#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
	import sys
	sys.path.append("/tmp/scap/usr/local/lib/python2.6/site-packages")
	import gtk
	import pygtk
	import gobject
	import gtk.glade
	import openscap
	import pango
	pygtk.require("2.0")
except:
	print "problem import"


class GUI_glade:
	"""This class create GUI and interface for using GUI"""
	treeview_XCCDF = None
	textview_XCCDF = None
	filechooserdialog = None

	def __init__(self,gladefile):
		
		#Create GUI
		try:
			self.__wTree = gtk.glade.XML(gladefile)
		except:
			print "ERROR: import glade file"
			exit(1)

		#Get interface on widgets
		GUI_glade.treeview_XCCDF = self.__wTree.get_widget("treeview_XCCDF")
		GUI_glade.textview_XCCDF = self.__wTree.get_widget("textview_XCCDF")
		GUI_glade.filechooserdialog = self.__wTree.get_widget("filechooserdialog1")
		
		#Provazani signalu z glade na vlastni nebo systemove funkce
		dic = { "on_button4_clicked" : self.btnHelloWorld_clicked,
				"on_window1_destroy" : gtk.main_quit,
				"on_menuButton_destroy" : gtk.main_quit,
				"on_menuOpenXCCDF_activate" : self.showOpenDialog 
				}
		self.__wTree.signal_autoconnect(dic)
		return
		
	def showOpenDialog(self,widget):
		if GUI_glade.filechooserdialog  <> None:
			GUI_glade.filechooserdialog.show()		# nebo GUI_glade.filechooserdialog.set_property("visible",True)
			# pokud bych spustel primo ne z glade 
				#chooser = gtk.FileChooserDialog(title=None,action=gtk.FILE_CHOOSER_ACTION_OPEN,
				#                     buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
				#chooser.show()

		return

	def btnHelloWorld_clicked(self, widget):
		print "Hello World!"
		return
		
class Imp_xccdf_to_treeModel:
	""" This class import XCCDF file to treemodel """
	
	def __init__(self,treeview,textview,xccdf_file):
		""" Read data frorm file to treemodel """
		self.treeview = treeview
		self.textview = textview
		self.xccdf_file= xccdf_file

		# create a TreeStore with one string column to use as the model
		self.treestore = gtk.TreeStore(str)
		try:
			xccdf_src = openscap.oscap_import_source_new_file(self.xccdf_file, "UTF-8")
			xccdf_benchmark = openscap.xccdf_benchmark_import(xccdf_src)
		except:
			print "Spatny soubor xccdf"
		
		xccdf_benchmark_item_iter = openscap.xccdf_benchmark_get_content(xccdf_benchmark)
		self.read_xccdf_struct(self.treestore,xccdf_benchmark_item_iter,None)
		openscap.xccdf_item_iterator_free(xccdf_benchmark_item_iter)
		
		self.treeview.set_model(self.treestore)
		column = gtk.TreeViewColumn('XCCDF ID', gtk.CellRendererText(),text=0) # text: je nastaveni sloupce z modelu, ktery se pouzije
		self.treeview.append_column(column)
		
	def read_xccdf_struct(self,treestore,xccdf_benchmark_item_iter,tree_node = None):
		""" Read structuro of XML(benchmark_content) to treeStore.
			param tree_parent_node: node fo tree model
			param xccdf_benchmark_item_iter: iter of of benchmark_content """
		
		while openscap.xccdf_item_iterator_has_more(xccdf_benchmark_item_iter):
			
			xccdf_benchmark_item = openscap.xccdf_item_iterator_next(xccdf_benchmark_item_iter)
			xccdf_benchmark_group = openscap.xccdf_item_to_group(xccdf_benchmark_item)
			if xccdf_benchmark_group  <> None:
				tree_parent_node = treestore.append(tree_node, [openscap.xccdf_group_get_id(xccdf_benchmark_group)])
				print openscap.xccdf_group_get_id(xccdf_benchmark_group)
			
				# read iter for current group	
				xccdf_benchmark_item_iter1 = openscap.xccdf_group_get_content (xccdf_benchmark_group)
				self.read_xccdf_struct(treestore,xccdf_benchmark_item_iter1,tree_parent_node)
				openscap.xccdf_item_iterator_free(xccdf_benchmark_item_iter1)
		return
		
if __name__ == "__main__":

	interface_GUI = GUI_glade("xccdf.glade")
	tree_model_XCCDF = Imp_xccdf_to_treeModel(GUI_glade.treeview_XCCDF,GUI_glade.textview_XCCDF,"/tmp/scap/usr/local/lib/python2.6/site-packages/otool/src/xccdf/file/scap-rhel5-xccdf.xml")
	
	gtk.main()
	
	
	"""
			i = 0
		j = 0

		xccdf_src = openscap.oscap_import_source_new_file(xccdf_file, "UTF-8")
		xccdf_benchmark = openscap.xccdf_benchmark_import(xccdf_src)
		xccdf_benchmark_item_iter = openscap.xccdf_benchmark_get_content(xccdf_benchmark)
		
		while openscap.xccdf_item_iterator_has_more(xccdf_benchmark_item_iter):
			xccdf_benchmark_item = openscap.xccdf_item_iterator_next(xccdf_benchmark_item_iter)
			xccdf_benchmark_group = openscap.xccdf_item_to_group(xccdf_benchmark_item)
			xccdf_benchmark_item_iter1 = openscap.xccdf_group_get_content (xccdf_benchmark_group)
			while openscap.xccdf_item_iterator_has_more(xccdf_benchmark_item_iter1):
				xccdf_benchmark_item = openscap.xccdf_item_iterator_next(xccdf_benchmark_item_iter1)
				xccdf_benchmark_group = openscap.xccdf_item_to_group(xccdf_benchmark_item)
				print openscap.xccdf_group_get_id(xccdf_benchmark_group)
				j = j + 1
				print "vnitrni" + str(j)
			i= i + 1
			j=0
			print openscap.xccdf_group_get_id(xccdf_benchmark_group)
		print "nejsi" + str(i) """
		