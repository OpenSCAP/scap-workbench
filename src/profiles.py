#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2010 Red Hat Inc., Durham, North Carolina.
# All Rights Reserved.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
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

logger = logging.getLogger("OSCAPEditor")

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
        #self.profile_details = ProfileDetails(self.core, self)

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
        self.btn_extend = self.builder.get_object("tailoring:profiles:btn_extend")
        self.btn_extend.connect("clicked", self.__cb_extend)
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
            else: self.profile_title.set_text(details["titles"][details["titles"].keys()[0]] or "")
         
            if len(details["descriptions"]) == 0:
                 self.__set_description("")
            else:
                if self.core.selected_lang in details["descriptions"]: 
                    self.__set_description(details["descriptions"][self.core.selected_lang])
                else: self.__set_description(details["descriptions"][details["descriptions"].keys()[0]])

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
    def __cb_add(self, widget):
        pass

    def __cb_extend(self, widget):
        pass

    def __cb_copy(self, widget):
        pass

    def __cb_delete(self, widget):
        pass

    def __cb_save(self, widget):
        self.data_model.save()


class NewProfileWindow(abstract.Window):
    """
    GUI for create new profile.
    """
    def __init__(self, action="add", core=None):
        """
        @param action type of creating profile (copy, extend, new)
        """
        self.core = core
        self.action = action
        self.draw_window()

    #set function
    def set_abstract(self, abstract):
        """
        Set if new profal is abstract or not.
        @param abstract True/False - Yes/No
        """
        if abstract == True:
            self.label_abstract = "Yes"
        else:
            self.label_abstract = "No"
    
    def set_extend(self, text):
        """
        Set id profile.
        @param text
        """
        self.label_extend = text

    def set_version(self, text):
        """
        Set version of profile.
        @param text
        """
        self.entry_version = text
        
    def set_language(self, languages, active):
        """
        Set list of languades for comboBox and set active.
        @param languages List of laguages name.
        @param active Number of active item in list
        """
        model = self.cBox_language.get_model()
        model.clear()
        for lan in languages:
            model.append([lan])
        self.cBox_language.set_active(active)

    def set_title(self, text):
        """
        Set title to the textView.
        @param text Text with title
        """
        textbuffer = self.texView_title.get_buffer()
        textbuffer.set_text(text)
        
    def set_descriprion(self, text):
        """
        Set description to the textView.
        @param text Text with description
        """
        textbuffer = self.texView_description.get_buffer()
        textbuffer.set_text(text)

    #callBack function
    def cb_abstract(self, combobox):
        model = combobox.get_model()
        index = combobox.get_active()

    def cb_version(self, entry):
        pass
    
    def cb_language(self, combobox):
        model = combobox.get_model()
        index = combobox.get_active()

    def cb_textView(self, widget, data=None):
        print data

    def cb_btn(self, button, data=None):
        pass
    
    def delete_event(self, widget, event, data=None):
        self.window.destroy()
    
    # draw function
    def add_frame_cBox(self, body, text, expand):
        frame = gtk.Frame(text)
        label = frame.get_label_widget()
        label.set_use_markup(True)        
        frame.set_shadow_type(gtk.SHADOW_NONE)
        if expand: body.pack_start(frame, True, True)
        else: body.pack_start(frame, False, True)
        alig = gtk.Alignment(0.5, 0.5, 1, 1)
        alig.set_padding(0, 0, 12, 0)
        frame.add(alig)
        return alig

    def add_label(self,table, text, left, right, top, bottom, x=gtk.FILL, y=gtk.FILL):
        label = gtk.Label(text)
        table.attach(label, left, right, top, bottom, x, y)
        label.set_alignment(0, 0.5)
        return label
        
    def draw_window(self):
        # Create a new window
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("New profile")
        self.window.set_size_request(600, 400)
        self.window.set_modal(True)
        self.window.connect("delete_event", self.delete_event)
        
        # for insert data
        vbox = gtk.VBox()
        alig = self.add_frame_cBox(vbox, "<b>New</b>", True)
        table = gtk.Table()
        table.set_row_spacings(4)
        
        self.add_label(table, "Abstract: ", 0, 1, 0, 1)
        self.add_label(table, "Extend: ", 0, 1, 1, 2)
        self.add_label(table, "Version: ", 0, 1, 2, 3)
        self.add_label(table, "Language: ", 0, 1, 3, 4)
        self.add_label(table, "Title: ", 0, 1, 4, 5)
        self.add_label(table, "Description: ", 0, 1, 5, 6)
        
        if self.action == "add":
            self.cBox_language = gtk.ComboBox()
            model = gtk.ListStore(str)
            cell = gtk.CellRendererText()
            self.cBox_language.pack_start(cell)
            self.cBox_language.add_attribute(cell, 'text', 0)
            self.cBox_language.set_model(model)
            self.cBox_language.connect('changed', self.cb_abstract)
            table.attach(self.cBox_language, 1, 2, 0, 1,gtk.FILL,gtk.FILL)
            self.set_language(["No", "Yes"], 0)
        else:
            self.label_abstract = self.add_label(table, "None ", 1, 2, 0, 1)
        self.label_extend = self.add_label(table, "None ", 1, 2, 1, 2)

        self.entry_version = gtk.Entry()
        self.entry_version.connect("selection-notify-event", self.cb_version, "version")
        table.attach(self.entry_version, 1, 2, 2, 3, gtk.EXPAND|gtk.FILL, gtk.FILL)

        self.cBox_language = gtk.ComboBox()
        model = gtk.ListStore(str)
        cell = gtk.CellRendererText()
        self.cBox_language.pack_start(cell)
        self.cBox_language.add_attribute(cell, 'text', 0)
        self.cBox_language.set_model(model)
        self.cBox_language.connect('changed', self.cb_language)
        table.attach(self.cBox_language, 1, 2, 3, 4,gtk.FILL,gtk.FILL)

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.texView_title = gtk.TextView()
        self.texView_title.connect("selection-notify-event", self.cb_textView, "title")
        sw.add(self.texView_title)
        table.attach(sw, 1, 2, 4, 5, gtk.EXPAND|gtk.FILL, gtk.EXPAND|gtk.FILL)
        
        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.texView_description = gtk.TextView()
        self.texView_title.connect("selection-notify-event", self.cb_textView, "description")
        sw.add(self.texView_description)
        table.attach(sw, 1, 2, 5, 6, gtk.EXPAND|gtk.FILL, gtk.EXPAND|gtk.FILL)

        alig.add(table)
        #operationes
        box = gtk.HButtonBox()
        box.set_layout(gtk.BUTTONBOX_END)

        btn = gtk.Button("Create")
        btn.connect("clicked", self.cb_btn, "create")
        box.add(btn)

        btn = gtk.Button("Cancel")
        btn.connect("clicked", self.cb_btn, "cancel")
        box.add(btn)

        vbox.pack_start(box, False, True)

        vbox.pack_start(gtk.Statusbar(), False, True)
        self.window.add(vbox)
        self.window.show_all()

    def destroy_window(self):
        self.window.destroy()


