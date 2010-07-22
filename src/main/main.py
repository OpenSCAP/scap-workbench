#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" TODO:
- Zmen si odsadenie tabulatora na 4 znaky a dodrzuj odstupy medzi zaciatkom riadku a funkciami a teplom funckcie
- Dodrziavaj ten isty format pre komentare "#" a popis funckcii, objektov 3x "
- Pozor na definicie a volania funkcii - <nazov_funckcie>(parameter1, parameter2=hodnota, ...) (medzery!)
- Vyhladaj a dorob TODO
- prijde dat do vlastniho modulu tridy pro vytvareni menu
- pro kazde okno vlastni modul
- v hlavnim modulu se to bude spojovat
"""

import pygtk
import gtk

class TreeToolBar_toggleButtonGroup:
    """ Create Main item for TreeToolBar_toggleButtonGroup and draw all tree
    """
	
    def __init__(self, container_for_body, container_for_toolBar):
        self.container_for_body = container_for_body
        self.container_for_toolBar = container_for_toolBar
        self.main_item = Item_treeToolBar_toggleButtonGroup(self, None)
	
    def add_item(self, item, selected=False, position=None):
        self.main_item.add_item(item, selected, position)
    
    def init_draw(self, sensitive = False):
        """init all TreeToolBar_toggleButtonGroup
        if sensitive = True set sensitive to toggleButton
        """
        self.container_for_toolBar.show()
        self.init_selected(self.main_item, sensitive)
            
    def init_selected(self, item, sensitive=False):
        """init branch TreeToolBar_toggleButtonGroup
        if sensitive = True set sensitive to toggleButton
        """
        for n in item.toggleButtonGroup_child:
                if n.container_child != None:
                        n.container_child.hide()
                init_selected(n)
        if item.selected_item_child.container_child != None:
                item.selected_item_child.container_child.show()
        item.container_child.show()

    def callback_toggleButton(self, widget, item):
        """ Change active of toggleButtons in current toolBar
        and visibility of child
        """
        old_active_item = item.parent_item.selected_item_child

        if old_active_item == item:
            self.change_select(item, True)
        else:
            # Deselect and select new item (active)
            self.change_select(old_active_item, False)
            item.parent_item.selected_item_child = item
            
            # hide and show toolBar
            if old_active_item.container_child != None:
                    old_active_item.container_child.hide()
            if item.container_child != None:
                    item.container_child.show()
        return
            
    def change_select(self, item, active):
        item.toggleButton.handler_block_by_func(self.callback_toggleButton)
        item.toggleButton.set_active(active)
        item.toggleButton.handler_unblock_by_func(self.callback_toggleButton)
        return
		

class Item_treeToolBar_toggleButtonGroup:
    """ Class for tree of toogleBar with toggleButtons in group
    """

    def __init__(self, treeToolBar_toggleButtonGroup, name, container_with_body=None, condition_sensitivity=None):
        # structure
        self.treeToolBar_toggleButtonGroup = treeToolBar_toggleButtonGroup  # main group
        self.toggleButtonGroup_child = []		                    # list of Item_treeToolBar_toggleButtonGroup direct chlidrens
        self.container_child = None				            # instance container of dependeci toolBar
        self.toolBar_child = None				            # instance toolbar for toggleButtonGroup
        self.parent_item = None					            #

        # information
        self.selected_item_child = None                         # který toggleButon v primem potomku je active (predelat primo na togglebutton) (TODO CZ->ENG)
        self.condition_sensitivity = condition_sensitivity	#f-ce for resolve sensitive return tre or false (if none always True)
        
        # function
        self.container_with_body = container_with_body		# container of body (top level has None)

        #togglebutton if not main
        if treeToolBar_toggleButtonGroup != None:
            # setings
            self.toggleButton = gtk.ToggleButton(name)	# instance of toggleButton(top level has None))
            self.toggleButton.set_sensitive(True)		# init sensitivity
            self.toggleButton.show()
            self.toggleButton.connect("toggled", self.treeToolBar_toggleButtonGroup.callback_toggleButton, self)
            self.active = name
		
    def add_item(self,item,selected = False, position = None):
        """ Add item (Item_treeToolBar_toggleButtonGroup) to child toolBar
        """
        
        item.parent_item = self

        if len(self.toggleButtonGroup_child) > 0:
            self.toggleButtonGroup_child[len(self.toggleButtonGroup_child):] = item
        else:
            toggleButtonGroup_child = [item]
        
        if self.container_child == None:
            # first add
            self.container_child = gtk.VBox()
            self.toolBar_child = gtk.Toolbar()
            self.toolBar_child.show()
            self.container_child.pack_start(self.toolBar_child, expand=False, fill=True, padding=0)
            
            # if parent_item == None it is main item // musi se pridavat postupne ne spojovat ruzne vetve
            # jink to presmeruje na Main item
            if self.parent_item == None:
                container = self.treeToolBar_toggleButtonGroup.container_for_toolBar
                container.pack_start(self.container_child, expand=False, fill=True, padding=0)
            else:
                self.parent_item.container_child.pack_start(self.container_child, expand=False, fill=True, padding=0)
        # add widget to toolBar
        separator = gtk.VSeparator()
        separator.show()
        self.toolBar_child.add(separator)
        self.toolBar_child.add(item.toggleButton)
        
        if position != None:
            item.toggleButton.position = position * 2	
            separator.positon = position * 2
        
        # resolving selected
        if selected == True:
            # set selected this item
            if self.selected_item_child != None:
                #Deselect selected item
                self.treeToolBar_toggleButtonGroup.change_select(self.selected_item_child, False)
                    
            self.treeToolBar_toggleButtonGroup.change_select(item, True)
            self.selected_item_child = item
                
        elif self.selected_item_child == None:
            #some tooggleButton must be selected
            self.selected_item_child = item
            self.treeToolBar_toggleButtonGroup.change_select(item, True)
        
        # init visible toolbar
        self.treeToolBar_toggleButtonGroup.init_draw()
            
    def del_item(self,item):
            """ Delete item (Item_treeToolBar_toggleButtonGroup) from child toolBar
            """
            raise NotImplementedError, "Function not implemented yet"
	

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
        vbox_menu = gtk.VBox()
        vbox_menu.show()
        self.vbox_main.pack_start(vbox_menu, expand=False, fill=True, padding=0)
        self.treeToolBar_toggleButtonGroup = TreeToolBar_toggleButtonGroup(vbox_menu, vbox_body)
        #main_item = self.treeToolBar_toggleButtonGroup.main_item()
        # menu 1
        menu1_but1 = Item_treeToolBar_toggleButtonGroup(self.treeToolBar_toggleButtonGroup, "menu 1.1", container_with_body=None, condition_sensitivity=None)
        self.treeToolBar_toggleButtonGroup.add_item(menu1_but1, True)
        menu1_but2 = Item_treeToolBar_toggleButtonGroup(self.treeToolBar_toggleButtonGroup, "menu 1.2", container_with_body=None, condition_sensitivity=None)
        self.treeToolBar_toggleButtonGroup.add_item(menu1_but2, False)
        menu1_but3 = Item_treeToolBar_toggleButtonGroup(self.treeToolBar_toggleButtonGroup, "menu 1.3", container_with_body=None, condition_sensitivity=None)
        self.treeToolBar_toggleButtonGroup.add_item(menu1_but3, False)
        
        # menu 2b1
        menu2b1_but1 = Item_treeToolBar_toggleButtonGroup(self.treeToolBar_toggleButtonGroup, "menu 2.1 button1", container_with_body=None, condition_sensitivity=None)
        menu1_but1.add_item(menu2b1_but1, False)
        menu2b1_but2 = Item_treeToolBar_toggleButtonGroup(self.treeToolBar_toggleButtonGroup, "menu 2.2 button1", container_with_body=None, condition_sensitivity=None)
        menu1_but1.add_item(menu2b1_but2, True)
        
        # menu 2b2
        menu2b2_but1 = Item_treeToolBar_toggleButtonGroup(self.treeToolBar_toggleButtonGroup, "menu 2.1 button2", container_with_body=None, condition_sensitivity=None)
        menu1_but2.add_item(menu2b2_but1, False)
        menu2b2_but2 = Item_treeToolBar_toggleButtonGroup(self.treeToolBar_toggleButtonGroup, "menu 2.2 button2", container_with_body=None, condition_sensitivity=None)
        menu1_but2.add_item(menu2b2_but2, False)
        
        # menu 3b2
        menu3b2b2_but1 = Item_treeToolBar_toggleButtonGroup(self.treeToolBar_toggleButtonGroup, "menu 3.1 button2", container_with_body=None, condition_sensitivity=None)
        menu2b2_but2.add_item(menu3b2b2_but1, False)
        menu3b2b3_but2 = Item_treeToolBar_toggleButtonGroup(self.treeToolBar_toggleButtonGroup, "menu 3.2 button2", container_with_body=None, condition_sensitivity=None)
        menu2b2_but2.add_item(menu3b2b3_but2, False)
        self.vbox_main.pack_start(vbox_body, expand=True, fill=True, padding=0)
        
        self.window.show()
        return

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
