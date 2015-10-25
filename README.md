# warning!
It's very alpha and might mess up your Tracker database. Don't use it in production.

## nautilus-tags-tab
Nautilus 3.x plugin for managing file tags

It's a rewrite of tracker-tags-tab.py plugin created by Edward B. Duffy back in the day. Tested on Nautilus version 3.2.12 (GTK3 based), uses Sparql to query Tracker.

## Instalation
Make sure Nautilus is not running: `killall nautilus`
Place the tracker-tags-tab.py file in `~/.local/share/nautilus-python/extensions/` directory
... and start Nautilus again.
Go to Preferences -> List Columns and check new column called `Tags`.
![alt tag](https://raw.github.com/lusk/nautilus-tags-tab/master/screenshots/activation.png)
Now select any file (or files), right-click them, select properties and go to `Tags` tab to add some tags.
![alt tag](https://raw.github.com/lusk/nautilus-tags-tab/master/screenshots/usage.png)
Your tags should be visible next to the files in list view. It might need a refresh sometimes...
Anyway, the nice thing about all this is, that now you can searched for your files using tags the same super-fast-way you run applications in dash. Just make sure you have installed also this extension - https://github.com/hamiller/tracker-search-provider/tree/gnome_16
