#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" prijde dat do vlastniho modulu tridy pro vytvareni menu"""
""" pro kazde okno vlastni modul """
""" v hlavnim modulu se to bude spojovat"""
import pygtk
import gtk

class TreeToolBar_toggleButtonGroup:
	""" Create Main item for TreeToolBar_toggleButtonGroup and draw all tree"""
	
	def __init__(self,conteiner_for_body,conteiner_for_toolBar):
		self.__conteiner_for_body=conteiner_for_body
		self.__conteiner_for_toolBar=conteiner_for_toolBar
		self.__main_item = Item_treeToolBar_toggleButtonGroup(self,None)
		return
	
	def get_conteiner_for_body(self):
		return self.__conteiner_for_body
		
	def get_conteiner_for_toolBar(self):
		return self.__conteiner_for_toolBar
		
	def get_main_item(self):
		return self.__main_item
		
	def add_item(self,item,selected = False, position = None):
		self.__main_item.add_item(item,selected,position)
	
	def init_draw(self,sensitive = False):
		"""init all TreeToolBar_toggleButtonGroup
		if sensitive  = True se sensitive to toggleButton"""
		self.__conteiner_for_toolBar.show()
		self.init_selected(self.__main_item,sensitive)
		
	def	init_selected(self,item,sensitive = False):
		"""init branch TreeToolBar_toggleButtonGroup
		if sensitive  = True se sensitive to toggleButton"""
		for n in item.toggleButtonGroup_child:
			if n.conteiner_child <> None:
				n.conteiner_child.hide()
			init_selected(n)
		if item.selected_item_child.conteiner_child <> None:
			item.selected_item_child.conteiner_child.show()
		item.conteiner_child.show()

	def callback_toggleButton(self, widget,item):
		#""" Change active of toggleButtons in current toolBar
		#and visibility of child"""
		old_active_item = item.parent_item.selected_item_child
		#print old_active_item
		if old_active_item == item:
			self.change_select(item,True)
		else:
			#Deselect and select new item (active)
			self.change_select(old_active_item,False)
			item.parent_item.selected_item_child = item
			
			# hide and show toolBar
			if old_active_item.conteiner_child <> None:
				old_active_item.conteiner_child.hide()
			if item.conteiner_child <> None:
				item.conteiner_child.show()
		return
		
	def change_select(self,item,active):
		item.toggleButton.handler_block_by_func(self.callback_toggleButton)
		item.toggleButton.set_active(active)
		item.toggleButton.handler_unblock_by_func(self.callback_toggleButton)
		return
		
class Item_treeToolBar_toggleButtonGroup:
	
	""" Class for tree of toogleBar with toggleButtons in group"""
	def __init__(self,treeToolBar_toggleButtonGroup,name, conteiner_with_body = None,condition_sensitivity=None):
		
		# structure
		self.treeToolBar_toggleButtonGroup =treeToolBar_toggleButtonGroup # main group
		self.toggleButtonGroup_child = []		# list of Item_treeToolBar_toggleButtonGroup direct chlidrens
		self.conteiner_child = None				# instance conteiner of dependeci toolBar
		self.toolBar_child = None				# instance toolbar for toggleButtonGroup
		self.parent_item = None					#

		#information
		self.selected_item_child = None # který toggleButon v primem potomku je active (predelat primo na togglebutton)
		self.condition_sensitivity = condition_sensitivity	#f-ce for resolve sensitive return tre or false (if none always True)
		
		# function
		self.conteiner_with_body = conteiner_with_body		# conteiner of body (top level has None)

		#togglebutton if not main
		if treeToolBar_toggleButtonGroup <> None:
			# setings
			self.toggleButton = gtk.ToggleButton(name)		# instance of toggleButton(top level has None))
			self.toggleButton.set_sensitive(True)			# init sensitivity
			self.toggleButton.show()
			self.toggleButton.connect("toggled", self.treeToolBar_toggleButtonGroup.callback_toggleButton,self)
			self.active = name
		return
		
	def add_item(self,item,selected = False, position = None):
		""" Add item (Item_treeToolBar_toggleButtonGroup) to child toolBar"""
		
		#if self.toggleButtonGroup_child <> None:
		if len(self.toggleButtonGroup_child) > 0:
			self.toggleButtonGroup_child[len(self.toggleButtonGroup_child):] = item
		else:
			toggleButtonGroup_child = [item]
		item.parent_item = self
		
		if self.conteiner_child == None:
			# first add
			self.conteiner_child = gtk.VBox()
			self.toolBar_child = gtk.Toolbar()
			self.toolBar_child.show()
			self.conteiner_child.pack_start(self.toolBar_child, expand=False, fill=True, padding=0)
			
			# if parent_item == None it is main item // musi se pridavat postupne ne spojovat ruzne vetve
			# jink to presmeruje na Main item
			if self.parent_item == None:
				conteiner = self.treeToolBar_toggleButtonGroup.get_conteiner_for_toolBar()
				conteiner.pack_start(self.conteiner_child, expand=False, fill=True, padding=0)
			else:
				self.parent_item.conteiner_child.pack_start(self.conteiner_child, expand=False, fill=True, padding=0)
		# add widget to toolBar
		separator = gtk.VSeparator()
		separator.show()
		self.toolBar_child.add(separator)
		self.toolBar_child.add(item.toggleButton)
		
		if position <> None:
			item.toggleButton.position = position * 2	
			separator.positon = position * 2
		
		# resolving selected
		if selected == True:
			# set selected this item
			if self.selected_item_child <> None:
				#Deselect selected item
				self.treeToolBar_toggleButtonGroup.change_select(self.selected_item_child,False)
				
			self.treeToolBar_toggleButtonGroup.change_select(item,True)
			self.selected_item_child = item
			
		elif self.selected_item_child == None:
			#some tooggleButton must be selected
			self.selected_item_child = item
			self.treeToolBar_toggleButtonGroup.change_select(item,True)
		
		# init visible toolbar
		self.treeToolBar_toggleButtonGroup.init_draw()
		
	def del_item(self,item):
		""" Delete item (Item_treeToolBar_toggleButtonGroup) from child toolBar"""
		return
	
class Main_window:

	# close the window and quit
	def delete_event(self, widget, event, data=None):
		gtk.main_quit()
		return False

	def __init__(self):
		# Create a new window
		
		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window.set_title("Main window")
		self.window.set_size_request(300, 300)
		self.window.connect("delete_event", self.delete_event)
		self.vbox_main = gtk.VBox()
		self.vbox_main.show()
		self.window.add(self.vbox_main)
		
		# conteiner for body
		vbox_body = gtk.VBox()
		vbox_body.show()
		
		#create menu
		vbox_menu = gtk.VBox()
		vbox_menu.show()
		self.vbox_main.pack_start(vbox_menu, expand=False, fill=True, padding=0)
		self.treeToolBar_toggleButtonGroup = TreeToolBar_toggleButtonGroup(vbox_menu,vbox_body)
		#main_item = self.treeToolBar_toggleButtonGroup.get_main_item()
		# menu 1
		menu1_but1 = Item_treeToolBar_toggleButtonGroup(self.treeToolBar_toggleButtonGroup,"menu 1.1", conteiner_with_body = None,condition_sensitivity=None)
		self.treeToolBar_toggleButtonGroup.add_item(menu1_but1,True)
		menu1_but2 = Item_treeToolBar_toggleButtonGroup(self.treeToolBar_toggleButtonGroup,"menu 1.2", conteiner_with_body = None,condition_sensitivity=None)
		self.treeToolBar_toggleButtonGroup.add_item(menu1_but2,False)
		menu1_but3 = Item_treeToolBar_toggleButtonGroup(self.treeToolBar_toggleButtonGroup,"menu 1.3", conteiner_with_body = None,condition_sensitivity=None)
		self.treeToolBar_toggleButtonGroup.add_item(menu1_but3,False)
		
		# menu 2b1
		menu2b1_but1 = Item_treeToolBar_toggleButtonGroup(self.treeToolBar_toggleButtonGroup,"menu 2.1 button1", conteiner_with_body = None,condition_sensitivity=None)
		menu1_but1.add_item(menu2b1_but1,False)
		menu2b1_but2 = Item_treeToolBar_toggleButtonGroup(self.treeToolBar_toggleButtonGroup,"menu 2.2 button1", conteiner_with_body = None,condition_sensitivity=None)
		menu1_but1.add_item(menu2b1_but2,True)
		
		# menu 2b2
		menu2b2_but1 = Item_treeToolBar_toggleButtonGroup(self.treeToolBar_toggleButtonGroup,"menu 2.1 button2", conteiner_with_body = None,condition_sensitivity=None)
		menu1_but2.add_item(menu2b2_but1,False)
		menu2b2_but2 = Item_treeToolBar_toggleButtonGroup(self.treeToolBar_toggleButtonGroup,"menu 2.2 button2", conteiner_with_body = None,condition_sensitivity=None)
		menu1_but2.add_item(menu2b2_but2,False)
		
		# menu 3b2
		menu3b2b2_but1 = Item_treeToolBar_toggleButtonGroup(self.treeToolBar_toggleButtonGroup,"menu 3.1 button2", conteiner_with_body = None,condition_sensitivity=None)
		menu2b2_but2.add_item(menu3b2b2_but1,False)
		menu3b2b3_but2 = Item_treeToolBar_toggleButtonGroup(self.treeToolBar_toggleButtonGroup,"menu 3.2 button2", conteiner_with_body = None,condition_sensitivity=None)
		menu2b2_but2.add_item(menu3b2b3_but2,False)
		self.vbox_main.pack_start(vbox_body, expand=True, fill=True, padding=0)
		
		self.window.show()
		return

class menu():
	""" sem se presune vytvareni menu
	bude obsahovat slovnik (jmeno taggleButtonu a ukazatel na nej), aby se dalo pridavat pod jednotliva menu
	pres ni se tedy budou moci pridavat dalsi menu"""
	
	def __init__(self):
		
		return
def main():
	gtk.main()
	
if __name__ == "__main__":
	#otool_xample = Core_draw()
	Main_window()
	main()
