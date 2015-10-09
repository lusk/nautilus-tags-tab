#  Copyright (C) 2006/7, Edward B. Duffy <eduffy@gmail.com>
#  Copyright (C) 2015, Lukas Stancik <lukas.stancik@gmail.com>
#  Version: 0.9.0
#  tracker-tags-tab.py:  Tag your files in your Tracker database
#                        via Nautilus's property dialog.
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc.,  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import os
os.environ["NAUTILUS_PYTHON_REQUIRE_GTK3"] = "1"

import hashlib
import urllib

from gi.repository import Nautilus, Gtk, GObject, Gio, Tracker
from gi.repository.GLib import GError

# -------------------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------------------
# Info column
# -------------------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------------------

class ColumnExtension(GObject.GObject, Nautilus.ColumnProvider, Nautilus.InfoProvider):
    def __init__(self):
        self.conn = Tracker.SparqlConnection.get (None)
        pass

    def get_tags(self, path):
        file_tags = []

        query = """
            SELECT ?labels
            WHERE {
                ?f nie:isStoredAs ?as ;
                    nao:hasTag ?tags .
                ?as nie:url '%s' .
                ?tags a nao:Tag ;
                    nao:prefLabel ?labels .
            } ORDER BY ASC(?labels)
        """ % path

        cursor = self.conn.query (query, None)

        if not cursor:
            pass
        else:
            i = 0
            while (cursor.next (None)):
                i+=1
                file_tags.append(cursor.get_string(0)[0])
            # print "File %(path)s has tags: %(tags)s" % {'path': path, 'tags': file_tags}

        return ','.join(file_tags)

    def get_columns(self):
        ip = Nautilus.Column(name="NautilusPython::tags_column",
                               attribute="tags",
                               label="Tags",
                               description="Get all tags")
        return [ip]

    def update_file_info(self, file):
        if file.get_uri_scheme() != 'file':
            return

        file.add_string_attribute('tags', self.get_tags(file.get_uri()))

# -------------------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------------------
# Properties tab
# -------------------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------------------

class TagPropertyPage(GObject.GObject, Nautilus.PropertyPageProvider):
    def __init__(self):
        self.conn = Tracker.SparqlConnection.get (None)
        pass

    # Adds a new row with empty string to the store
    def _on_add_tag(self, button):
        # print "_on_add_tag"
        self.store.append([False, ''])

    # Removes or adds a tag to all selected files when checkbox state changes
    def _on_toggle(self, cell, path, files):
        # print "_on_toggle"
        on = not self.store.get_value(self.store.get_iter(path), 0)
        self.store.set_value(self.store.get_iter(path), 0, on)
        tag = self.store.get_value(self.store.get_iter(path), 1)
        if on: func = self.add_tag
        else:  func = self.remove_tag
        for f in files:
            func(f.get_uri(), tag)

    # Updates a tag in all selected files when changed
    def _on_edit_tag(self, cell, path, text, files):
        # print "_on_edit_tag"
        old_text = self.store.get_value(self.store.get_iter(path), 1)
        on = self.store.get_value(self.store.get_iter(path), 0)
        if on:
            for f in files:
                # First remove the old tag
                self.remove_tag(f.get_uri(),old_text)
                # Then add the new one
                self.add_tag(f.get_uri(),text)
        self.store.set_value(self.store.get_iter(path), 1, text)

    # This takes the tags in store and concatenates them into the entry field
    # it is triggered with every change to the store
    def _on_update_tag_summary(self, store, path, iter):
        # print "_on_update_tag_summary"
        tags = [ ]
        for row in store:
            if row[0]:
                tags.append(row[1])
                self.entry_tag.handler_block(self.entry_changed_id)
                self.entry_tag.set_text(','.join(tags))
                self.entry_tag.handler_unblock(self.entry_changed_id)

    # This is triggered anytime there has been change to the store
    def _on_tag_summary_changed(self, entry, files):
        # print "_on_tag_summary_changed"
        # get a set of new tags from entry field
        new_tags = set(entry.get_text().split(','))
        # remove the empty string
        new_tags.discard('')

        for f in files:
            # get current tags from the files
            old_tags = set(self.get_tags(f.get_uri()))
            # get list of tags to be removed from the file
            to_be_removed = list(old_tags.difference(new_tags))
            # get list of tags to be added to the file
            to_be_added = list(new_tags.difference(old_tags))

            # remove tags
            if to_be_removed:
                # print "to_be_removed"
                # print to_be_removed
                for tag in to_be_removed:
                    self.remove_tag(f.get_uri(),tag)

            # add tags
            if to_be_added:
                # print "to_be_added"
                # print to_be_added
                for tag in to_be_added:
                    self.add_tag(f.get_uri(),tag)

            # check-box list needs to be updated (remove outdated tags, add the new ones)

            # suspend watching of changes in store
            self.store.handler_block(self.store_changed_id)

            # the set of all tags most likely changed, get fresh temporary set from all the files
            all_tags = set()
            for f in files:
                for tag in self.get_tags(f.get_uri()):
                    all_tags.add(tag)

            # and update the store according to the fresh tags set
            i = 0
            while i < len(self.store):
                # print self.store[i][1] + " in all_tags" + self.store[i][1] in all_tags

                # if the tag in store is in the fresh set of tags
                if self.store[i][1] in all_tags:
                    # set its bool value to true if it is also in new_tags, false otherwise
                    self.store[i][0] = (self.store[i][1] in new_tags)
                    # remove it form the fresh set (its only temporary anyway)
                    all_tags.remove(self.store[i][1])
                    i += 1
                # if the tag is not to be found in all_tags remove it from store
                else:
                    del self.store[i]
            # inside all_tags are now only new tags left, lets add them to the store
            for t in all_tags:
                self.store.append([True, t])

            # resume watching changes to the store
            self.store.handler_unblock(self.store_changed_id)

    def remove_tag(self, path, tag):
        # print "remove_tag"
        # TODO: find out if the tag to be added already exists or not and act accordingly
        query = """
            DELETE {
                ?unknown nao:hasTag ?id
            } WHERE {
                ?unknown nie:isStoredAs ?as .
                ?as nie:url '%(path)s' .
                ?id nao:prefLabel '%(tag)s'
            }
        """ % { "tag": tag, "path": path }

        try:
            self.conn.update (query, 0, Gio.Cancellable())
            # print "Removed '" + tag + "' tag from " + path
        except Exception, e:
            # print e
            raise e

    def tag_exists(self, tag_label):
        if self.conn:
            squery = """
                SELECT ?tag
                WHERE {
                    ?tag a nao:Tag .
                    ?tag nao:prefLabel '%s' .
                }
            """ % tag_label

            cursor = self.conn.query (squery, None)

            while (cursor.next (None)):
                if cursor.get_string(0)[0]:
                    # print "Tag already exists"
                    return True
                else:
                    # print "Tag does not exist"
                    return False
        else:
            raise Exception("Couldn't get a proper SPARQL connection")
            return False

    def new_tag(self, tag_label):
        if self.conn:
            uquery = ("INSERT { _:tag a nao:Tag ; nao:prefLabel '%s' .}"
                      "WHERE { OPTIONAL { ?tag a nao:Tag ; nao:prefLabel '%s' } ."
                      "FILTER (!bound(?tag)) }") % (tag_label, tag_label)
            cursor = self.conn.update(uquery, 0, Gio.Cancellable())
            # print "Created new tag: " + tag_label
            return True
        else:
            raise Exception("Couldn't get a proper SPARQL connection")
            return False

    def existing_tag(self, path, tag_label):
        if self.conn:
            uquery = """
                INSERT {
                    ?unknown nao:hasTag ?id
                } WHERE {
                    ?unknown nie:isStoredAs ?as .
                    ?as nie:url '%(path)s' .
                    ?id nao:prefLabel '%(tag_label)s'
                }
            """ % { "tag_label": tag_label, "path": path }

            cursor = self.conn.update(uquery, 0, Gio.Cancellable())
            # print "File tagged with existing tag: " + tag_label
            return True
        else:
            raise Exception("Couldn't get a proper SPARQL connection")
            return False

    def add_tag(self, path, tag_label):
        if self.tag_exists(tag_label): # Tag already exists?
            return self.existing_tag(path, tag_label) # cool, use it
        elif self.new_tag(tag_label): # It does not? Crete it
            return self.existing_tag(path, tag_label) # and tag the file with it
        else:
            return False

    def get_tags(self,path):
        if self.conn:
            squery = """
                SELECT ?labels
                WHERE {
                    ?f nie:isStoredAs ?as ;
                        nao:hasTag ?tags .
                    ?as nie:url '%s' .
                    ?tags a nao:Tag ;
                        nao:prefLabel ?labels .
                } ORDER BY ASC(?labels)
            """ % path

            cursor = self.conn.query(squery, None)

            tag_list = []
            while (cursor.next (None)):
                tag_list.append(cursor.get_string(0)[0])

            # print "File %(path)s has tags: %(tags)s" % {'path': path, 'tags': tag_list}
            return tag_list
        else:
            raise Exception("Couldn't get a proper SPARQL connection")
            return False

    def get_property_pages(self, files):
        # Everytime the options window is displayed start with empty set
        self.all_tags_set = set()

        # Create dictionary with path as a key and a list of tags as values
        tags_by_path = { }

        for f in files:
            if f.get_uri_scheme() != 'file':
                pass
            else:
                # Get filepath as string like '/home/user/file.txt'
                file_path = urllib.url2pathname(f.get_uri()[7:])
                # Get all tags for a file
                tags_for_path = self.get_tags(f.get_uri())
                # Push the tags under path key into tags_by_path dictionary
                tags_by_path[file_path] = tags_for_path
                # And also put them in the all_tags set
                for tag in tags_for_path:
                    self.all_tags_set.add(tag)

        # Create another dictionary with tag as a key and 0 as an initial value for usage count
        tags_usage_count = dict([ (t,0) for t in self.all_tags_set ])

        # Go through all the files
        for f in files:
            # And for every tag of every file
            for t in tags_by_path[urllib.url2pathname(f.get_uri()[7:])]:
                # Raise the usage count
                tags_usage_count[t] += 1

        # This is the top level container
        main = Gtk.VBox()

        # Entry field for comma separated tags
        tags_csv = Gtk.HBox()
        tags_csv.set_border_width(6)
        tags_csv.set_spacing(12)
        self.entry_tag = Gtk.Entry()
        tags_csv.pack_start(Gtk.Label('Tags: '), False, False, 0)
        tags_csv.pack_start(self.entry_tag, True, True, 0)

        # Add the entry field to top level container
        main.pack_start(tags_csv, False, False, 0)

        # Track changes to the entry field
        self.entry_changed_id = self.entry_tag.connect(
            'activate', self._on_tag_summary_changed, files)

        # Scrolling window with tags and checkboxes in front of them
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_shadow_type(Gtk.ShadowType.ETCHED_OUT)

        # Store for all the tags accross all selected files
        # bool: Is the tag in all the selected files or not
        # str: Tag label
        self.store = Gtk.ListStore(bool, str)

        self.store_changed_id = self.store.connect(
            'row-changed', self._on_update_tag_summary)

        # Fill the store with items from all tags set
        for tag in self.all_tags_set:
            # This also triggers _on_update_tag_summary
            iter = self.store.append([False, tag])
            # If the usage count matches number of all selected files, set bool parameter to true
            if tags_usage_count[tag] == len(files):
                self.store.set_value(iter, 0, True)
            # If the tag is not used at all, set it to false
            elif tags_usage_count[tag] == 0:
                self.store.set_value(iter, 0, False)
            # Cry in the stdout otherwise
            else:
                # print 'inconsistant'
                pass

        # Create a TreeView container
        treeview = Gtk.TreeView(self.store)
        treeview.set_headers_visible(False)

        # Add a column with a checkbox and watch for it's changes
        column_toggle = Gtk.TreeViewColumn()
        treeview.append_column(column_toggle)
        tag_state = Gtk.CellRendererToggle()
        column_toggle.pack_start(tag_state, True)
        column_toggle.add_attribute(tag_state, 'active', 0)
        tag_state.connect('toggled', self._on_toggle, files)
        tag_state.set_property('activatable', True)

        # Add a column with a text, make it editable and watch for changes
        column_tag_text = Gtk.TreeViewColumn()
        treeview.append_column(column_tag_text)
        tag_text = Gtk.CellRendererText()
        column_tag_text.pack_start(tag_text, True)
        column_tag_text.add_attribute(tag_text, 'text', 1)
        tag_text.connect('edited', self._on_edit_tag, files)
        tag_text.set_property('editable', True)

        # Add the TreeView into the scrollable window
        scrolled_window.add(treeview)
        main.pack_start(scrolled_window, True, True, 0)

        # Create an "Add tag" button at the very bottom that adds an empty row to the listbox
        hbox = Gtk.HBox()
        hbox.set_border_width(6)
        btn = Gtk.Button(stock='gtk-add')
        btn.get_child().get_child().get_children()[1].props.label = '_Add Tag'
        btn.connect('clicked', self._on_add_tag)
        hbox.pack_end(btn, False, False, 0)
        main.pack_start(hbox, False, False, 0)

        # Show time!
        main.show_all()

        pp = Nautilus.PropertyPage(name="NautilusPython::tag",
                                    label=Gtk.Label('Tag'),
                                    page=main)

        # Need to return list here, took me almost a day to figure out :)
        return [pp]

