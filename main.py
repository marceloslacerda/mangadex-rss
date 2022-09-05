import os
import pathlib
import pickle
import logging
import hashlib
import re
from functools import total_ordering
from typing import Tuple, Type

from urllib.parse import urljoin

import requests

from feedgen.feed import FeedGenerator

NO_CHAPTER = -2

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=os.environ.get("loglevel", "WARNING"),
    force=True,
)

PROJECT_PATH = pathlib.Path(__file__).resolve().parent
CACHE_PATH = PROJECT_PATH / pathlib.Path("cache.bin")
TOKEN_PATH = PROJECT_PATH / pathlib.Path("token.txt")
try:
    USERNAME = os.environ["username"]
    PASSWORD = os.environ["password"]
except KeyError:
    print(
        "Either and/or the username or password environment variable was not"
        " set. Please read the README.md for more information."
    )
    exit(1)

LANGUAGES = list(
    l.strip() for l in os.environ.get("languages", "en").split(",") if l.strip()
)
FETCH_LIMIT = os.environ.get("fetch_limit", 10)
FEED_PATH = os.environ.get("feed_file", PROJECT_PATH / "rss.xml")
MARK_OLD = os.environ.get("mark_old", False)


@total_ordering
class Chapter:
    """Base chapter class"""

    class Nothing:
        """Placeholder class to prevent any instance to compare to it"""

    dominant_class: Type["Chapter"] = Nothing

    def __init__(self, contents: Tuple) -> None:
        self.contents = contents

    def __lt__(self, other) -> bool:
        if isinstance(other, self.dominant_class):
            return True
        elif isinstance(other, self.__class__):
            return self.contents < other.contents
        else:
            return False

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.contents == other.contents
        else:
            return False

    def __hash__(self) -> int:
        return hash(self.contents)


class PairChapter(Chapter):
    """Chapter in the form of x.y where x and y are numbers.
    Instances of this class are ordered below NumberChapters and above everything else."""

    def __init__(self, arg: str) -> None:
        pair = arg.split(".")
        if len(pair) != 2:
            raise ValueError(f"{arg} is not a pair chapter")
        self.first = int(pair[0])
        self.last = int(pair[1])
        super().__init__((self.first, self.last))

    def __str__(self) -> str:
        return f"{self.first}.{self.last}"


class PartialNumberChapter(Chapter):
    """Chapter that starts with a number but has some extra text.
    Instances of this class are ordered below PairChapters and above StringChapters.
    """

    dominant_class = PairChapter

    def __init__(self, arg: str) -> None:
        match = re.match(r"(\d+)(.+)", arg)
        if not match:
            raise ValueError(f"{arg} is not a partial number chapter")
        else:
            self.number = int(match.group(1))
            self.text = match.group(2)
        super().__init__((self.number, self.text))

    def __str__(self):
        return f"{self.number}{self.text}"


class NumberChapter(Chapter):
    """Single number chapter."""

    dominant_class = PartialNumberChapter

    def __init__(self, arg: str) -> None:
        self.value = int(arg)
        super().__init__((self.value,))

    def __str__(self) -> str:
        return str(self.value)


class StringChapter(Chapter):
    """Chapter that couldn't be parsed.
    Always below other chapters."""

    dominant_class = NumberChapter

    def __init__(self, arg):
        self.value = arg
        super().__init__((self.value,))

    def __str__(self) -> str:
        return self.value


def get_api_method(session, method, params=None):
    response = session.get(
        urljoin("https://api.mangadex.org/", method),
        params=params,
    )
    response.raise_for_status()
    return response.json()


def get_latest_chapter(session, manga_id):
    result = get_api_method(
        session,
        f"manga/{manga_id}/aggregate",
        params={"translatedLanguage[]": language for language in LANGUAGES},
    )
    logging.debug("Manga %s aggregate result:\n%s", manga_id, result)
    chapters = {}
    if not result["volumes"]:
        return {"chapter_no": NO_CHAPTER, "chapter_id": None}
    for vol_id, volume in result["volumes"].items():
        for chapter_no in volume["chapters"]:
            if isinstance(chapter_no, dict):
                chapters[
                    parse_str_to_chapter(chapter_no["chapter"], vol_id, manga_id)
                ] = chapter_no["id"]
            else:
                chapters[parse_str_to_chapter(chapter_no, vol_id, manga_id)] = volume[
                    "chapters"
                ][chapter_no]["id"]
    latest_chapter_no = max(chapters)
    return {
        "chapter_no": latest_chapter_no,
        "chapter_id": chapters[latest_chapter_no],
    }


def parse_str_to_chapter(chapter_str, volume, manga_id) -> Chapter:
    classes = (NumberChapter, PairChapter, PartialNumberChapter, StringChapter)
    for class_ in classes:
        try:
            return class_(chapter_str)
        except ValueError:
            pass
    logging.error(
        "Error parsing chapter %s of volume %s of" " manga with id %s",
        chapter_str,
        volume,
        manga_id,
    )


def get_unread_manga(cache):
    session = get_session(USERNAME, PASSWORD)
    logging.debug("Session obtained")
    payload = [
        ("limit", FETCH_LIMIT),
        ("order[createdAt]", "desc"),
    ]
    payload.extend(("translatedLanguage[]", language) for language in LANGUAGES)
    updates = get_api_method(
        session,
        "user/follows/manga/feed",
        payload,
    )["data"]
    logging.debug("Feed result:\n%s", updates)
    results = []
    for update in updates:
        manga_id = next(
            r["id"] for r in update["relationships"] if r["type"] == "manga"
        )
        chapter_no = parse_str_to_chapter(
            update["attributes"]["chapter"], update["attributes"]["volume"], manga_id
        )
        chapter_id = update["id"]
        if chapter_id in cache["chapters"]:
            continue
        if manga_id not in cache["manga"]:
            mdata = get_api_method(session, "manga/" + manga_id)
            cache["manga"][manga_id] = mdata
        else:
            mdata = cache["manga"][manga_id]
        if "latest_chapter" not in mdata:
            mdata["latest_chapter"] = get_latest_chapter(session, manga_id)
        # todo deal with missing chapters
        # todo deal with deleted chapters
        if chapter_id not in cache["chapters"]:
            chapdata = get_api_method(session, "chapter/" + chapter_id)
            cache["chapters"][chapter_id] = chapdata
            if mdata["latest_chapter"]["chapter_no"] < chapter_no:
                mdata["latest_chapter"]["chapter_id"] = chapter_id
                mdata["latest_chapter"]["chapter_no"] = chapter_no
        else:
            chapdata = cache["chapters"][chapter_id]
        results.append(
            {
                "manga_id": manga_id,
                "manga_title": list(mdata["data"]["attributes"]["title"].values())[0],
                "chapter_no": chapter_no,
                "chapter_vol": update["attributes"]["volume"],
                "chapter_id": chapter_id,
                "chapter_title": chapdata["data"]["attributes"]["title"],
                "latest_chapter": mdata["latest_chapter"],
                "official": update["attributes"]["externalUrl"],
                "created_at": chapdata["data"]["attributes"]["createdAt"],
                "language": chapdata["data"]["attributes"]["translatedLanguage"],
            }
        )
    return results


def get_session(username, password):
    logging.debug("Getting an open session")
    s = requests.Session()
    if not TOKEN_PATH.exists():
        try:
            response = s.post(
                "https://api.mangadex.org/auth/login",
                json={"username": username, "password": password},
            )
            response.raise_for_status()
            jwt = response.json()["token"]
            TOKEN_PATH.write_text(jwt["refresh"])
            s.headers.update({"Authorization": jwt["session"]})
            return s
        except requests.exceptions.HTTPError:
            print("Could not login to mangadex")
            raise
    else:
        try:
            response = s.post(
                "https://api.mangadex.org/auth/refresh",
                json={"token": TOKEN_PATH.read_text()},
            )
            response.raise_for_status()
            jwt = response.json()["token"]
            s.headers.update({"Authorization": jwt["session"]})
            return s
        except requests.exceptions.HTTPError:
            print("Could not refresh the token. Try again later.")
            os.remove(TOKEN_PATH)
            raise


def script_hash() -> bytes:
    """Get the hash of this version of mangadex-rss"""
    m = hashlib.md5()
    with open(__file__, "rb") as f:
        m.update(f.read())
        return m.digest()


def is_old_cache(cache: dict, hash_: bytes) -> bool:
    """True if this version of mangadex-rss is old"""
    try:
        return cache["hash"] != hash_
    except KeyError:
        return True


def main():
    fg = FeedGenerator()
    fg.id("https://mangadex.org/user/follows/manga/feed")
    fg.title("Mangadex Subscriptions")
    fg.link(href="https://mangadex.org", rel="alternate")
    fg.logo("https://mangadex.org/favicon.svg")
    fg.subtitle("Mangadex User Feed")
    fg.language("en")
    logging.debug("Starting up")
    hash_ = script_hash()
    if CACHE_PATH.exists():
        cache = pickle.load(CACHE_PATH.open("rb"))
        if is_old_cache(cache, hash_):
            logging.debug("Purging old cache")
            cache = {"chapters": {}, "manga": {}, "page": 0, "hash": hash_}
    else:
        cache = {"chapters": {}, "manga": {}, "page": 0, "hash": hash_}

    for entry in get_unread_manga(cache):
        fe = fg.add_entry()
        chapter_url = f"https://mangadex.org/chapter/{entry['chapter_id']}"
        fe.guid(chapter_url)
        chapter_no_str = str(entry["chapter_no"])
        title = f"Chapter {chapter_no_str} of {entry['manga_title']} released"
        if entry["chapter_vol"]:
            title = f"Volume {entry['chapter_vol']}, " + title
        fe.title(title)
        if entry["chapter_title"]:
            chapter_title = f"'{entry['chapter_title']}'"
        else:
            chapter_title = chapter_no_str
        if entry["latest_chapter"]["chapter_no"] > entry["chapter_no"] and MARK_OLD:
            latest_chap_no = str(entry["latest_chapter"]["chapter_no"])
            latest_chap_id = entry["latest_chapter"]["chapter_id"]
            description = (
                f"An old chapter <a href='{chapter_url}'>{chapter_title}</a> of"
                f' <a href="https://mangadex.org/manga/{entry["manga_id"]}">{entry["manga_title"]}</a>'
                f' was released. Latest: <a href="https://mangadex.org/manga/{latest_chap_id}">{latest_chap_no}</a>'
            )
            fe.title(title + " (old)")
        else:
            description = (
                f"A new chapter <a href='{chapter_url}'>{chapter_title}</a> of"
                f' <a href="https://mangadex.org/manga/{entry["manga_id"]}">{entry["manga_title"]}</a>'
                " was released."
            )
        if entry["official"]:
            description += (
                f'<br/>Official publisher <a href="{entry["official"]}">link</a>'
            )
        if len(LANGUAGES) > 1:
            fe.title(fe.title() + f' - Language [{entry["language"]}]')
        fe.description(description)
        chapter_link = f"https://mangadex.org/chapter/{entry['chapter_id']}/1"
        fe.link(href=chapter_link)
        fe.guid(chapter_link)
        fe.published(entry["created_at"])
    write_rss(fg)
    pickle.dump(cache, CACHE_PATH.open("wb"))


def write_rss(fg):
    try:
        with open(FEED_PATH, "r") as feed_file:
            if not fg.entry():
                return
            feed_str = str(fg.rss_str(), "utf-8")
            old_str = feed_file.read()
            old_begin_idx = old_str.find("<item>")
            if old_begin_idx == -1:
                fg.rss_file(FEED_PATH)
                return
            old_end_idx = old_str.rfind("</item>") + 7
            new_end_idx = feed_str.find("</item>") + 7
            new_str = (
                feed_str[:new_end_idx]
                + old_str[old_begin_idx:old_end_idx]
                + feed_str[new_end_idx:]
            )
        with open(FEED_PATH, "w") as feed_file:
            feed_file.write(new_str)
    except FileNotFoundError:
        fg.rss_file(FEED_PATH)


if __name__ == "__main__":
    main()
