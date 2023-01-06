import json
from argparse import ArgumentError, ArgumentParser, FileType
from concurrent.futures import ThreadPoolExecutor, as_completed
from os import chdir, mkdir, system
from pathlib import Path
from shutil import move
from sys import argv

import mutagen
from tqdm import tqdm
from youtube_dl import YoutubeDL

M4A_FORMAT = "140"


class Progress:
    def __init__(self, bar):
        self.bar = bar
        self.prev = 0


def write_metadata(playlist_id):
    with open(f"{playlist_id}.info.json") as f:
        info = json.load(f)
    album_dir_path = Path(playlist_id)
    m4a_paths = list(album_dir_path.glob("*.m4a"))
    track_number_max = len(m4a_paths)
    for m4a_path in m4a_paths:
        entry_id, _ = m4a_path.stem.split(".", 1)
        (entry,) = [e for e in info["entries"] if e["id"] == entry_id]
        track_number = int(entry["playlist_index"])
        title = entry["title"]
        album = entry["album"]
        artist = entry["artist"]

        mutagen_file = mutagen.File(m4a_path)
        mutagen_file.tags["trkn"] = [(track_number, track_number_max)]
        mutagen_file.tags["\xa9nam"] = title
        mutagen_file.tags["\xa9alb"] = album
        mutagen_file.tags["\xa9ART"] = artist
        mutagen_file.save()


def download(url, progress):
    class Logger:
        def debug(self, msg):
            pass
            # print(f"debug: {msg}")

        def warning(self, msg):
            pass
            # print(f"warning: {msg}")

        def error(self, msg):
            pass
            # print(f"error: {msg}")

    def prog_hook(d):
        progress.bar.desc = d["filename"]
        progress.bar.total = d["total_bytes"]
        progress.bar.update(d["downloaded_bytes"] - progress.prev)
        progress.prev = d["downloaded_bytes"]
        # if d["status"] != "downloading":
        #     print(d)
        #     print(type(d))
        pass

    with YoutubeDL(
        {
            "format": M4A_FORMAT,
            "outtmpl": "%(id)s.%(title)s.%(ext)s",
            "logger": Logger(),
            "progress_hooks": [prog_hook],
        }
    ) as ydl:
        ydl.download([url])


def get_info(playlist_url):
    class Logger:
        def debug(self, msg):
            if msg.startswith("[download] Finished downloading playlist:"):
                system("clear")
                # print("getting info done")
            elif msg.startswith("[download] Downloading video"):
                system("clear")
                item = msg.replace("[download] Downloading video ", "")
                print(f"Downloading info {item}")
            else:
                pass
            # print(f"debug: {msg}")

        def warning(self, msg):
            pass
            # print(f"warning: {msg}")

        def error(self, msg):
            pass
            # print(f"error: {msg}")

    def prog_hook(d):
        pass
        # print(d)
        # if d['status'] == 'finished':
        #     print('Done downloading, now converting ...')

    opts = {"logger": Logger(), "progress_hooks": [prog_hook]}

    log_msg = "Info download"
    print(log_msg)
    print("-" * len(log_msg))
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
    return info


def parse_args():
    parser = ArgumentParser()
    parser.add_argument("-r", "--resume", type=FileType("r"))
    parser.add_argument("url", type=str, nargs="?")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.url is None and args.resume is None:
        raise ArgumentError(args.resume, "Either File to resume (-r) or URL required")
    if args.resume:
        info = json.load(args.resume)
    else:
        info = get_info(args.url)
    playlist_id = info["id"]
    entries_len = len(info["entries"])
    with open(f"{playlist_id}.info.json", "w") as f:
        json.dump(info, f)
    download_dir = playlist_id
    try:
        mkdir(download_dir)
    except FileExistsError as err:
        pass
    except Exception as err:
        raise Exception("unknown") from err
    chdir(download_dir)
    song_urls = [
        (entry["webpage_url"], _format["filesize"])
        for entry in info["entries"]
        for _format in entry["formats"]
        if _format["format_id"] == "140"
    ]
    with ThreadPoolExecutor(max_workers=len(song_urls)) as executor:
        # executor.map(download, song_urls)
        futures = {}
        for i, url in enumerate(song_urls, start=1):
            # progress=tqdm(total=url[1],position=i)
            progress = Progress(tqdm(position=i))
            futures[executor.submit(download, url[0], progress)] = (url, progress)
        done_bars = []
        with tqdm(total=len(song_urls), position=0, desc="Download") as progress:
            for future in as_completed(futures):
                _url, p = futures[future]
                done_bars.append(p.bar)
                progress.update(1)
        for bar in done_bars:
            bar.close()
        # executor.shutdown()
    parts = list(Path(".").glob("*.part"))
    done = list(Path(".").glob("*.m4a"))
    while parts or (len(done) < entries_len):
        with ThreadPoolExecutor(max_workers=len(song_urls)) as executor:
            executor.map(download, song_urls)
            executor.shutdown()
        parts = list(Path(".").glob("*.part"))
        done = list(Path(".").glob("*.m4a"))
    chdir("..")
    write_metadata(playlist_id)
