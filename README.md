# vsco-dl

vsco-dl allows you to scrape and download a VSCO user's images/videos and journals.

### Installation

To install vsco-dl:

```bash
$ pip install vsco-dl
```

To update vsco-dl:

```bash
 $ pip install vsco-dl --upgrade
```


## Usage

To download a user's images/videos:
```
 $ vsco-dl -i <username>
```

Images are by default downloaded into `./<username>`. You can change this with the `-o` option.


You may specify a file as input. This file must contain one username per line. Blank lines are skipped.
```
 $ vsco-dl -i -f <filename>
```


## Options

|Option|Description|
|---|---|
|-i, --images|Scrape and download user's images/videos
|-f, --filename|Specify filename containing multiple usernames to download
|-o, --output|Set output directory for user. `%u` will be replaced by the username.
|-w, --workers|Set max download workers (default is 5)
|-h, --help|Print help


## License

This project is licensed under the GNU GPLv3 License - see [LICENSE](LICENSE) for details

