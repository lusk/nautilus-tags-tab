# warning!
It's very alpha and might mess up your Tracker database. Don't use it in production.

## nautilus-tags-tab
Nautilus 3.x plugin for managing file tags

It's a rewrite of tracker-tags-tab.py plugin created by Edward B. Duffy back in the day. Tested on Nautilus version 3.2.12 (GTK3 based), uses Sparql to query Tracker.

## Instalation
Make sure Nautilus is not running: `killall nautilus`
Place the tracker-tags-tab.py file in `~/.local/share/nautilus-python/extensions/` directory
... and start Nautilus again. You should be now able to select new visible column called `Tags` and there is a new tab `Tag` in the properties window of every file.
