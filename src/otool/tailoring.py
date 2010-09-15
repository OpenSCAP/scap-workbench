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
    
    def __init__(self, core=None):
        self.core = core
        self.data_model = commands.DHItemsTree(core)
        abstract.List.__init__(self, "gui:tailoring:refines:item_list", core)
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
        self.emit("update")

class DepsList(abstract.List):
    
    def __init__(self, core=None):
        self.core = core
        self.data_model = commands.DHDependencies(core)
        abstract.List.__init__(self, "gui:tailoring:refines:deps_list", core)
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

class ValuesList(abstract.List):
    
    def __init__(self, core=None):
        self.core = core
        self.data_model = commands.DHValues(core)
        abstract.List.__init__(self, "gui:tailoring:refines:values_list", core)
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
    
    def __init__(self, core=None):
        self.core = core
        self.data_model = commands.DHProfiles(core)
        abstract.List.__init__(self, "gui:tailoring:profiles:profile_list", core)

        selection = self.get_TreeView().get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)

        # actions
        self.add_sender(self.id, "show")
        self.add_sender(self.id, "profile_changed")
        #self.add_receiver("gui:btn:tailoring:profiles", "update", self.__update)
        self.add_receiver("gui:tailoring:profiles:profile_list", "update", self.__show)
        selection.connect("changed", self.cb_item_changed, self.get_TreeView())

        # TODO: Update should be called after importing XCCDF file.
        self.__update()

    def __show(self):
        if "profile" not in self.__dict__ or self.profile != self.core.selected_profile:
            self.profile = self.core.selected_profile

    def __update(self):
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
        #self.description.set_tooltip_text("")
        self.title.set_text("")
        for child in self.refBox.get_children():
            child.destroy()
        for child in self.fixBox.get_children():
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
        self.description.display_html(description)
        
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
        for i, fixtext in enumerate(fixes):
            hbox = gtk.HBox()
            counter = gtk.Label("%d) " % (i+1,))
            counter.set_alignment(0,0)
            hbox.pack_start(counter, False, False)
            label = gtk.Label()
            label.set_text(fixtext["text"])
            label.set_tooltip_text(["", "Need reboot\n"][fixtext["reboot"]])
            hbox.pack_start(label, True, True)
            label.set_use_markup(True)
            label.set_line_wrap(True)
            label.set_line_wrap_mode(pango.WRAP_WORD) 
            label.set_alignment(0,0)
            label.connect("size-allocate", render.label_size_allocate)
            hbox.show_all()
            self.fixBox.pack_start(hbox, True, True)

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
        hbox.pack_start(self.type, expand=False, fill=True, padding=1)
        vbox.pack_start(hbox, expand=False, fill=True, padding=1)
        
        #weight
        hbox = gtk.HBox()
        hbox.pack_start(gtk.Label("Weight: "), expand=False, fill=False, padding=1)
        self.weight = gtk.Label("")
        hbox.pack_start(self.weight, expand=False, fill=False, padding=1)
        vbox.pack_start(hbox, expand=False, fill=False, padding=1)
        
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
        for child in self.description.get_children():
            print "Child:",child
        self.description.set_wrap_mode(gtk.WRAP_WORD)
        sw = gtk.ScrolledWindow()
        sw.set_property("hscrollbar-policy", gtk.POLICY_AUTOMATIC)
        sw.set_property("vscrollbar-policy", gtk.POLICY_AUTOMATIC)
        sw.set_property("border-width", 0)
        sw.add(self.description)
        sw.show()
        expander.add(alig)
        vbox.pack_start(sw, expand=True, fill=True, padding=1)
        self.box_details.pack_start(expander, expand=True, fill=True, padding=1)
        
        #References
        expander = gtk.Expander("<b>References</b>")
        expander.set_expanded(True)
        label = expander.get_label_widget()
        label.set_use_markup(True)
        alig = gtk.Alignment(0.5, 0.5, 1, 1)
        alig.set_padding(0, 10, 12, 4)
        expander.add(alig)
        vbox = gtk.VBox()
        alig.add(vbox)
        vbox.pack_start(gtk.HSeparator(), expand=False, fill=True, padding=3)
        self.refBox = gtk.VBox()
        vbox.pack_start(self.refBox, expand=False, fill=True, padding=0)
        self.box_details.pack_start(expander, expand=False, fill=True, padding=1)

        #fixes
        expander = gtk.Expander("<b>Fixes</b>")
        expander.set_expanded(True)
        label = expander.get_label_widget()
        label.set_use_markup(True)
        alig = gtk.Alignment(0.5, 0.5, 1, 1)
        alig.set_padding(0, 10, 12, 4)
        vbox = gtk.VBox()
        alig.add(vbox)
        vbox.pack_start(gtk.HSeparator(), expand=False, fill=True, padding=3)
        self.fixBox = gtk.VBox()
        vbox.pack_start(self.fixBox, expand=True, fill=True, padding=0)
        expander.add(alig)
        self.box_details.pack_start(expander, expand=False, fill=True, padding=1)

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
            print item
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
        self.data_model = commands.DataHandler(self.core)

        self.add_receiver("gui:tailoring:profiles:profile_list", "update", self.__update)
        self.add_receiver("gui:tailoring:profiles:profile_list", "changed", self.__update)
        self.add_receiver("gui:btn:main:xccdf", "lang_changed", self.__update)
        
    def __update(self):
        details = self.data_model.get_profile_details(self.core.selected_profile)
        if details != None:
            self.guiProfiles.set_info(details["id"], str(details["abstract"]), str(details["extends"] or ""))
            self.guiProfiles.set_version(details["version"])

            if self.core.selected_lang in details["titles"]: 
                self.guiProfiles.set_title(details["titles"][self.core.selected_lang])
            else: 
                for lang in details["titles"]:
                    self.guiProfiles.set_title(details["titles"][lang])
                    break
                
            if self.core.selected_lang in details["descriptions"]: 
                self.guiProfiles.set_description(details["descriptions"][self.core.selected_lang][:200]+" ...")
            else: 
                for lang in details["descriptions"]:
                    self.guiProfiles.set_description(details["descriptions"][lang])
                    break
        else:
            self.guiProfiles.set_info("", "", "")
            self.guiProfiles.set_version("")
            self.guiProfiles.set_title("")
            self.guiProfiles.set_description("")
        
class MenuButtonProfiles(abstract.MenuButton):
    """
    GUI for profiles.
    """
    def __init__(self, c_body=None, sensitivity=None, core=None):
        abstract.MenuButton.__init__(self,"gui:btn:tailoring:profiles", "Profiles", None, c_body, sensitivity)
        self.core = core
        self.c_body = c_body
        
        # draw body
        self.body = self.draw_body()
        self.add_sender(self.id, "update")
    
    #set functions
    def set_info(self, id, abstract, extend):
        """
        Set abstract and extend information.
        """
        self.id_profile.set_text(id)
        self.abstract.set_text(abstract)
        self.extend.set_text(extend)

    def set_version(self, version):
        """
        Set version of profile.
        """
        if version == None:
            version = ""
        self.version.set_text(version)
    
    def set_title(self, text):
        """
        Set title to the textView.
        @param text Text with title
        """
        self.title.set_text(text)
        
    def set_description(self, text):
        """
        Set description to the textView.
        @param text Text with description
        """
        self.description.set_text(text)
        
    #callBack functions
    def cb_btnProfiles(self, button, data=None):
        self.profile = NewProfileWindow(data)
        pass
        
    def cb_btnLang(self, widget, name, core, data):
        window = Language_form(name, core, data)

    # draw function
    def add_frame_vp(self,body, text,pos = 1):
        frame = gtk.Frame(text)
        label = frame.get_label_widget()
        label.set_use_markup(True)
        frame.set_shadow_type(gtk.SHADOW_NONE)
        frame.set_border_width(5)
        if pos == 1: body.pack1(frame,  resize=False, shrink=False)
        else: body.pack2(frame,  resize=False, shrink=False)
        alig = gtk.Alignment(0.5, 0.5, 1, 1)
        alig.set_padding(0, 0, 12, 0)
        frame.add(alig)
        return alig
        
    def add_label(self,table, text, left, right, top, bottom):
        label = gtk.Label(text)
        #table.attach(hbox, 1, 2, 3, 4,gtk.EXPAND|gtk.FILL,gtk.EXPAND|gtk.FILL, 0, 3)
        table.attach(label, left, right, top, bottom,gtk.FILL,gtk.FILL)
        label.set_alignment(0, 0.5)
        return label
        
    def draw_body(self):
        body = gtk.VPaned()

        # List of profiles
        alig = self.add_frame_vp(body, "<b>Profiles</b>")
        hbox = gtk.HBox()
        alig.add(hbox)
        self.profiles_list = ProfileList(self.core)
        hbox.pack_start(self.profiles_list.get_widget(), expand=True, fill=True, padding=3)
        
        ProfileDetails(self.core, self)
        
        # operations with profiles
        hbox.pack_start(gtk.VSeparator(), expand=False, fill=True, padding=10)
        box = gtk.VButtonBox()
        box.set_layout(gtk.BUTTONBOX_START)
        
        btn = gtk.Button("Add")
        btn.connect("clicked", self.cb_btnProfiles, "add")
        box.add(btn)
        
        btn = gtk.Button("Extend")
        btn.connect("clicked", self.cb_btnProfiles, "extend")
        box.add(btn)
        
        btn = gtk.Button("Copy")
        btn.connect("clicked", self.cb_btnProfiles, "copy")
        box.add(btn)
        
        btn = gtk.Button("Delete")
        btn.connect("clicked", self.cb_btnProfiles, "del")
        box.add(btn)
        
        hbox.pack_start(box, expand=False, fill=True, padding=0)

        # edit profiles
        #body.pack_start(gtk.HSeparator(), expand=False, fill=True, padding=10)
        
        alig = self.add_frame_vp(body, "<b>Details</b>",2)

        table = gtk.Table(5 ,2)
        alig.add(table)

        self.add_label(table, "ID: ", 0, 1, 0, 1)
        self.add_label(table, "Title: ", 0, 1, 1, 2)
        self.add_label(table, "Abstract: ", 0, 1, 2, 3)
        self.add_label(table, "Extend: ", 0, 1, 3, 4)
        self.add_label(table, "Version: ", 0, 1, 4, 5)
        self.add_label(table, "Description: ", 0, 1, 5, 6)

        #id
        self.id_profile = self.add_label(table, "", 1, 2, 0, 1)
        
        #title
        hbox = gtk.HBox()
        self.title = gtk.Label()
        self.title.set_alignment(0, 0.5)
        table.attach(hbox, 1, 2, 1, 2,gtk.FILL,gtk.FILL, 0, 3)
        hbox.pack_start(self.title, expand=True, fill=True, padding=0)
        self.but_title = gtk.Button("...")
        self.but_title.connect("clicked", self.cb_btnLang, "Titles", self.core, "titles")
        hbox.pack_start(self.but_title, expand=False, fill=True, padding=0)
        
        # abstract expand
        self.abstract = self.add_label(table, "", 1, 2, 2, 3)
        self.extend = self.add_label(table, "", 1, 2, 3, 4)

        #version
        self.version = self.add_label(table, "", 1, 2, 4, 5)

        #description
        hbox = gtk.HBox()
        self.description = gtk.Label()
        self.description.set_alignment(0, 0.5)
        table.attach(hbox, 1, 2, 5, 6,gtk.EXPAND|gtk.FILL,gtk.FILL, 0, 3)
        #table.attach(hbox, 1, 2, 4, 5,gtk.EXPAND|gtk.FILL,gtk.EXPAND|gtk.FILL, 0, 3)
        hbox.pack_start(self.description, expand=True, fill=True, padding=0)
        self.but_description = gtk.Button("...")
        self.but_description.connect("clicked", self.cb_btnLang, "Descriptions", self.core, "descriptions")
        hbox.pack_start(self.but_description, expand=False, fill=True, padding=0)

        body.show_all()
        body.hide()
        self.c_body.add(body)
        return body


class MenuButtonRefines(abstract.MenuButton):
    """
    GUI for refines.
    """
    def __init__(self, c_body=None, sensitivity=None, core=None):
        abstract.MenuButton.__init__(self, "gui:btn:tailoring:refines", "Refines", None, c_body, sensitivity)
        self.core = core
        self.c_body = c_body

        #draw body
        self.body = self.draw_body()

        # set signals
        self.add_sender(self.id, "update")

    #draw
    def draw_body(self):
        body = gtk.VBox()
        
        #main body
        vpaned_main = gtk.VPaned()
        body.pack_start(vpaned_main, expand=True, fill=True, padding=10)
        box_main = gtk.HBox()
        vpaned_main.pack1(box_main, resize=False, shrink=False)

        # filters
        self.filter = filter.Renderer(self.core, box_main)
        
        box_main.pack_start(gtk.VSeparator(), expand=False, fill=True, padding=0)
        hpaned = gtk.HPaned()
        hpaned.set_position(600)
        box_main.pack_start(hpaned, True, True)
        
        # tree
        alig = self.add_frame_vp(hpaned, "<b>Rules and Groups</b>",1)
        self.rules_list = ItemList(core=self.core)
        alig.add(self.rules_list.get_widget())
        
        # notebook for details and refines
        notebook = gtk.Notebook()
        hpaned.pack2(notebook, True, True)
 
        #Details 
        box_details = ItemDetails(self.core)
        notebook.append_page(box_details.box_details, gtk.Label("Details"))

        #set refines
        redDetails = RefineDetails(self.core)
        notebook.append_page(redDetails.vbox_refines, gtk.Label("Refines"))

        # box for dependecies and values
        box = gtk.HBox()
        vpaned_main.pack2(box, False, False)
        
        #Defendecies
        alig = self.add_frame_cBox(box, "<b>Dependencies</b>", 2)
        self.dependencies = DepsList(core=self.core)
        alig.add(self.dependencies.get_widget())
        
        # values
        alig = self.add_frame_cBox(box, "<b>Values</b>", 2)
        self.values = ValuesList(core=self.core)
        alig.add(self.values.get_widget())
        
        body.show_all()
        body.hide()
        self.c_body.add(body)
        self.filter.expander.cb_changed(None)
        return body


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

        self.set_language(["English", "Czech", "Russian"], 0)
        
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
