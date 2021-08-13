# mangadex-rss
A mangadex rss generator for the new site (v5)

# How to run

```bash
# Clone this repo
git clone https://github.com/marceloslacerda/mangadex-rss
cd mangadex-rss

# Install the requirements
pip  install requirements.txt

# Set your mangadex credentials
export username=myusername
export password=mypassword

# Set where the generator should put the generated feed file (optional)
export feed_file=/var/www/html/manga-feed.rss

# Run
python main.py
```
