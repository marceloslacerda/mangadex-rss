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
4. [OPTIONAL] Set where the generator should put the generated feed file.
   ```bash
   export feed_file=/var/www/html/manga-feed.rss
   ```

5. [OPTIONAL] Set which languages to filter.
   ```bash
   export languages='en,es'
   ```
6. Run.
   ```bash
   python main.py
   ```
