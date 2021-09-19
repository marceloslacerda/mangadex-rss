import datetime
import os
import pathlib
import requests
import pickle

from feedgen.feed import FeedGenerator

CACHE_PATH = pathlib.Path("cache.bin")
FETCH_LIMIT = 10
TOKEN_PATH = pathlib.Path("token.txt")
USERNAME = os.environ["username"]
PASSWORD = os.environ["password"]
LANGUAGES = ["en"]
FEED_PATH = os.environ.get("feed_file", "rss.xml")


def get_unread_manga(cache):
    session = get_session(USERNAME, PASSWORD)
    resp = session.get(
        f"https://api.mangadex.org/user/follows/manga/feed",
        params={"translatedLanguage[]": LANGUAGES[0], "limit": FETCH_LIMIT},
    ).json()
    chapters = []
    for chapter in resp["results"]:
        chapter_no = int(chapter["data"]["attributes"]["chapter"])
        if chapter["data"]["attributes"]["translatedLanguage"] in LANGUAGES:
            manga_id = [
                r["id"] for r in chapter["relationships"] if r["type"] == "manga"
            ][0]
            chapter_id = chapter["data"]["id"]
            if manga_id not in cache["manga"]:
                mdata = session.get("https://api.mangadex.org/manga/" + manga_id).json()
                cache["manga"][manga_id] = mdata
            else:
                mdata = cache["manga"][manga_id]
            # if latest chapter not in mdata add to it
            if 'latest_chapter' not in mdata:
                result = session.get(f"https://api.mangadex.org/manga/{manga_id}/aggregate",
                                     params={"translatedLanguage[]": LANGUAGES[0]}).json()
                latest_volume = max(int(key) for key in result['volumes'].keys())
                latest_chapter_no = max(int(key) for key in result['volumes'][latest_volume]['chapters'].keys())
                mdata['latest_chapter'] = {'chapter_no': int(latest_chapter_no),
                                           'chapter_id': result['volumes'][latest_volume]['chapters'][latest_chapter_no]['id']
                                           }
            # todo deal with missing chapters
            # todo deal with deleted chapters
            if chapter_id not in cache["chapters"]:
                chapdata = session.get(
                    "https://api.mangadex.org/chapter/" + chapter_id
                ).json()
                cache["chapters"][chapter_id] = chapdata
                if mdata['latest_chapter']['chapter_no'] < chapter_no:
                    mdata['latest_chapter']['chapter_id'] = chapter_id
                    mdata['latest_chapter']['chapter_no'] = chapter_no
            else:
                chapdata = cache["chapters"][chapter_id]
            chapters.append(
                {
                    "manga_id": manga_id,
                    "manga_title": list(mdata["data"]["attributes"]["title"].values())[
                        0
                    ],
                    "chapter_no": chapter_no,
                    "chapter_vol": chapter["data"]["attributes"]["volume"],
                    "chapter_id": chapter_id,
                    "chapter_title": chapdata["data"]["attributes"]["title"],
                    "latest_chapter": mdata["latest_chapter"]
                }
            )
    return chapters


def get_session(username, password):
    s = requests.Session()
    if not TOKEN_PATH.exists():
        try:
            jwt = s.post(
                "https://api.mangadex.org/auth/login",
                json={"username": username, "password": password},
            ).json()["token"]
            TOKEN_PATH.write_text(jwt["refresh"])
            s.headers.update({"Authorization": jwt["session"]})
            return s
        except requests.exceptions.HTTPError:
            print("Could not login to mangadex")
            raise
    else:
        try:
            jwt = s.post(
                "https://api.mangadex.org/auth/refresh",
                json={"token": TOKEN_PATH.read_text()},
            ).json()["token"]
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
        title = f"Chapter {entry['chapter_no']} of {entry['manga_title']} released"
        if entry["chapter_vol"]:
            title = f"Volume {entry['chapter_vol']}, " + title
        fe.title(title)
        chapter_title = f" ({entry['chapter_title']})"
        if entry['latest_chapter']['chapter_no'] > entry['chapter_no']:
            latest_chap_no = entry['latest_chapter']['chapter_no']
            latest_chap_id = entry['latest_chapter']['chapter_id']
            fe.description(
                f"""An old chapter <a href='{chapter_url}'>{chapter_title}</a> of
                        <a href="https://mangadex.org/manga/{entry['manga_id']}">{entry['manga_title']}</a>
                        was released. Latest: <a href="https://mangadex.org/manga/{latest_chap_id}">{latest_chap_no}"""
            )
            fe.title(title + " (old)")
        else:
            fe.description(
                f"""A new chapter <a href='{chapter_url}'>{chapter_title}</a> of
            <a href="https://mangadex.org/manga/{entry['manga_id']}">{entry['manga_title']}</a>
            was released."""
            )
        fe.link(href=f"https://mangadex.org/chapter/{entry['chapter_id']}/1")
    fg.rss_file(FEED_PATH)
    pickle.dump(cache, CACHE_PATH.open("wb"))


if __name__ == "__main__":
    main()
