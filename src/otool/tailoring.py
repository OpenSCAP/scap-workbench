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

class ItemList(abstract.List):
    
    def __init__(self, widget, core, progress=None):
        self.core = core
        self.data_model = commands.DHItemsTree(core, progress)
        abstract.List.__init__(self, "gui:tailoring:refines:item_list", core, widget)
        self.get_TreeView().set_enable_tree_lines(True)

        selection = self.get_TreeView().get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)

        # actions
        self.add_receiver("gui:btn:tailoring:refines", "update", self.__update)
        selection.connect("changed", self.cb_item_changed, self.get_TreeView())
        self.add_sender(self.id, "item_changed")

    def __update(self):
        if "profile" not in self.__dict__ or self.profile != self.core.selected_profile:
            self.profile = self.core.selected_profile
            self.data_model.fill()
            # Select the last one selected if there is one
            self.get_TreeView().get_model().foreach(self.set_selected, (self.core.selected_item, self.get_TreeView()))

    def cb_item_changed(self, widget, treeView):

        selection = treeView.get_selection( )
        if selection != None: 
            (model, iter) = selection.get_selected( )
            if iter: self.core.selected_item = model.get_value(iter, 0)
        treeView.columns_autosize()
        self.emit("update")

class ValuesList(abstract.List):
    
    def __init__(self, widget, core):
        self.core = core
        self.data_model = commands.DHValues(core)
        abstract.List.__init__(self, "gui:tailoring:refines:values_list", core, widget)
        self.get_TreeView().set_enable_tree_lines(True)

        selection = self.get_TreeView().get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)

        # actions
        self.add_receiver("gui:tailoring:refines:item_list", "update", self.__update)
        selection.connect("changed", self.cb_item_changed, self.get_TreeView())

    def __update(self):
        self.data_model.fill()

    def cb_item_changed(self, widget, treeView):

        selection = treeView.get_selection( )
        if selection != None: 
            (model, iter) = selection.get_selected( )
            if iter: self.core.selected_deps = model.get_value(iter, 0)
            
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
        if "profile" not in self.__dict__ or self.profile != self.core.selected_profile:
            self.data_model.fill()
            self.get_TreeView().get_model().foreach(self.set_selected, (None, self.get_TreeView()))

    def cb_item_changed(self, widget, treeView):

        selection = treeView.get_selection( )
        if selection != None: 
            (model, iter) = selection.get_selected( )
            if iter: self.core.selected_profile = model.get_value(iter, 0)
        self.emit("update")


class ItemDetails(EventObject):

    def __init__(self, core):
        
        #create view
        self.core = core
        EventObject.__init__(self, self.core)
        self.data_model = commands.DataHandler(self.core)

        self.add_receiver("gui:tailoring:refines:item_list", "update", self.__update)
        self.add_receiver("gui:tailoring:refines:item_list", "changed", self.__update)
        self.draw()

    def __update(self):
        details = self.data_model.get_item_details(self.core.selected_item)
        self.id.set_text(details["id"])
        self.type.set_text(details["typetext"])
        self.weight.set_text(str(details["weight"]))

        # clear
        self.description.get_buffer().set_text("")
        self.fixes.get_buffer().set_text("")
        self.title.set_text("")
        for child in self.refBox.get_children():
            child.destroy()
        fixes = []

        if self.core.selected_lang in details["titles"]: 
            self.title.set_text(details["titles"][self.core.selected_lang])
        else: 
            for lang in details["titles"]:
                self.title.set_text(details["titles"][lang])
                break

        description = ""
        if self.core.selected_lang in details["descriptions"]: 
            description = details["descriptions"][self.core.selected_lang].replace("xhtml:","")
            description = description.replace("xmlns:", "")
        else: 
            for lang in details["descriptions"]:
                description = details["descriptions"][lang]
                break
        if description == "": description = "No description"
        description = "<body>"+description+"</body>"
        try:
            self.description.display_html(description)
        except Exception as err:
            logger.error("Exception: %s", err)
        
        for i, ref in enumerate(details["references"]):
            hbox = gtk.HBox()
            counter = gtk.Label("%d) " % (i+1,))
            counter.set_alignment(0,0)
            hbox.pack_start(counter, False, False)
            text = "<a href='%s'>%s</a>" % (ref[1], ref[0])
            label = gtk.Label(text)
            hbox.pack_start(label, True, True)
            label.set_tooltip_text(ref[1])
            label.set_use_markup(True)
            label.set_track_visited_links(True)
            label.set_line_wrap(True)
            label.set_line_wrap_mode(pango.WRAP_WORD) 
            label.set_alignment(0,0)
            label.connect("size-allocate", render.label_size_allocate)
            hbox.show_all()
            self.refBox.pack_start(hbox, True, True)

        if "fixtexts" in details: fixes.extend(details["fixtexts"])
        if "fixes" in details: fixes.extend(details["fixes"])
        text = None
        for i, fixtext in enumerate(fixes):
            if text == None: text = ""
            hbox = gtk.HBox()
            text += "    "+fixtext["text"].replace("xhtml:", "").replace("xmlns:", "")+"<br>"
        if text == None: text = "No fixes specified"
        text = "<body>"+text+"</body>"
        try:
            self.fixes.display_html(text)
        except Exception as err:
            logger.error("Exception: %s", err)

    def draw(self):
        self.box_details = gtk.VBox()

        #info (id, title, type)
        expander = gtk.Expander("<b>Info</b>")
        expander.set_expanded(True)
        label = expander.get_label_widget()
        label.set_use_markup(True)
        alig = gtk.Alignment(0.5, 0.5, 1, 1)
        alig.set_padding(0, 10, 12, 4)
        expander.add(alig)
        vbox = gtk.VBox()
        alig.add(vbox)
        vbox.pack_start(gtk.HSeparator(), expand=False, fill=False, padding=1)
        self.box_details.pack_start(expander, expand=False, fill=False, padding=1)

        #id
        hbox = gtk.HBox()
        hbox.pack_start(gtk.Label("ID: "), expand=False, fill=False, padding=1)
        self.id = gtk.Label("")
        hbox.pack_start(self.id, expand=False, fill=False, padding=1)
        vbox.pack_start(hbox, expand=False, fill=False, padding=1)

        #title
        hbox = gtk.HBox()
        hbox.pack_start(gtk.Label("Title: "), expand=False, fill=False, padding=1)
        self.title = gtk.Label("")
        self.title.set_line_wrap(True)
        self.title.set_line_wrap_mode(pango.WRAP_WORD)
        self.title.set_alignment(0,0)
        hbox.pack_start(self.title, expand=False, fill=False, padding=1)
        vbox.pack_start(hbox, expand=False, fill=False, padding=1)

        #type
        hbox = gtk.HBox()
        hbox.pack_start(gtk.Label("Type: "), expand=False, fill=False, padding=1)
        self.type = gtk.Label("")
        hbox.pack_start(self.type, expand=False, fill=False, padding=1)
        vbox.pack_start(hbox, expand=False, fill=False, padding=1)
        
        #weight
        hbox = gtk.HBox()
        hbox.pack_start(gtk.Label("Weight: "), expand=False, fill=False, padding=1)
        self.weight = gtk.Label("")
        hbox.pack_start(self.weight, expand=False, fill=False, padding=1)
        vbox.pack_start(hbox, expand=False, fill=False, padding=1)
        
        #References
        expander = gtk.Expander("<b>References</b>")
        expander.set_expanded(False)
        label = expander.get_label_widget()
        label.set_use_markup(True)
        alig = gtk.Alignment(0.5, 0.5, 1, 1)
        alig.set_padding(0, 10, 12, 4)
        expander.add(alig)
        vbox = gtk.VBox()
        alig.add(vbox)
        vbox.pack_start(gtk.HSeparator(), expand=False, fill=True, padding=3)
        self.refBox = gtk.VBox()
        vbox.pack_start(self.refBox, expand=False, fill=False, padding=0)
        self.box_details.pack_start(expander, expand=False, fill=False, padding=1)
        
        # Get the background color from window and destroy it
        window = gtk.Window()
        nb = gtk.Notebook()
        window.add(nb)
        window.realize()
        nb.realize()
        bg_color = nb.get_style().bg[gtk.STATE_NORMAL]
        window.destroy()

        #fixes
        expander = gtk.Expander("<b>Fixes</b>")
        expander.set_expanded(False)
        label = expander.get_label_widget()
        label.set_use_markup(True)
        alig = gtk.Alignment(0, 0, 1, 1)
        alig.set_padding(0, 10, 12, 4)
        vbox = gtk.VBox()
        alig.add(vbox)
        vbox.pack_start(gtk.HSeparator(), expand=False, fill=False, padding=3)
        self.fixes = HtmlTextView()
        self.fixes.set_wrap_mode(gtk.WRAP_WORD)
        self.fixes.modify_base(gtk.STATE_NORMAL, bg_color)
        sw = gtk.ScrolledWindow()
        sw.set_property("hscrollbar-policy", gtk.POLICY_AUTOMATIC)
        sw.set_property("vscrollbar-policy", gtk.POLICY_AUTOMATIC)
        sw.set_property("border-width", 0)
        sw.add(self.fixes)
        sw.show()
        expander.add(alig)
        vbox.pack_start(sw, expand=False, fill=False, padding=1)
        self.box_details.pack_start(expander, expand=False, fill=False, padding=1)

        #description
        expander = gtk.Expander("<b>Description</b>")
        expander.set_expanded(True)
        label = expander.get_label_widget()
        label.set_use_markup(True)
        alig = gtk.Alignment(0, 0, 1, 1)
        alig.set_padding(0, 10, 12, 4)
        vbox = gtk.VBox()
        alig.add(vbox)
        vbox.pack_start(gtk.HSeparator(), expand=False, fill=False, padding=3)
        self.description = HtmlTextView()
        self.description.set_wrap_mode(gtk.WRAP_WORD)
        self.description.modify_base(gtk.STATE_NORMAL, bg_color)
        sw = gtk.ScrolledWindow()
        sw.set_property("hscrollbar-policy", gtk.POLICY_AUTOMATIC)
        sw.set_property("vscrollbar-policy", gtk.POLICY_AUTOMATIC)
        sw.set_property("border-width", 0)
        sw.add(self.description)
        sw.show()
        expander.add(alig)
        vbox.pack_start(sw, expand=True, fill=True, padding=1)
        self.box_details.pack_start(expander, expand=True, fill=True, padding=1)

class RefineDetails(EventObject):
    
    def __init__(self, core):
        #create view
        self.core = core
        EventObject.__init__(self, self.core)
        self.data_model = commands.DataHandler(self.core)

        self.add_receiver("gui:tailoring:refines:item_list", "update", self.__update)
        self.add_receiver("gui:tailoring:refines:item_list", "changed", self.__update)

        self.draw()

    def __update(self):

        details = self.data_model.get_item_details(self.core.selected_item)

        if details["typetext"] == "Rule":

            self.combo_role.set_model(self.model_role)
            if "role" in details:
                self.combo_role.set_active(details["role"])
            else:
                self.combo_role.set_active(0)

            self.combo_severity.set_model(self.model_severity)
            if "severity" in details:
                self.combo_severity.set_active(details["severity"])
            else:
                self.combo_severity.set_active(0)
        else:
            self.combo_role.set_model(gtk.ListStore(str))
            self.combo_severity.set_model(gtk.ListStore(str))

    def draw(self):
        
        self.vbox_refines = gtk.VBox()
        alig = gtk.Alignment(0, 0)
        alig.set_padding(10, 10, 10, 10)
        self.vbox_refines.pack_start(alig, True, True)
        vbox_refines = gtk.VBox()
        alig.add(vbox_refines)
        
        #alig = self.add_frame_cBox(vbox_refines, "<b>Operator</b>", False)
        #self.cB_operator = gtk.combo_box_entry_new_text()
        #alig.add(self.cB_operator)
        
        #alig = self.add_frame_cBox(vbox_refines, "<b>Check</b>", False)
        #self.cB_check = gtk.combo_box_entry_new_text()
        #alig.add(self.cB_check)
        
        self.model_role = self.create_model(["Full", "Unscored", "Unchecked"])
        self.combo_role = self.add_cBox(vbox_refines, "<b>Role</b>", False)
        self.combo_role.connect('changed', self.cb_changed, "role")
        
        
        self.model_severity = self.create_model(["Unkonown", "Info", "Low", "Medium", "High"])
        self.combo_severity = self.add_cBox(vbox_refines, "<b>Severity</b>", False)
        self.combo_severity.connect('changed', self.cb_changed, "severity")
        

    def create_model(self, data):
        model = gtk.ListStore(str)
        for item in data:
            model.append([item])
        return model
        
    def add_cBox(self, body, text, expand):
        
        combo = gtk.ComboBox()
        cell = gtk.CellRendererText()
        combo.pack_start(cell)
        combo.add_attribute(cell, 'text', 0)
        
        frame = gtk.Frame(text)
        label = frame.get_label_widget()
        label.set_use_markup(True)        
        frame.set_shadow_type(gtk.SHADOW_NONE)
        if expand: body.pack_start(frame, True, True)
        else: body.pack_start(frame, False, True)
        alig = gtk.Alignment(0.5, 0.5, 1, 1)
        alig.set_padding(0, 0, 12, 0)
        frame.add(alig)
        alig.add(combo)
        return combo
        
    def cb_changed(self, widget, data):
        pass
        #TODO
    
    
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
        self.data_model = commands.DataHandler(self.core)
        
        # draw body
        self.body = self.builder.get_object("tailoring:profiles:box")

        self.profiles_list = ProfileList(self.builder.get_object("tailoring:profiles:treeview"), self.core)
        self.profile_details = ProfileDetails(self.core, self)

        self.profile_id = self.builder.get_object("tailoring:profiles:details:lbl_id")
        self.profile_abstract = self.builder.get_object("tailoring:profiles:details:lbl_abstract")
        self.profile_extend = self.builder.get_object("tailoring:profiles:details:lbl_extend")
        self.profile_version = self.builder.get_object("tailoring:profiles:details:lbl_version")
        self.profile_title = self.builder.get_object("tailoring:profiles:details:lbl_title")

        self.profile_description = HtmlTextView()
        self.profile_description.show()
        box = self.builder.get_object("tailoring:profiles:details:box_description")
        self.builder.get_object("tailoring:profiles:details:btn_description").realize()
        bg_color = self.builder.get_object("tailoring:profiles:details:btn_description").get_style().bg[gtk.STATE_NORMAL]
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
            self.profile_id.set_text(details["id"])
            self.profile_abstract.set_text(str(details["abstract"]))
            self.profile_extend.set_text(str(details["extends"] or ""))
            self.profile_version.set_text(details["version"] or "")

            if self.core.selected_lang in details["titles"]: 
                self.profile_title.set_text(details["titles"][self.core.selected_lang] or "")
            else: self.profile_title.set_text(details["titles"][details["titles"].keys()[0]] or "")
                
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
    def cb_btnProfiles(self, button, data=None):
        self.profile = NewProfileWindow(data)


class MenuButtonRefines(abstract.MenuButton):
    """
    GUI for refines.
    """
    def __init__(self, builder, widget, core):
        abstract.MenuButton.__init__(self, "gui:btn:tailoring:refines", widget, core)
        self.builder = builder
        self.core = core

        #draw body
        self.body = self.builder.get_object("tailoring:refines:box")
        self.draw_nb(self.builder.get_object("tailoring:refines:box_nb"))
        self.progress = self.builder.get_object("tailoring:refines:progress")
        self.progress.hide()
        self.filter = filter.Renderer(self.core, self.builder.get_object("tailoring:refines:box_filter"))
        self.filter.expander.cb_changed()
        self.rules_list = ItemList(self.builder.get_object("tailoring:refines:tw_items"), self.core, self.progress)
        self.values = ValuesList(self.builder.get_object("tailoring:refines:tw_values"), self.core)

        # set signals
        self.add_sender(self.id, "update")

    # draw notebook
    def draw_nb(self, box):
        # notebook for details and refines
        notebook = gtk.Notebook()
        box.pack_start(notebook, True, True)
 
        #Details 
        box_details = ItemDetails(self.core)
        notebook.append_page(box_details.box_details, gtk.Label("Details"))

        #set refines
        redDetails = RefineDetails(self.core)
        notebook.append_page(redDetails.vbox_refines, gtk.Label("Refines"))
        notebook.show_all()
        

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


class Language_form():
    """
    Form for show information in accessible languages
    """
    def __init__(self, name, core, data):
        
        self.core = core
        self.data_model = commands.DataHandler(self.core)
        
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title(name)
        self.window.set_size_request(400, 250)
        self.window.set_modal(True)
        #lself.window.set_transient_for(parent)
        
        label_text = gtk.Label()
        label_text.set_alignment(0,0)
        self.window.add(label_text)
        details = self.data_model.get_profile_details(self.core.selected_profile)
        text = ""
        if details != None:
            for lang in details[data]:
                text += "%s:    %s\n\n" % (lang, details[data][lang])
            label_text.set_text(text)
        else:
            label_text.set_text("no " + data)
        if text == "":
            label_text.set_text("no " + data)
        
        self.window.show_all()
