# mangadex-rss

A mangadex rss generator for the new site (v5)

# How to run

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
