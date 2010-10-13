# -*- coding: utf-8 -*-
#
# Copyright 2010 Red Hat Inc., Durham, North Carolina.
# All Rights Reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#      Maros Barabas        <mbarabas@redhat.com>
#      Vladimir Oberreiter  <xoberr01@stud.fit.vutbr.cz>

import pygtk
import gtk
import gobject
import pango

import abstract
import logging
import core
from events import EventObject

    
import commands
import filter
import render

from htmltextview import HtmlTextView

logger = logging.getLogger("scap-workbench")

class ProfileList(abstract.List):
    
    def __init__(self, widget, core):
        self.core = core
        self.data_model = commands.DHProfiles(core)
        abstract.List.__init__(self, "gui:tailoring:profiles:profile_list", core, widget)

        selection = self.get_TreeView().get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)

        # actions
        self.add_sender(self.id, "show")
        self.add_sender(self.id, "profile_changed")
        self.add_receiver("gui:btn:tailoring:profiles", "update", self.__update)
        self.add_receiver("gui:tailoring:profiles:profile_list", "update", self.__show)
        selection.connect("changed", self.cb_item_changed, self.get_TreeView())

    def __show(self):
        if "profile" not in self.__dict__ or self.profile != self.core.selected_profile:
            self.profile = self.core.selected_profile

    def __update(self):
        if "profile" not in self.__dict__ or self.profile != self.core.selected_profile or self.core.force_reload_profiles:
            self.data_model.fill()
            self.get_TreeView().get_model().foreach(self.set_selected, (None, self.get_TreeView()))
            self.core.force_reload_profiles = False

    def cb_item_changed(self, widget, treeView):

        selection = treeView.get_selection( )
        if selection != None: 
            (model, iter) = selection.get_selected( )
            if iter: self.core.selected_profile = model.get_value(iter, 0)
        self.emit("update")


class ProfileDetails(EventObject):

    def __init__(self, core, guiProfiles):
        
        #create view
        self.core = core
        self.guiProfiles = guiProfiles
        EventObject.__init__(self, self.core)
 

class MenuButtonProfiles(abstract.MenuButton):
    """
    GUI for profiles.
    """
    def __init__(self, builder, widget, core):
        abstract.MenuButton.__init__(self, "gui:btn:tailoring:profiles", widget, core)
        self.builder = builder
        self.core = core
        self.widget = widget
        self.data_model = commands.DHProfiles(self.core)
        
        # draw body
        self.body = self.builder.get_object("tailoring:profiles:box")

        self.profiles_list = ProfileList(self.builder.get_object("tailoring:profiles:treeview"), self.core)

        """Get labels for details
        """
        self.profile_id = self.builder.get_object("tailoring:profiles:details:lbl_id")
        self.profile_abstract = self.builder.get_object("tailoring:profiles:details:lbl_abstract")
        self.profile_extend = self.builder.get_object("tailoring:profiles:details:lbl_extend")
        self.profile_version = self.builder.get_object("tailoring:profiles:details:lbl_version")
        self.profile_title = self.builder.get_object("tailoring:profiles:details:lbl_title")
        render.label_set_autowrap(self.profile_title)

        """Get buttons from Builder and connect callbacks
        """
        self.btn_add = self.builder.get_object("tailoring:profiles:btn_add")
        self.btn_add.connect("clicked", self.__cb_add)
        self.btn_copy = self.builder.get_object("tailoring:profiles:btn_copy")
        self.btn_copy.connect("clicked", self.__cb_copy)
        self.btn_delete = self.builder.get_object("tailoring:profiles:btn_delete")
        self.btn_delete.connect("clicked", self.__cb_delete)
        self.btn_save = self.builder.get_object("tailoring:profiles:btn_save")
        self.btn_save.connect("clicked", self.__cb_save)

        self.profile_description = HtmlTextView()
        self.profile_description.show()
        box = self.builder.get_object("tailoring:profiles:details:box_description")
        self.builder.get_object("label1").realize()
        bg_color = self.builder.get_object("label1").get_style().bg[gtk.STATE_NORMAL]
        self.profile_description.set_wrap_mode(gtk.WRAP_WORD)
        self.profile_description.modify_base(gtk.STATE_NORMAL, bg_color)
        box.pack_start(self.profile_description, True, True)

        self.add_sender(self.id, "update")
        self.add_receiver("gui:tailoring:profiles:profile_list", "update", self.__update)
        self.add_receiver("gui:tailoring:profiles:profile_list", "changed", self.__update)
        self.add_receiver("gui:btn:main:xccdf", "lang_changed", self.__update)
        
    def __update(self):

        details = self.data_model.get_profile_details(self.core.selected_profile)
        if details != None:
            self.profile_id.set_text(details["id"] or "")
            self.profile_abstract.set_text(str(details["abstract"]))
            self.profile_extend.set_text(str(details["extends"] or ""))
            self.profile_version.set_text(details["version"] or "")

            if self.core.selected_lang in details["titles"]: 
                self.profile_title.set_text(details["titles"][self.core.selected_lang] or "")
            else: self.profile_title.set_text("Unknown")
         
            if len(details["descriptions"]) == 0:
                 self.__set_description("")
            else:
                if self.core.selected_lang in details["descriptions"]: 
                    self.__set_description(details["descriptions"][self.core.selected_lang])
                else: self.__set_description("Unknown")

        else:
            self.profile_id.set_text("")
            self.profile_abstract.set_text("")
            self.profile_extend.set_text("")
            self.profile_version.set_text("")
            self.profile_title.set_text("")
            self.__set_description("")
    
    #set functions
    def __set_description(self, description):
        """
        Set description to the textView.
        @param text Text with description
        """
        self.profile_description.get_buffer().set_text("")
        if description == "": description = "No description"
        description = "<body>"+description+"</body>"
        self.profile_description.display_html(description)
        
    #callBack functions
    def __cb_add(self, widget, values=None):
        if not self.core.lib:
            logger.error("Library not initialized or XCCDF file not specified")
            return False
        window = NewProfileWindow(self.core, self.__cb_add_profile, values)
        window.show()

    def __cb_add_profile(self, values):
        logger.debug("New profile window returned: %s", values)
        # TODO: Add profile and emit update ?
        self.data_model.add(values)
        self.core.force_reload_profiles = True
        self.emit_signal("update")

    def __cb_copy(self, widget):
        pass

    def __cb_delete(self, widget):
        pass

    def __cb_save(self, widget):
        if not self.core.lib:
            logger.error("Library not initialized or XCCDF file not specified")
            return False
        self.data_model.save()


class NewProfileWindow(abstract.Window):
    """
    GUI for create new profile.
    """
    def __init__(self, core, cb, values=None):
        """
        @param action type of creating profile (copy, extend, new)
        """
        self.core = core
        self.__cb = cb
        self.__values = values
        self.data_model = commands.DataHandler(core)

        self.builder = gtk.Builder()
        self.builder.add_from_file("/usr/share/scap-workbench/new_profile.glade")

        self.btn_add = self.builder.get_object("btn_add")
        self.btn_add.connect("clicked", self.__cb_add)
        self.btn_cancel = self.builder.get_object("btn_cancel")
        self.btn_cancel.connect("clicked", self.__delete_event)
        self.btn_ok = self.builder.get_object("btn_ok")
        self.btn_ok.connect("clicked", self.__cb_ok)

        # info box
        self.info_box = self.builder.get_object("info_box:alig")
        self.builder.get_object("info_box:eb").modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color("#FFFFC0"))
        self.builder.get_object("info_box:btn").connect("clicked", self.__cb_info_close)
        self.info_box_lbl = self.builder.get_object("info_box:lbl")

        self.entry_id = self.builder.get_object("entry_id")
        self.cbentry_lang = self.builder.get_object("cbentry_lang")
        for lang in self.core.langs:
            self.cbentry_lang.get_model().append([lang])
        self.entry_title = self.builder.get_object("entry_title")
        self.entry_version = self.builder.get_object("entry_version")
        self.entry_description = self.builder.get_object("entry_description")
        self.cbox_abstract = self.builder.get_object("cbox_abstract")
        self.cbox_abstract.set_tooltip_text("You can't add abstract profile in tailoring")

        self.cb_extends = self.builder.get_object("cb_extends")
        self.cb_extends.connect("changed", self.__cb_extends_changed)
        self.cb_extends.set_sensitive(False)
        self.cb_extends.set_tooltip_text("You can't extend profile in tailoring")

        self.profiles_model = gtk.ListStore(str, str)
        self.cb_extends.set_model(self.profiles_model)
        cell = gtk.CellRendererText()
        self.cb_extends.pack_start(cell, False)
        self.cb_extends.add_attribute(cell, 'text', 0)
        cell = gtk.CellRendererText()
        self.cb_extends.pack_start(cell, True)
        self.cb_extends.add_attribute(cell, 'text', 1)

        model = self.cb_extends.get_model()
        profiles = self.data_model.get_profiles()
        model.append([None, ''])
        for profile in profiles:
            logger.debug("Appending \"%s\" model", profiles[0])
            model.append(profile)

        self.tw_langs = self.builder.get_object("tw_langs")
        selection = self.tw_langs.get_selection()
        selection.connect("changed", self.__cb_lang_changed)

        self.langs_model = gtk.ListStore(str, str, str)
        self.tw_langs.set_model(self.langs_model)
        self.tw_langs.append_column(gtk.TreeViewColumn("Lang", gtk.CellRendererText(), text=0))
        self.tw_langs.append_column(gtk.TreeViewColumn("Title", gtk.CellRendererText(), text=1))
        self.tw_langs.append_column(gtk.TreeViewColumn("Description", gtk.CellRendererText(), text=2))

        self.window = self.builder.get_object("new_profile:dialog")
        self.window.connect("delete-event", self.__delete_event)

    def __cb_extends_changed(self, widget):
        if widget.get_active() == 0: self.info_box.hide()
        else:
            self.info_box_lbl.set_text("For all attributes will be set \"overide\" parameter.")
            self.info_box.show_all()

    def __cb_info_close(self, widget):
        self.info_box.hide()

    def __cb_lang_changed(self, widget):
        selection = self.tw_langs.get_selection( )
        if selection != None: 
            (model, iter) = selection.get_selected( )
            if iter: 
                self.cbentry_lang.set_text(model.get_value(iter, 0))
                self.entry_title.set_text(model.get_value(iter, 1))
                self.entry_description.get_buffer().set_text(model.get_value(iter, 2))
        

    def __cb_add(self, widget):

        result = None
        for row in self.langs_model:
            if row[0] == self.cbentry_lang.get_active_text():
                md = gtk.MessageDialog(self.window, 
                        gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION,
                        gtk.BUTTONS_YES_NO, "Language \"%s\" already specified.\n\nRewrite stored data ?" % (row[0],))
                md.set_title("Language found")
                result = md.run()
                md.destroy()
                if result == gtk.RESPONSE_NO: 
                    return
                else: self.langs_model.remove(row.iter)

        buffer = self.entry_description.get_buffer()
        self.langs_model.append([self.cbentry_lang.get_active_text(), 
            self.entry_title.get_text(),
            buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)])

        # Add lang to combo box model
        found = False
        for item in self.cbentry_lang.get_model():
            if item[0] == self.cbentry_lang.get_active_text(): 
                found = True
        if not found: 
            self.cbentry_lang.get_model().append([self.cbentry_lang.get_active_text()])
            self.cbentry_lang.set_active_iter(self.cbentry_lang.get_model()[-1].iter)
            self.core.langs.append(self.cbentry_lang.get_active_text())

        # Clear
        self.cbentry_lang.set_active(-1)
        self.entry_title.set_text("")
        self.entry_description.get_buffer().set_text("")

    def show(self):
        self.window.set_transient_for(self.core.main_window)
        self.window.show()

    def __cb_ok(self, widget):
        if self.entry_id.get_text() == "":
            logger.error("No ID specified")
            md = gtk.MessageDialog(self.window, 
                    gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR,
                    gtk.BUTTONS_OK, "ID of profile has to be specified !")
            md.run()
            md.destroy()
            return
        values = {}
        values["id"] = self.entry_id.get_text()
        values["abstract"] = self.cbox_abstract.get_active()
        values["version"] = self.entry_version.get_text()
        if self.cb_extends.get_active() >= 0: values["extends"] = self.cb_extends.get_model()[self.cb_extends.get_active()][0]
        else: values["extends"] = None
        values["details"] = []
        for row in self.langs_model:
            item = {"lang": row[0],
                    "title": row[1],
                    "description": row[2]}
            values["details"].append(item)

        self.window.destroy()
        self.__cb(values)

    def __delete_event(self, widget, event=None):
        self.window.destroy()
