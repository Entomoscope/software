#! /usr/bin/python3

from datetime import datetime, timedelta

# Récupération de la date du jour
TODAY_NOW = datetime.now()
# Date du jour sous la forme YYYYMMDD
TODAY = TODAY_NOW.strftime('%Y%m%d')

# Récupération de la date de demain
TOMORROW_NOW = datetime.now() + timedelta(1)
# Date de demain sous la forme YYYYMMDD
TOMORROW = TOMORROW_NOW .strftime('%Y%m%d')
