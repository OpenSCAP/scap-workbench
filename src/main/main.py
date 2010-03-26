#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" TODO:
- prijde dat do vlastniho modulu tridy pro vytvareni menu
- pro kazde okno vlastni modul
- v hlavnim modulu se to bude spojovat
"""

import pygtk
import gtk

class Menu:
    """ Create Main item for TreeToolBar_toggleButtonGroup and draw all tree
    Menu
    """
    def __init__(self, id, c_toolBar):
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

        # setings
        self.widget = gtk.ToggleToolButton()
        self.widget.set_is_important(True)
        self.widget.set_label(name)
        if self.sensitivity == None: 
            self.widget.set_sensitive(True)
        else: self.widget.set_sensitive(False)
        self.widget.show()
        self.widget.connect("toggled", self.cb_toggle, self)

    def set_active(self, active):
        self.widget.handler_block_by_func(self.cb_toggle)
        self.widget.set_active(active)
        if self.menu: self.menu.set_active(active)
        self.widget.handler_unblock_by_func(self.cb_toggle)

    def set_menu(self, menu):
        self.menu = menu

    def cb_toggle(self, widget, item):
        """ Change active of toggleButtons in current toolBar
        and visibility of child
        """
        self.parent.toggle_button(self)
            

class Main_window:
    """TODO:
    """

    def __init__(self):
        # Create a new window
		
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("Main window")
        self.window.set_size_request(300, 300)
        self.window.connect("delete_event", self.delete_event)
        self.vbox_main = gtk.VBox()
        self.vbox_main.show()
        self.window.add(self.vbox_main)
        
        # container for body
        vbox_body = gtk.VBox()
        vbox_body.show()
        
        #create menu

        # menu 1
        vbox_menu = gtk.Toolbar()
        self.vbox_main.pack_start(vbox_menu, expand=False, fill=True, padding=0)
        self.menu = Menu("menu:main", vbox_menu)
        menu1_but1 = MenuButton("menu:main:btn1", "XCCDF", vbox_body)
        self.menu.add_item(menu1_but1)
        menu1_but2 = MenuButton("menu:main:btn1", "OVAL", vbox_body)
        self.menu.add_item(menu1_but2)

        # menu 2
        vbox_submenu = gtk.Toolbar()
        self.vbox_main.pack_start(vbox_submenu, expand=False, fill=True, padding=0)
        self.submenu = Menu("menu:XCCDF", vbox_submenu)
        menu2_but1 = MenuButton("menu:XCCDF:btn1", "XCCDF button1", vbox_body)
        self.submenu.add_item(menu2_but1)
        menu2_but2 = MenuButton("menu:XCCDF:btn2", "XCCDF button2", vbox_body)
        self.submenu.add_item(menu2_but2)
        menu1_but1.set_menu(self.submenu)

        # menu 3
        vbox_submenu1 = gtk.Toolbar()
        self.vbox_main.pack_start(vbox_submenu1, expand=False, fill=True, padding=0)
        self.submenu1 = Menu("menu:OVAL", vbox_submenu1)
        menu3_but1 = MenuButton("menu:OVAL:btn1", "OVAL button1", vbox_body)
        self.submenu1.add_item(menu3_but1)
        menu3_but2 = MenuButton("menu:OVAL:btn2", "OVAL button2", vbox_body)
        self.submenu1.add_item(menu3_but2)
        menu1_but2.set_menu(self.submenu1)

        self.vbox_main.pack_start(vbox_body, expand=True, fill=True, padding=0)
        
        self.window.show()
        self.menu.show()

    def delete_event(self, widget, event, data=None):
        """ close the window and quit
        """
        gtk.main_quit()
        return False

class menu():
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
