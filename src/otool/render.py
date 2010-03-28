#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pygtk
import gtk
import gobject

class Menu:
    """ Create Main item for TreeToolBar_toggleButtonGroup and draw all tree
    Menu
    """
    def __init__(self, id, c_toolBar):

        self.id = id
        self.btnList = []
        self.active_item = None
        self.default_item = None
        self.c_toolBar = c_toolBar
	
    def add_item(self, item, position=None):
        """ Add item to the menu list
        """

        if len(self.btnList) == 0:
            self.set_default(item)
        self.btnList.append(item)
        # vizual
        if position != None: 
            self.c_toolBar.insert_space((position*2)+1)
            self.c_toolBar.insert(item.widget, position)
        else: 
            self.c_toolBar.insert(item.widget, self.c_toolBar.get_n_items())

        item.parent = self

    def show(self):
        self.c_toolBar.show()
        self.toggle_button(self.active_item)

    def set_active(self, active):
        if active: self.show()
        else: self.c_toolBar.hide()

    def set_default(self, item):
        self.active_item = item
        self.default_item = item

    def toggle_button(self, item):
        """ Toggle selected button
        @param item selected MenuButton object
        """
        # Deselect all buttons
        if self.active_item: self.active_item.set_active(False)
        # Show selected button
        self.active_item = item
        self.active_item.set_active(True)
		
    def refresh(self):
        """ Refresh graphic content
        Async. method called after data change
        """
        raise NotImplementedError, "Function \"refresh\" is not implemented yet"

class MenuButton:
    """ Class for tree of toogleBar with toggleButtons in group
    """

    def __init__(self, id, name, c_body=None, sensitivity=None):
        """
        @param sensitivity filter function
        """
        # structure
        self.id = id
        self.name = name
        self.sensitivity = sensitivity
        self.parent = None
        self.c_body = c_body
        self.menu = None
        self.body = None

        # setings
        self.widget = gtk.ToggleToolButton()
        self.widget.set_is_important(True)
        self.widget.set_label(name)
        if self.sensitivity == None: 
            self.widget.set_sensitive(True)
        else: self.widget.set_sensitive(False)
        self.widget.show()
        self.widget.connect("toggled", self.cb_toggle)


    def set_active(self, active):
        self.widget.handler_block_by_func(self.cb_toggle)
        self.widget.set_active(active)
        self.set_body(active)
        if self.menu: 
            self.menu.set_active(active)
            if self.menu.active_item:
                self.menu.active_item.set_active(active)
        self.widget.handler_unblock_by_func(self.cb_toggle)

    def set_menu(self, menu):
        self.menu = menu

    def cb_toggle(self, widget):
        """ Change active of toggleButtons in current toolBar
        and visibility of child
        """
        self.parent.toggle_button(self)

    def set_body(self,active):
        if self.body:
            if active:
                self.body.show_all()
            else:
                self.body.hide_all()

class MenuButton_XCCDF(MenuButton):

    def __init__(self, c_body=None, sensitivity=None):
        MenuButton.__init__(self,"menu:main:btn:xccdf", "XCCDF", c_body, sensitivity)
        self.c_body = c_body
        
        # referencies
        self.label_title = None
        self.label_description = None
        self.label_version = None
        self.label_url = None
        self.cBox_language = None

        # draw body
        self.body = self.draw_body()
        
        
    # set functions
    def set_detail(self, tile, description, version, url):
        self.label_title.set_text(title)
        self.label_description.set_text(description)
        self.label_version.set_text(version)
        self.label_url.set_text(url)
        
    def set_language(self, languages, active):
        model = self.cBox_language.get_model()
        model.clear()
        for lan in languages:
            model.append([lan])
        self.cBox_language.set_active(active)
        
    # callBack functions
    def cb_btn(self, btn, data=None):
        print "clicked = ", data

    def cb_changed(self, combobox):
        model = combobox.get_model()
        index = combobox.get_active()
        if index < 0:
           pass#print 'I prefered English Language'
        else:
             print 'I prefered', model[index][0], 'Language'
        return
        
        
    # draw functions
    def add_label(self,table, text, left, right, top, bottom, x=gtk.FILL, y=gtk.FILL):
        label = gtk.Label(text)
        table.attach(label, left, right, top, bottom, x, y)
        label.set_alignment(0, 0.5)
        return label
        
    def add_frame(self, body, text, expand = True):
        frame = gtk.Frame(text)
        label = frame.get_label_widget()
        label.set_use_markup(True)
        if expand: body.pack_start(frame, expand=True, fill=True, padding=0)
        else: body.pack_start(frame, expand=False, fill=True, padding=0)
        alig = gtk.Alignment(0.5, 0.5, 1, 1)
        alig.set_padding(0, 0, 12, 0)
        frame.add(alig)
        return alig

    def draw_body(self):
        body = gtk.VBox()
        alig = self.add_frame(body, "<b>List</b>")
        table = gtk.Table(5 ,2)
        alig.add(table)

        self.add_label(table, "Name: ", 0, 1, 0, 1)
        self.add_label(table, "Description: ", 0, 1, 1, 2)
        self.add_label(table, "Version: ", 0, 1, 2, 3)
        self.add_label(table, "URL: ", 0, 1, 3, 4)
        self.add_label(table, "Prefered Language: ", 0, 1, 4, 5)

        self.label_title = self.add_label(table, "None ", 1, 2, 0, 1)
        self.label_description = self.add_label(table, "None ", 1, 2, 1, 2)
        self.label_version = self.add_label(table, "None", 1, 2, 2, 3)
        self.label_url = self.add_label(table, "None ", 1, 2, 3, 4)

        self.cBox_language = gtk.ComboBox()
        model = gtk.ListStore(str)
        cell = gtk.CellRendererText()
        self.cBox_language.pack_start(cell)
        self.cBox_language.add_attribute(cell, 'text', 0)
        self.cBox_language.set_model(model)
        self.cBox_language.connect('changed', self.cb_changed)
        self.cBox_language.set_active(0)
        table.attach(self.cBox_language, 1, 2, 4, 5,gtk.FILL,gtk.FILL)

        self.set_language(["English", "Czech", "Russian"], 0)
        
        # generator for oval
        alig = self.add_frame(body, "<b>Generator for OVAL</b>")

        # operations
        alig = self.add_frame(body, "<b>Operations</b>", False)
        box = gtk.HButtonBox()
        box.set_layout(gtk.BUTTONBOX_START)
        
        btn = gtk.Button("Load File")
        btn.connect("clicked", self.cb_btn, "load")
        box.add(btn)
        
        btn = gtk.Button("Save Changes")
        btn.connect("clicked", self.cb_btn, "save")        
        box.add(btn)
        
        btn = gtk.Button("Validate")
        btn.connect("clicked", self.cb_btn, "valid")
        box.add(btn)
        alig.add(box)

        # add to conteiner
        body.hide_all()
        self.c_body.add(body)
        return body


        
class MenuButton_profiles(MenuButton):

    def __init__(self, c_body=None, sensitivity=None):
        MenuButton.__init__(self,"menu:main:btn:xccdf", "Profiles", c_body, sensitivity)
        self.c_body = c_body
        
        #referencies
        self.label_abstract = None
        self.label_extend = None
        self.entry_version = None
        self.textView_tile = None
        self.textView_description = None
        self.treeView_profiles = None
        
        # draw body
        self.body = self.draw_body()
    
    #set functions
    def set_listProfiles(self, model):
        self.treeView_profiles.set_model(model)
    
    def set_info(self, abstract, extend):
        self.label_abstract.set_text(abstract)
        self.label_extend.set_text(extend)

    def set_version(self, version):
        self.entry_version.set_text(version)
    
    def set_title(self, text):
        textbuffer = self.texView_title.get_buffer()
        textbuffer.set_text(text)
        
    def set_descriprion(self, text):
        textbuffer = self.texView_description.get_buffer()
        textbuffer.set_text(text)
        
    #callBack functions
    def cb_btnProfiles(self, button, data=None):
        self.profile = New_profile(data)
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
        alig = self.add_frame_vp(body, "<b>List of profiles</b>")
        hbox = gtk.HBox()
        alig.add(hbox)
        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.treeView_profiles = gtk.TreeView()
        sw.add(self.treeView_profiles)
        hbox.pack_start(sw, expand=True, fill=True, padding=3)
        
        column = gtk.TreeViewColumn('ID', gtk.CellRendererText(),text=0) 
        column.set_sort_column_id(0)
        self.treeView_profiles.append_column(column)
        
        column = gtk.TreeViewColumn('Title', gtk.CellRendererText(),text=1) 
        column.set_sort_column_id(1)
        self.treeView_profiles.append_column(column)
        
        column = gtk.TreeViewColumn('Version', gtk.CellRendererText(),text=2) 
        column.set_sort_column_id(2)
        self.treeView_profiles.append_column(column)
        
        selection = self.treeView_profiles.get_selection()
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
           
        self.set_listProfiles(model)
        
        body.hide_all()
        self.c_body.add(body)
        return body

class MenuButton_refines(MenuButton):

    def __init__(self, c_body=None, sensitivity=None):
        MenuButton.__init__(self,"menu:main:btn:xccdf", "Refines", c_body, sensitivity)
        self.c_body = c_body
        
        #referencies
        self.label_abstract = None
        self.label_extend = None
        
        #draw body
        self.body = self.draw_body()
        
    #set functions
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
        hbox_main = gtk.HBox()
        body.pack_start(hbox_main, expand=True, fill=True, padding=0)

        # filters
        vbox_filter = gtk.VBox()
        hbox_main.pack_start(vbox_filter, expand=False, fill=True, padding=0)
        alig = self.add_frame_cBox(vbox_filter, "<b>Layouts list profiles</b>", False)
        self.cb_filter = gtk.combo_box_entry_new_text()
        alig.add(self.cb_filter)
        alig = self.add_frame_cBox(vbox_filter, "<b>Filters</b>", False)
        self.btn_filter = gtk.Button("Set fiters")
        alig.add(self.btn_filter)
        alig_filters = self.add_frame_cBox(vbox_filter, "<b>Active filters</b>", False)
        
        hbox_main.pack_start(gtk.VSeparator(), expand=False, fill=True, padding=4)
        
        # show data
        vpaned_tree = gtk.VPaned()
        hbox_main.pack_start(vpaned_tree, expand=True, fill=True, padding=0)
        
        # tree
        alig = self.add_frame_vp(vpaned_tree, "<b>List</b>",1)
        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.treeV = gtk.TreeView()
        sw.add(self.treeV)
        alig.add(sw)
        
        #Details
        vpaned_details = gtk.VPaned()
        vpaned_tree.pack2(vpaned_details,  resize=False, shrink=False)
 
        alig = self.add_frame_vp(vpaned_details, "<b>Details</b>",1)
        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        textV = gtk.TextView()
        alig.add(sw)
        sw.add(textV)
        
        #Defendecies
        alig = self.add_frame_vp(vpaned_details, "<b>Defendencies</b>",2)
        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        textV = gtk.TextView()
        alig.add(sw)
        sw.add(textV)
        
        hbox_main.pack_start(gtk.VSeparator(), expand=False, fill=True, padding=4)
        
        #set refines
        vbox_refines = gtk.VBox()
        hbox_main.pack_start(vbox_refines, expand=False, fill=True)
        
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
        body.hide_all()
        self.c_body.add(body)
        return body


class MenuButton_oval(MenuButton):

    def __init__(self, c_body=None, sensitivity=None):
        MenuButton.__init__(self,"menu:main:btn:oval", "Oval", c_body, sensitivity)
        self.c_body = c_body
        self.title = None
        self.description = None
        self.version = None
        self.url = None
        self.language = None
        self.body = self.draw_body()


    def draw_body(self):
        body = gtk.VBox()

        body.hide_all()
        self.c_body.add(body)
        return body

class New_profile:
    
    def __init__(self, action="add"):
        self.action = action
        self.draw_window()


        
    #set function
    def set_abstract(self, abstract):
        if abstract == True:
            self.label_abstract = "Yes"
        else:
            self.label_abstract = "No"
    
    def set_extend(self, text):
        self.label_extend = text

    def set_version(self, text):
        self.entry_version = text
        
    def set_language(self, languages, active):
        model = self.cBox_language.get_model()
        model.clear()
        for lan in languages:
            model.append([lan])
        self.cBox_language.set_active(active)

    def set_title(self, text):
        textbuffer = self.texView_title.get_buffer()
        textbuffer.set_text(text)
        
    def set_descriprion(self, text):
        textbuffer = self.texView_description.get_buffer()
        textbuffer.set_text(text)

    #callBack function
    def cb_abstract(self, combobox):
        model = combobox.get_model()
        index = combobox.get_active()
        if index < 0:
            pass#print 'I prefered English Language'
        else:
                print 'I prefered', model[index][0], 'Language'
        return

    def cb_version(self, entry):
        pass
    
    def cb_language(self, combobox):
        model = combobox.get_model()
        index = combobox.get_active()
        if index < 0:
            pass#print 'I prefered English Language'
        else:
                print 'I prefered', model[index][0], 'Language'
        return

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
    
class Value:
    """
    struct for create iformation for value
    """
    def __init__(self, name, id, list_values, default, old_value=None):
        self.name = name
        self.id = id
        self.list_values = list_values
        self.default = default
        self.old_value = old_value
        
class Main_window:
    """TODO:
    """

    def __init__(self):
        # Create a new window
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("Main window")
        self.window.set_size_request(700, 500)
        self.window.connect("delete_event", self.delete_event)
        self.vbox_main = gtk.VBox()
        self.vbox_main.show()
        self.window.add(self.vbox_main)
        
        # container for body
        vbox_body = gtk.VBox()
        vbox_body.show()
        
        #create menu

        # main menu
        vbox_menu = gtk.Toolbar()
        self.vbox_main.pack_start(vbox_menu, expand=False, fill=True, padding=0)
        self.menu = Menu("menu:main", vbox_menu)
        menu1_but1 = MenuButton("menu:main:btn:main", "Main", vbox_body)
        self.menu.add_item(menu1_but1)
        menu1_but2 = MenuButton("menu:main:btn:tailoring", "Tailoring", vbox_body)
        self.menu.add_item(menu1_but2)
        menu1_but3 = MenuButton("menu:main:btn:edit", "Edit", vbox_body)
        self.menu.add_item(menu1_but3)
        menu1_but4 = MenuButton("menu:main:btn:scan", "Scan", vbox_body)
        self.menu.add_item(menu1_but4)
        menu1_but5 = MenuButton("menu:main:btn:reports", "Reports", vbox_body)
        self.menu.add_item(menu1_but5)
        
        
        # subMenu_but_main
        vbox_submenu = gtk.Toolbar()
        self.vbox_main.pack_start(vbox_submenu, expand=False, fill=True, padding=0)
        self.submenu = Menu("menu:main", vbox_submenu)
        menu2_but1 = MenuButton_XCCDF(vbox_body)
        self.submenu.add_item(menu2_but1)
        menu2_but2 = MenuButton_oval(vbox_body)
        self.submenu.add_item(menu2_but2)
        menu1_but1.set_menu(self.submenu)

        # subMenu_but_tailoring
        vbox_submenu1 = gtk.Toolbar()
        self.vbox_main.pack_start(vbox_submenu1, expand=False, fill=True, padding=0)
        self.submenu1 = Menu("menu:tailoring", vbox_submenu1)
        menu3_but1 = MenuButton_profiles(vbox_body)
        self.submenu1.add_item(menu3_but1)
        menu3_but2 = MenuButton_refines(vbox_body)
        self.submenu1.add_item(menu3_but2)
        menu1_but2.set_menu(self.submenu1)

        # subMenu_but_edit

        # subMenu_but_scan

        # subMenu_but_reports



        self.vbox_main.pack_start(vbox_body, expand=True, fill=True, padding=0)
        
        self.window.show()
        self.menu.show()

    def delete_event(self, widget, event, data=None):
        """ close the window and quit
        """
        gtk.main_quit()
        return False

class create_menu():
    # TODO: CZ -> ENG
    """ sem se presune vytvareni menu
    bude obsahovat slovnik (jmeno taggleButtonu a ukazatel na nej), aby se dalo pridavat pod jednotliva menu
    pres ni se tedy budou moci pridavat dalsi menu
    """
    
    def __init__(self):
        return


if __name__ == "__main__":
	#otool_xample = Core_draw()
	Main_window()
	gtk.main()
