# mangadex-rss

A [mangadex](https://mangadex.org/) rss generator for the new site (v5).

# How to install and run

1. Clone this repo.

   ```bash
   git clone https://github.com/marceloslacerda/mangadex-rss
   cd mangadex-rss
   ```
2. Install the requirements (preferrably using [virtual environments](https://docs.python.org/3/library/venv.html) or using the `--user` [option](https://stackoverflow.com/questions/42988977/what-is-the-purpose-of-pip-install-user)).

   ```bash
   pip install -r requirements.txt
   ```

3. Set your mangadex credentials.
   ```bash
   export username=myusername
   export password=mypassword
   ```
4. [OPTIONAL] Set some other environment variables to customize the behavior.
   ```bash
   # This sets the generator should put the generated feed file.
   export feed_file=/var/www/html/manga-feed.rss
   # Set which languages to filter.
   export languages='en,es'
   # Set how many chapters to fetch per run (default 10)
   export fetch_limit=20
   ```

5. Run.
   ```bash
   python main.py
   ```
 ---
 
 # How does it work?
 
 It connects to [mangadex api](https://api.mangadex.org/docs/) using your credentials and pulls the latest changes to the manga you are following and turns that into a [RSS xml](https://www.rssboard.org/rss-specification) that's written to the chosen `feed_file`.
 
 # How do I use the generated file?
 
 There are several ways to use the rss file, in my particular case I used [tt-rss](https://tt-rss.org/) on my personal vps.
 
 That might be too complicated or costly for most. Some rss readers might be able to open the file normally. I know that [liferea](https://lzone.de/liferea/) (example image below) is not only capable of reading local rss files but is also will regularly check it for changes, other readers might be able to do the same.
 
 ![liferea subscription box for local file rss](https://msl09.com.br/images/Screenshot_2022-09-05_06-53-45.png "liferea file subscription window")
 
 # How do I keep updating the generated RSS?

I personally use a [cron](https://en.wikipedia.org/wiki/Cron) job that calls **mangadex-rss** every 5th minute of each hour.

```cron
5 * * * * root /opt/mangadex-rss/md-rss
```

The `md-rss` file is just an executable script that calls **mangadex-rss** with my credentials.

```bash
#!/bin/sh -e
cd "$(dirname $0)"
. venv/bin/activate
export username=...
export password='...'
export feed_file=/var/www/html/manga.rss
python3 main.py
```
If you are going the route of running **mangadex-rss** on your local computer you might want to run the job as a regular user [cron job](https://geek-university.com/user-cron-jobs/).

# Final notes

For any other questions or suggestions, please open an issue and I'll try to respond to the best of my abilities.

As usual, code contributions are welcome.
