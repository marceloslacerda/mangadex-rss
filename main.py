import os
import pathlib
import requests
import pickle
from urllib.parse import urljoin

from feedgen.feed import FeedGenerator

CACHE_PATH = pathlib.Path("cache.bin")
FETCH_LIMIT = 10
TOKEN_PATH = pathlib.Path("token.txt")
USERNAME = os.environ["username"]
PASSWORD = os.environ["password"]
LANGUAGES = ["en"]
FEED_PATH = os.environ.get("feed_file", "rss.xml")


def get_api_method(session, method, params=None):
    response = session.get(
        urljoin(f"https://api.mangadex.org/", method),
        params=params,
    )
    response.raise_for_status()
    return response.json()


def get_latest_chapter(session, manga_id):
    result = get_api_method(
        session,
        f"manga/{manga_id}/aggregate",
        params={"translatedLanguage[]": LANGUAGES[0]},
    )
    chapters = {}
    for volume in result["volumes"].values():
        for chapter_no in volume["chapters"]:
            chapters[parse_chapter_to_tup(chapter_no)] = volume["chapters"][chapter_no][
                "id"
            ]
    latest_chapter_no = max(chapters)
    return {
        "chapter_no": latest_chapter_no,
        "chapter_id": chapters[latest_chapter_no],
    }


def parse_chapter_to_tup(txt):
    if isinstance(txt, int) or isinstance(txt, tuple):
        return txt
    try:
        return (int(txt),)
    except ValueError:
        if "." in txt:
            return tuple(int(x) for x in txt.split("."))


def get_unread_manga(cache):
    session = get_session(USERNAME, PASSWORD)
    updates = get_api_method(
        session,
        "user/follows/manga/feed",
        {"translatedLanguage[]": LANGUAGES[0], "limit": FETCH_LIMIT},
    )["data"]
    results = []
    for update in updates:
        chapter_no = parse_chapter_to_tup(update["attributes"]["chapter"])
        manga_id = next(
            r["id"] for r in update["relationships"] if r["type"] == "manga"
        )
        chapter_id = update["id"]
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
            }
        )
    return results


def get_session(username, password):
    s = requests.Session()
    if not TOKEN_PATH.exists():
        try:
            resposnse = s.post(
                "https://api.mangadex.org/auth/login",
                json={"username": username, "password": password},
            )
            resposnse.raise_for_status()
            jwt = resposnse.json()["token"]
            TOKEN_PATH.write_text(jwt["refresh"])
            s.headers.update({"Authorization": jwt["session"]})
            return s
        except requests.exceptions.HTTPError:
            print("Could not login to mangadex")
            raise
    else:
        try:
            resposnse = s.post(
                "https://api.mangadex.org/auth/refresh",
                json={"token": TOKEN_PATH.read_text()},
            )
            resposnse.raise_for_status()
            jwt = resposnse.json()["token"]
            s.headers.update({"Authorization": jwt["session"]})
            return s
        except requests.exceptions.HTTPError:
            print("Could not refresh the token. Try again later.")
            os.remove(TOKEN_PATH)
            raise


def main():
    fg = FeedGenerator()
    fg.id("https://mangadex.org/user/follows/manga/feed")
    fg.title("Mangadex Subscriptions")
    fg.link(href="https://mangadex.org", rel="alternate")
    fg.logo("https://mangadex.org/favicon.svg")
    fg.subtitle("Mangadex User Feed")
    fg.language("en")
    if CACHE_PATH.exists():
        cache = pickle.load(CACHE_PATH.open("rb"))
    else:
        cache = {"chapters": {}, "manga": {}, "page": 0}

    for entry in get_unread_manga(cache):
        fe = fg.add_entry()
        chapter_url = f"https://mangadex.org/chapter/{entry['chapter_id']}"
        fe.guid(chapter_url)
        chapter_no_str = parse_tup_to_chapter(entry["chapter_no"])
        title = f"Chapter {chapter_no_str} of {entry['manga_title']} released"
        if entry["chapter_vol"]:
            title = f"Volume {entry['chapter_vol']}, " + title
        fe.title(title)
        if entry["chapter_title"]:
            chapter_title = f"'{entry['chapter_title']}'"
        else:
            chapter_title = chapter_no_str
        if entry["latest_chapter"]["chapter_no"] > entry["chapter_no"]:
            latest_chap_no = parse_tup_to_chapter(entry["latest_chapter"]["chapter_no"])
            latest_chap_id = entry["latest_chapter"]["chapter_id"]
            fe.description(
                f"An old chapter <a href='{chapter_url}'>{chapter_title}</a> of"
                f' <a href="https://mangadex.org/manga/{entry["manga_id"]}">{entry["manga_title"]}</a>'
                f' was released. Latest: <a href="https://mangadex.org/manga/{latest_chap_id}">{latest_chap_no}'
            )
            fe.title(title + " (old)")
        else:
            fe.description(
                f"A new chapter <a href='{chapter_url}'>{chapter_title}</a> of"
                f' <a href="https://mangadex.org/manga/{entry["manga_id"]}">{entry["manga_title"]}</a>'
                "was released."
            )
        fe.link(href=f"https://mangadex.org/chapter/{entry['chapter_id']}/1")
    fg.rss_file(FEED_PATH)
    pickle.dump(cache, CACHE_PATH.open("wb"))


def parse_tup_to_chapter(tup):
    return ".".join(str(x) for x in tup)


if __name__ == "__main__":
    main()
