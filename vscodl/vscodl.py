#!/usr/bin/env python
import argparse
import concurrent.futures
import os
from concurrent.futures import ThreadPoolExecutor

import requests
from tqdm import tqdm

from vscodl import constants, vsco


class Scraper:
    def __init__(self, username, workers=5, output_dir=None):
        self.username = username
        self.output_dir = output_dir
        self.workers = workers

        self.session = requests.Session()

        # Send request to get cookie which is required later
        vsco.init(self.session)
        self.uid = self.session.cookies.get_dict()["vs"]

        # VSCO user information
        self.site_id = None
        self.has_collection = False
        self.images = []
        self.journals = []
        self.profile_image_url = None

        # Progress bars
        self.find_progress = None
        self.download_progress = None

        self.totalj = 0

    @staticmethod
    def get_media_filename(source, upload_timestamp, ext):
        return "{}_{}.{}".format(os.path.basename(source)[:-4], upload_timestamp, ext)

    @staticmethod
    def prepare_dir(path) -> None:
        """Makes sure directory is created and writable"""
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        elif not os.path.isdir(path):
            raise RuntimeError("{} is not a directory!".format(path))
        if not os.access(path, os.W_OK):
            raise RuntimeError("{} is not writable!".format(path))

    @staticmethod
    def file_exists(filename, upload_timestamp=None) -> bool:
        l = os.listdir()
        if filename in l:
            return True
        if upload_timestamp is not None and (f"{upload_timestamp}.jpg" in l or f"{upload_timestamp}.mp4" in l):
            return True
        return False

    def prepare_main_dir(self) -> None:
        """Prepares main download directory"""
        path = self.output_dir.replace("%u", self.username) if self.output_dir else self.username
        self.prepare_dir(path)
        os.chdir(path)

    def prepare_journal_dir(self) -> None:
        """Prepares journal directory"""
        self.prepare_main_dir()
        path = "journal"
        self.prepare_dir(path)
        os.chdir(path)

    def get_site_id(self) -> int:
        """Gets VSCO user/site ID"""
        if self.site_id is None:
            info = vsco.get_sites(self.session, self.uid, self.username)[0]
            self.site_id = info["id"]
            self.has_collection = info["has_collection"] if "has_collection" in info else False
            self.profile_image_url = info["profile_image"].split("?")[0]
        return self.site_id

    def fetch_media_urls(self, page) -> list:
        """Returns media URLs"""
        page += 1
        found = []
        while True:
            medias = vsco.get_medias(self.session, self.uid, self.site_id, size=100, page=page)["media"]

            if len(medias) == 0:
                break

            for media in medias:
                # Check if file already exists in download directory (backwards-compatible with vsco-scraper)
                upload_timestamp = str(media["upload_date"])[:-3]

                source = media["responsive_url"] if not media["is_video"] else media["video_url"]
                ext = source[-3:]

                destination = self.get_media_filename(source, upload_timestamp, ext)

                if self.file_exists(destination, upload_timestamp):
                    continue

                # Tuple of source, destination
                found.append(("https://{}".format(source), destination))
                self.find_progress.update()
            page += self.workers
        return found

    def fetch_article_urls(self, page) -> list:
        """Returns article URLs to download (or text)"""
        page += 1
        found = []
        while True:
            articles = vsco.get_articles(self.session, self.uid, self.site_id, size=100, page=page)["articles"]

            if len(articles) == 0:
                break

            for article in articles:
                journal_slug = article["permalink"]

                for item in article["body"]:
                    if item["type"] == "image":
                        destination = item["content"][0]["id"] + ".jpg"
                        source = "https://" + item["content"][0]["responsive_url"]
                    elif item["type"] == "video":
                        destination = item["content"][0]["id"] + ".mp4"
                        source = "https://" + item["content"][0]["video_url"]
                    elif item["type"] == "text":
                        destination = item["content"][:251] + ".txt"
                        source = item["content"]
                    else:
                        print("Found unexpected type: {}".format(item["type"]))
                        continue

                    if os.path.isdir(journal_slug) and destination in os.listdir(journal_slug):
                        continue

                    found.append((source, os.path.join(journal_slug, destination)))
                    self.find_progress.update()
            page += self.workers
        return found

    def fetch_profile_image(self, url):
        r = self.session.get(url)
        if r.status_code == 200:
            # Get final url from redirect
            filename = os.path.basename(r.url)
            destination = self.get_media_filename(filename, 0, filename[-3:])
            if not self.file_exists(destination, 0):
                self.find_progress.update()
                return [(r.url, destination)]
        return []

    def download_images(self):
        """Downloads images/videos of a user."""
        cwd = os.getcwd()
        self.get_site_id()
        self.prepare_main_dir()

        # Fetch media urls
        self.find_progress = tqdm(desc="{} - Finding images".format(self.username), unit=" images")
        with ThreadPoolExecutor(max_workers=self.workers) as tpe:
            futures = [tpe.submit(self.fetch_media_urls, page) for page in range(self.workers)]

            # Download profile image if there is one
            if self.profile_image_url:
                futures.append(tpe.submit(self.fetch_profile_image, self.profile_image_url))

            for future in concurrent.futures.as_completed(futures):
                self.images += future.result()
        self.find_progress.close()

        if not self.images:
            return

        # Download media
        with ThreadPoolExecutor(max_workers=self.workers) as tpe:
            futures = {tpe.submit(self.download_file, file): file for file in self.images}
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(self.images),
                               desc="{} - Downloading images".format(self.username), unit=" images"):
                try:
                    future.result()
                except Exception as e:
                    print("Failed to download {}:".format(futures[future][0]), e)
        os.chdir(cwd)

    def download_journals(self):
        """Downloads journals of a user."""
        cwd = os.getcwd()
        self.get_site_id()

        # Find journal image/video/text files
        self.find_progress = tqdm(desc="{} - Finding journal posts".format(self.username), unit=" journal posts")
        with ThreadPoolExecutor(max_workers=self.workers) as tpe:
            futures = [tpe.submit(self.fetch_article_urls, page) for page in range(self.workers)]
            for future in concurrent.futures.as_completed(futures):
                self.journals += future.result()
        self.find_progress.close()

        if not self.journals:
            return

        self.prepare_journal_dir()

        # Download
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as tpe:
            futures = {tpe.submit(self.download_file, file): file for file in self.journals}
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(self.journals),
                               desc="{} - Downloading journal posts".format(self.username), unit=" journal posts"):
                try:
                    future.result()
                except Exception as e:
                    print("Failed to download {}:".format(futures[future][0]), e)
        os.chdir(cwd)

    def download_file(self, file) -> bool:
        """Downloads a file."""
        source, destination = file

        if destination in os.listdir():
            return True

        d = os.path.dirname(destination)
        if d != "":
            os.makedirs(d, exist_ok=True)

        with open(destination, "wb") as f:
            if destination[-3:].lower() == "txt":
                # The actual text body is source in this case
                f.write(source.encode("utf-8"))
            else:
                use_host_header = source.split("/")[3] == "1"

                r = vsco.download_url(self.session, source, use_host_header)
                if destination[-3:].lower() == "mp4":
                    for chunk in r.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
                else:
                    f.write(r.content)
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Scrapes a specified users VSCO, currently only supports one user at a time")
    parser.add_argument("--version", action="version", version="%(prog)s {}".format(constants.VERSION))
    parser.add_argument("username", action="store", nargs="?", help="Username of VSCO user")
    parser.add_argument("-i", "--images", action="store_true", dest="images", help="Download user images/videos")
    parser.add_argument("-j", "--journals", action="store_true", dest="journals", help="Download user journals")
    parser.add_argument("-f", "--file", action="store", dest="file", help="Filename containing usernames to download")
    parser.add_argument("-w", "--workers", action="store", dest="workers", type=int, default=5,
                        help="Number of download workers")
    parser.add_argument("-o", "--output", action="store", dest="output", type=str, help="Output dir")
    args = parser.parse_args()

    if not args.images and not args.journals:
        parser.error("One of -i and -j must be used")

    if not args.username and not args.file:
        parser.error("Must provide username or use -f argument")

    if args.username:
        scraper = Scraper(args.username, args.workers, args.output)
        if args.images:
            scraper.download_images()
        if args.journals:
            scraper.download_journals()
    elif args.file:
        cwd = os.getcwd()
        with open(args.file, "r") as f:
            usernames = [x.strip() for x in f]
        for username in usernames:
            if username == "":
                continue

            os.chdir(cwd)
            scraper = Scraper(username, args.workers, args.output)

            if args.images:
                scraper.download_images()
            if args.journals:
                scraper.download_journals()
            print()


if __name__ == "__main__":
    main()
