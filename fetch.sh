#!/usr/bin/env bash
# Python's virtual environment and mangadex-rss requirements preparation (do it only once):
#python3 -m venv ./venv/
#./bin/pip install -r requirements.txt

# Configuration:
path="."
export username=your_mangadex-user
export password=your_mangadex-password
export languages='en,fr'
export feed_file="${path}/rss.xml"
#export loglevel=DEBUG
export fetch_limit=50
venv="${path}/venv/bin"

rmifexist() {
if [[ -e $1 ]];
then
  rm $1
fi
}

#rmifexist ./mangadex.xml
#rmifexist ./cache.bin

${venv}/python3 ${path}/main.py

