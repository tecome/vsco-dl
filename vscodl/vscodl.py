#!/usr/bin/env python
import argparse
import concurrent.futures
import os
from concurrent.futures import ThreadPoolExecutor

import constants
import requests
import vsco
from tqdm import tqdm


class Scraper:
    def __init__(self, username, workers=5, output_dir=None):
        self.username = username
        self.output_dir = output_dir
        self.workers = workers

        self.session = requests.Session()

        # Send request to get cookie which is required later
        vsco.user_info(self.session)
        self.uid = self.session.cookies.get_dict()["vs"]

        # VSCO user information
        self.site_id = None
        self.has_collection = False
        self.images = []
        self.journals = []

        # Progress bars
        self.find_progress = None
        self.download_progress = None

        self.totalj = 0

    def prepare_dir(self) -> None:
        """Prepares download directory"""
        path = self.output_dir.replace("%u", self.username) if self.output_dir else self.username

        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        elif not os.path.isdir(path):
            raise RuntimeError("{} is not a directory!".format(path))
        if not os.access(path, os.W_OK):
            raise RuntimeError("{} is not writable!".format(path))

        os.chdir(path)

    def get_site_id(self) -> int:
        """Gets VSCO user/site ID"""
        if self.site_id is None:
            info = vsco.get_sites(self.session, self.uid, self.username)[0]
            self.site_id = info["id"]
            self.has_collection = info["has_collection"]
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

                destination = "{}_{}.{}".format(os.path.basename(source)[:-4], upload_timestamp, ext)

                if destination in os.listdir() or "{}.jpg".format(upload_timestamp) in os.listdir() or \
                        "{}.mp4".format(upload_timestamp) in os.listdir():
                    continue

                # Tuple of source, destination
                found.append(("https://{}".format(source), destination))
                self.find_progress.update()
            page += self.workers

        return found

    def download_images(self) -> bool:
        """Downloads images/videos of a user."""
        self.get_site_id()
        self.prepare_dir()

        # Fetch media urls
        self.find_progress = tqdm(desc="{} - Finding images".format(self.username), unit=" images")
        with ThreadPoolExecutor(max_workers=self.workers) as tpe:
            futures = [tpe.submit(self.fetch_media_urls, page) for page in range(self.workers)]
            for future in concurrent.futures.as_completed(futures):
                self.images += future.result()
        self.find_progress.close()

        # Download media
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as tpe:
            futures = {tpe.submit(self.download_file, file): file for file in self.images}
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(self.images),
                               desc="{} - Downloading images".format(self.username), unit=" images"):
                try:
                    future.result()
                except Exception as e:
                    print("Failed to download {}:".format(futures[future][0]), e)

        return True

    def download_file(self, file) -> bool:
        """Downloads a file."""
        source, destination = file

        if destination in os.listdir():
            return True

        with open(destination, "wb") as f:
            r = vsco.download_url(self.session, source)
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
    parser.add_argument("-i", "--images", action="store_true", dest="images", help="Download user images/videos",
                        required=True)
    # parser.add_argument("-j", "--journals", action="store_true", dest="journals", help="Download user journals")
    parser.add_argument("-f", "--file", action="store", dest="file", help="Filename containing usernames to download")
    parser.add_argument("-w", "--workers", action="store", dest="workers", type=int, default=5,
                        help="Number of download workers")
    parser.add_argument("-o", "--output", action="store", dest="output", type=str, help="Output dir")
    args = parser.parse_args()

    # if not args.images and not args.journals:
    #     parser.error("One of -i and -j must be used")

    if args.username:
        scraper = Scraper(args.username, args.workers, args.output)
        if args.images:
            scraper.download_images()
        # if args.journals:
        #     scraper.download_journals()
    elif args.file:
        cwd = os.getcwd()
        with open(args.file, 'r') as f:
            usernames = [x.strip() for x in f]
        for username in usernames:
            if username == "":
                continue

            os.chdir(cwd)
            scraper = Scraper(username, args.workers, args.output)

            if args.images:
                scraper.download_images()
            # if args.journals:
            #     scraper.download_journals()
            print()


if __name__ == '__main__':
    main()