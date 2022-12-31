import json
from argparse import ArgumentError, ArgumentParser, FileType
from concurrent.futures import ThreadPoolExecutor
from os import chdir, mkdir
from pathlib import Path
from shutil import move
from sys import argv

import mutagen
from youtube_dl import YoutubeDL

M4A_FORMAT = "140"


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


def download(url):
    with YoutubeDL(
        {"format": M4A_FORMAT, "outtmpl": "%(id)s.%(title)s.%(ext)s"}
    ) as ydl:
        ydl.download([url])


def get_info(playlist_url):
    with YoutubeDL() as ydl:
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
    song_urls = [entry["webpage_url"] for entry in info["entries"]]
    with ThreadPoolExecutor(max_workers=len(song_urls)) as executor:
        executor.map(download, song_urls)
        executor.shutdown()
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
