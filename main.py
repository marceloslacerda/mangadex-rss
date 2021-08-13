import datetime
import os
import pathlib
import requests
import pickle

from feedgen.feed import FeedGenerator

CACHE_PATH = pathlib.Path('cache.bin')
FETCH_LIMIT = 10
TOKEN_PATH = pathlib.Path("token.txt")
USERNAME = os.environ["username"]
PASSWORD = os.environ["password"]
LANGUAGES = ["en"]
FEED_PATH = os.environ.get('feed_file', 'rss.xml')


def get_unread_manga(cache):
    session = get_session(USERNAME, PASSWORD)
    resp = session.get(
        f"https://api.mangadex.org/user/follows/manga/feed",
        params={"translatedLanguage[]": LANGUAGES[0], "limit": FETCH_LIMIT},
    ).json()
    chapters = []
    for chapter in resp["results"]:
        if chapter["data"]["attributes"]["translatedLanguage"] in LANGUAGES:

            manga_id = [
                r["id"] for r in chapter["relationships"] if r["type"] == "manga"
            ][0]
            chapter_id = chapter["data"]["id"]
            if manga_id not in cache['manga']:
                mdata = session.get(
                    "https://api.mangadex.org/manga/" + manga_id
                ).json()
                cache['manga'][manga_id] = mdata
            else:
                mdata = cache['manga'][manga_id]
            if chapter_id not in cache['chapters']:
                chapdata = session.get(
                    "https://api.mangadex.org/chapter/" + chapter_id
                ).json()
                cache['chapters'][chapter_id] = chapdata
            else:
                chapdata = cache['chapters'][chapter_id]
            chapters.append(
                {
                    "manga_id": manga_id,
                    "manga_title": list(mdata['data']['attributes']['title'].values())[0],
                    "chapter_no": chapter["data"]["attributes"]["chapter"],
                    "chapter_vol": chapter["data"]["attributes"]["volume"],
                    "chapter_id": chapter_id,
                    "chapter_title": chapdata['data']['attributes']['title']
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
            ).json()['token']
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
    #  fg.link(href='http://larskiesow.de/test.atom', rel='self')
    fg.language("en")
    if CACHE_PATH.exists():
        cache = pickle.load(CACHE_PATH.open('rb'))
    else:
        cache = {'chapters': {}, 'manga':{}, 'page': 0}

    for entry in get_unread_manga(cache):
        fe = fg.add_entry()
        chapter_url = f"https://mangadex.org/chapter/{entry['chapter_id']}"
        fe.guid(chapter_url)
        title = f"Chapter {entry['chapter_no']} of {entry['manga_title']} released"
        if entry['chapter_vol']:
            title = f"Volume {entry['chapter_vol']}, " + title
        fe.title(title)
        chapter_title = f" ({entry['chapter_title']})"
        fe.description(f"""A new chapter{chapter_title} of
        <a href="https://mangadex.org/manga/{entry['manga_id']}">{entry['manga_title']}</a>
        was released. <a href='{chapter_url}'>Link</a>.""")
        fe.link(href=f"https://mangadex.org/chapter/{entry['chapter_id']}/1")
    fg.rss_file(FEED_PATH)
    pickle.dump(cache, CACHE_PATH.open('wb'))


if __name__ == "__main__":
    main()
