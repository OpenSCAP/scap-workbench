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

import abstract
import logging
import core

logger = logging.getLogger("OSCAPEditor")

class ItemList(abstract.List):
    
    def __init__(self, core=None):
        self.core = core
        abstract.List.__init__(self, "gui:tailoring:refines:item_list", core)
        self.__render()
        self.add_receiver("gui:btn:tailoring:refines", "update", self.__update)

    def __update(self):
        self.cb_fill(self.model)

    def __render(self):
        items, model, cb_fill  = self.core.data.get_items_model(filter=None)
        if model == None: 
            return None

        self.render(items, model, cb_fill)

class ProfileList(abstract.List):
    
    def __init__(self, core=None):
        self.core = core
        abstract.List.__init__(self, "gui:tailoring:profiles:profile_list", core)
        self.__render()
        self.add_receiver("gui:btn:tailoring:profiles", "update", self.__update)

    def __update(self):
        self.cb_fill(self.model)

    def __render(self):
        items, model, cb_fill  = self.core.data.get_profiles_model(filter=None)
        if model == None: 
            return None

        self.render(items, model, cb_fill)


class MenuButtonProfiles(abstract.MenuButton):
    """
    GUI for profiles.
    """
    def __init__(self, c_body=None, sensitivity=None, core=None):
        abstract.MenuButton.__init__(self,"gui:btn:tailoring:profiles", "Profiles", c_body, sensitivity)
        self.core = core
        self.c_body = c_body
        
        #referencies
        self.label_abstract = None
        self.label_extend = None
        self.entry_version = None
        self.textView_tile = None
        self.textView_description = None
        
        # draw body
        self.body = self.draw_body()
        self.add_sender(self.id, "update")
    
    #set functions
    def set_info(self, abstract, extend):
        """
        Set abstract and extend information.
        """
        self.label_abstract.set_text(abstract)
        self.label_extend.set_text(extend)

    def set_version(self, version):
        """
        Set version of profile.
        """
        self.entry_version.set_text(version)
    
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
        
    #callBack functions
    def cb_btnProfiles(self, button, data=None):
        self.profile = NewProfileWindow(data)
        pass
    
    def cb_listProfiles(self, widget):
        pass
    
    def cb_textView(self, widget, data=None):
        print data
        
    def cb_version(self, widget, data=None):
        pass
        
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
        
        selection = self.profiles_list.get_TreeView().get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)
        selection.connect("changed", self.cb_listProfiles)
        
        
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

        self.add_label(table, "Abstract: ", 0, 1, 0, 1)
        self.add_label(table, "Extend: ", 0, 1, 1, 2)
        self.add_label(table, "Version: ", 0, 1, 2, 3)
        self.add_label(table, "Title: ", 0, 1, 3, 4)
        self.add_label(table, "Description: ", 0, 1, 4, 5)


        self.label_abstract = self.add_label(table, "None ", 1, 2, 0, 1)
        self.label_extend = self.add_label(table, "None ", 1, 2, 1, 2)

        self.entry_version = gtk.Entry()
        self.entry_version.connect("selection-notify-event", self.cb_version, "Description")
        table.attach(self.entry_version, 1, 2, 2, 3,gtk.EXPAND|gtk.FILL,gtk.FILL)

        hbox = gtk.HBox()
        table.attach(hbox, 1, 2, 3, 4,gtk.EXPAND|gtk.FILL,gtk.EXPAND|gtk.FILL, 0, 3)
        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.texView_title = gtk.TextView()
        self.texView_title.connect("selection-notify-event", self.cb_textView, "Title")
        sw.add(self.texView_title)
        hbox.pack_start(sw, expand=True, fill=True, padding=0)
        self.button_title = gtk.Button("...")
        hbox.pack_start(self.button_title, expand=False, fill=True, padding=0)

        hbox = gtk.HBox()
        table.attach(hbox, 1, 2, 4, 5,gtk.EXPAND|gtk.FILL,gtk.EXPAND|gtk.FILL, 0, 3)
        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.texView_description = gtk.TextView()
        self.texView_title.connect("selection-notify-event", self.cb_textView, "Description")
        sw.add(self.texView_description)
        hbox.pack_start(sw, expand=True, fill=True, padding=0)
        self.button_description = gtk.Button("...")
        hbox.pack_start(self.button_description, expand=False, fill=True, padding=0)

        #tests
        self.set_descriprion("pokuss")
        self.set_descriprion("pokuss2")
        self.set_title("title")
        self.set_version("version")
        model = gtk.ListStore( gobject.TYPE_STRING, gobject.TYPE_STRING,gobject.TYPE_STRING)
        model.append(["e", "e", "w"])
        model.append(["e", "e", "w"])
        model.append(["e", "e", "w"])
        model.append(["e", "e", "w"])
        
        body.show_all()
        body.hide()
        self.c_body.add(body)
        return body


class MenuButtonRefines(abstract.MenuButton):
    """
    GUI for refines.
    """
    def __init__(self, c_body=None, sensitivity=None, core=None):
        abstract.MenuButton.__init__(self, "gui:btn:tailoring:refines", "Refines", c_body, sensitivity)
        self.core = core
        self.c_body = c_body
        
        #referencies
        self.label_abstract = None
        self.label_extend = None
        self.details = None
        self.defendecies = None
        #draw body
        self.body = self.draw_body()

        # set signals
        self.add_sender(self.id, "update")
        
    #set functions
    
    def set_refinesList(self, layouts, model):
        self.sw.fill(layouts, model)
        
    def set_values(self, list_values):
        """ 
        The function create comboBoxs for set values
        @param list_values list of objects with name, id, list of values for selection
        """
        radek = 0
        self.vbox = gtk.VBox()
        for value in list_values:
            label = gtk.Label(value.name+": ")
            label.set_alignment(0, 0.5)
            self.vbox.pack_start(label, expand=False, fill=True, padding=0)
            comboBox = gtk.combo_box_entry_new_text()
            for val in value.list_values:
                comboBox.append_text(val)
            comboBox.connect('changed', self.cb_values)
            self.vbox.pack_start(comboBox, expand=False, fill=True, padding=0)
        self.values_c.add(self.vbox)
        
    def destroy_values(self):
        """
        The function destroy table with values
        """
        self.table.destroy()
        
    #callBack functions

    def cb_values(self, id):
        pass

    #draw functions
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

    def add_frame_vp(self,body, text,pos = 1):
        frame = gtk.Frame(text)
        frame.set_shadow_type(gtk.SHADOW_NONE)
        #frame.set_border_width(5)        
        label = frame.get_label_widget()
        label.set_use_markup(True)        
        if pos == 1: body.pack1(frame,  resize=False, shrink=False)
        else: body.pack2(frame,  resize=False, shrink=False)
        alig = gtk.Alignment(0.5, 0.5, 1, 1)
        alig.set_padding(0, 0, 12, 0)
        frame.add(alig)
        return alig
    
    def draw_body(self):
        body = gtk.VBox()
    
        # label info with profile name
        self.label_info = gtk.Label("None")
        body.pack_start(self.label_info, expand=False, fill=True, padding=0)
        body.pack_start(gtk.HSeparator(), expand=False, fill=True, padding=4)
        
        #main body
        vpaned_main = gtk.VPaned()
        body.pack_start(vpaned_main, expand=True, fill=True, padding=0)
        box_main = gtk.HBox()
        vpaned_main.pack1(box_main, resize=False, shrink=False)

        # filters
        vbox_filter = gtk.VBox()
        self.expander = ExpandBox(box_main, vbox_filter, "Search / Filters", False)
        alig = self.add_frame_cBox(vbox_filter, "<b>Layouts list profiles</b>", False)
        self.cb_filter = gtk.combo_box_entry_new_text()
        alig.add(self.cb_filter)
        alig = self.add_frame_cBox(vbox_filter, "<b>Filters</b>", False)
        self.btn_filter = gtk.Button("Set fiters")
        alig.add(self.btn_filter)
        alig_filters = self.add_frame_cBox(vbox_filter, "<b>Active filters</b>", False)
        
        box_main.pack_start(gtk.VSeparator(), expand=False, fill=True, padding=0)
        hpaned = gtk.HPaned()
        box_main.pack_start(hpaned, True, True)
        
        # tree
        alig = self.add_frame_vp(hpaned, "<b>Rules and Groups</b>",1)
        self.rules_list = ItemList(core=self.core)
        alig.add(self.rules_list.get_widget())
        
        # notebook for details and refines
        notebook = gtk.Notebook()
        hpaned.pack2(notebook, False, False)
 
        #Details 
        box_details = gtk.VBox()
        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.details = gtk.TextView()
        sw.add(self.details)
        notebook.append_page(sw, gtk.Label("Detail"))

        #set refines
        vbox_refines = gtk.VBox()
        notebook.append_page(vbox_refines, gtk.Label("Refines"))
        
        alig = self.add_frame_cBox(vbox_refines, "<b>Operator</b>", False)
        self.cB_operator = gtk.combo_box_entry_new_text()
        alig.add(self.cB_operator)
        
        alig = self.add_frame_cBox(vbox_refines, "<b>Check</b>", False)
        self.cB_check = gtk.combo_box_entry_new_text()
        alig.add(self.cB_check)
        
        alig = self.add_frame_cBox(vbox_refines, "<b>Role</b>", False)
        self.cB_role = gtk.combo_box_entry_new_text()
        alig.add(self.cB_role)
        
        alig = self.add_frame_cBox(vbox_refines, "<b>Severity</b>", False)
        self.cB_severity = gtk.combo_box_entry_new_text()
        alig.add(self.cB_severity)
        
        self.values_c = self.add_frame_cBox(vbox_refines, "<b>Values</b>", False)
        list_values = []
        list_values.append(Value("pokus1", 1, ["34","35","36","37"], 1))
        list_values.append(Value("pokus2", 1, ["34","35","36","37"], 1))
        list_values.append(Value("pokus3", 1, ["34","35","36","37"], 1))
        self.set_values(list_values)

        # box for defendecies and something else
        box = gtk.HBox()
        vpaned_main.pack2(box, False, False)
        
        #Defendecies
        alig = self.add_frame_cBox(box, "<b>Defendencies</b>",2)
        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.defendecies = gtk.TextView()
        alig.add(sw)
        sw.add(self.defendecies)
        

        # smothing else
        alig = self.add_frame_cBox(box, "<b>Something else</b>",2)
        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.d = gtk.TextView()
        alig.add(sw)
        sw.add(self.d)
        
        body.show_all()
        body.hide()
        self.c_body.add(body)
        self.expander.cb_changed(self)
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

class ExpandBox(abstract.EventObject):
    """
    Create expand box. Set only to conteiner.
    """
    
    def __init__(self, place, body, text, show=True, core=None):
        """
        @param place Conteiner for this expandBox.
        @param body Conteiner or widget to expandBox
        @param text Button name for show or hide expandBox
        @param show If ExpanBox should be hide/show False/True
        """
        self.core = core
        self.show = not show
        
        # body for expandBox
        rollBox = gtk.HBox()
        place.pack_start(rollBox, False, True)

        self.frameContent = body
        rollBox.pack_start(body , True, True)
        
        rollBox.pack_start(gtk.VSeparator() , False, True)
        
        #create icon
        self.image1 = gtk.Image()
        self.image2 = gtk.Image()
        self.pixbufShow = self.image1.render_icon(stock_id=getattr(gtk, "STOCK_GO_FORWARD"),
                                size=gtk.ICON_SIZE_MENU,
                                detail=None)
        self.pixbufHide = self.image2.render_icon(stock_id=getattr(gtk, "STOCK_GO_BACK"),
                        size=gtk.ICON_SIZE_MENU,
                        detail=None)
        
        #create label
        self.label = gtk.Label(text)
        self.label.set_angle(90)

        #create button
        hbox = gtk.VBox()
        hbox.pack_start(self.image1, False, True)        
        hbox.pack_start(self.label, True, True)
        hbox.pack_start(self.image2, False, True)
        btn = gtk.Button()
        btn.add(hbox)
        rollBox.pack_start(btn, False, True)
        btn.connect("clicked", self.cb_changed)

    def cb_changed(self, widget):
        logger.debug("Expander switched to %s", not self.show)
        if self.show:
            self.frameContent.hide_all()
            if widget != None: self.show = False
            self.image1.set_from_pixbuf(self.pixbufShow)
            self.image2.set_from_pixbuf(self.pixbufShow)
        else:
            self.frameContent.show_all()
            if widget != None: self.show = True
            self.image1.set_from_pixbuf(self.pixbufHide)
            self.image2.set_from_pixbuf(self.pixbufHide)

class Value(abstract.EventObject):
    """
    Structre for create iformation for value
    """
    def __init__(self, name, id, list_values, default, old_value=None):
        self.name = name
        self.id = id
        self.list_values = list_values
        self.default = default
        self.old_value = old_value
