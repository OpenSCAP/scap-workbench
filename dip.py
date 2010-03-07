#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
try:
 	import pygtk
  	pygtk.require("2.0")
except:
	print "import fail 1"
  	pass
try:
	import gtk
	import gobject
	import gtk.glade
	import openscap
except:
	print "import fail 2"
	sys.exit(1)

class Interface_GUI(object):
	""" Rozhrani ke komponentam GUI"""
	treeview_seznamCVE = None
	textview_detailCVE = None
	
	def __init__(self):
		pass

class Create_interface_GUI_from_glade:
	"""This class create GUI and interface for using GUI"""

	def __init__(self,gladefile):
		
		#Create GUI
		try:
			self.__wTree = gtk.glade.XML(gladefile)
		except:
			print "ERROR: import glade file"
			exit(1)
		
		#Create our dictionay and connect it (signals)
		dic = { "on_button4_clicked" : self.btnHelloWorld_clicked,
				"on_window1_destroy" : gtk.main_quit }
		self.__wTree.signal_autoconnect(dic)
		
		#Set intervafce with widgets
		Interface_GUI.treeview_seznamCVE = self.__wTree.get_widget("treeview_seznamCVE")
		Interface_GUI.textview_detailCVE = self.__wTree.get_widget("textview_detailCVE")

	def btnHelloWorld_clicked(self, widget):
		print "Hello World!"


class Imp_CVE_to_treeModelList:
	""" Nacte soubor s CVE do treeModelou ve tvaru: CVE;info;entry"""
	
	def __init__(self,widget_tree,widget_text,imp_cve):
		
		# nacteni zdroje dat CVE do modelu
		self.widget_text = widget_text
		try:
			src = openscap.oscap_import_source_new_file(imp_cve, "UTF-8")
			model = openscap.cve_model_import(src)
			entry_iter = openscap.cve_model_get_entries(model)
		except:
			print "ERROR: Incorect format xml file with CVE"
			exit(1)
		
		# create a ListStore wirh cve (cve- id, cve summary, cve-entry)
		list_store = gtk.ListStore(
			gobject.TYPE_STRING,
			gobject.TYPE_STRING,
			gobject.TYPE_PYOBJECT,
			gobject.TYPE_FLOAT)
		
		# zpracovani jednotlivych zaznamu
		while openscap.cve_entry_iterator_has_more(entry_iter):
			
			entry = openscap.cve_entry_iterator_next(entry_iter)
			entry_id_text  = openscap.cve_entry_get_id(entry)
			entry_summary_iter = openscap.cve_entry_get_summaries(entry)
			
			# nacteni summary
			entry_summary_text_all = ""
			while openscap.cve_summary_iterator_has_more (entry_summary_iter):
				entry_summary = openscap.cve_summary_iterator_next(entry_summary_iter)
				entry_summary_text = openscap.cve_summary_get_summary(entry_summary)
				entry_summary_text_all = entry_summary_text_all + entry_summary_text
			openscap.cve_summary_iterator_free(entry_summary_iter)
			
			cvss_entry = openscap.cve_entry_get_cvss(entry)
			if cvss_entry <> None:
				cvss_entry_score_text = openscap.cvss_entry_get_score(cvss_entry)
				if cvss_entry_score_text <> None:
					scoreCVSS = eval(cvss_entry_score_text)
				else:
					scoreCVSS = ""
			
			# data move to list store
			iter_lStore = list_store.append()
			list_store.set(iter_lStore,
				0, entry_id_text,
				1, entry_summary_text_all,
				2, entry,
				3, scoreCVSS)
				
		openscap.cve_entry_iterator_free(entry_iter)
		
		# set model to treeview
		widget_tree.set_model(list_store)
		
		# column for id - cve
		column = gtk.TreeViewColumn('CVE ID', gtk.CellRendererText(),
									text=0)
		column.set_sort_column_id(0)
		widget_tree.append_column(column)
		
		# column for score CVESS
		column = gtk.TreeViewColumn('CVSS score', gtk.CellRendererText(),
									text=3)
		column.set_sort_column_id(3)
		widget_tree.append_column(column)
		
		# column for cve description
		column = gtk.TreeViewColumn('CVE description', gtk.CellRendererText(),
									text=1)
		column.set_sort_column_id(1)
		widget_tree.append_column(column)
		
		# nastaven reakce na vyber raku v treeview
		selection = widget_tree.get_selection()
		selection.set_mode(gtk.SELECTION_SINGLE)
		selection.connect("changed", self.on_selection_changed)
	
	#call_back for select row in treeview 
	def on_selection_changed(self, selection):
		treeview = selection.get_tree_view()
		model, iter = selection.get_selected()
		if iter:
			entry = model.get_value(iter, 2)    # vezme pole vybraneho radku
			Entry_to_text(self.widget_text,entry)




class Entry_to_text:
	""" vezme entry zaznam a vypise jej do textoveho pole"""
	
	def __init__(self,widget_text,entry):
		
		#pripraveni dat dotextbufferr
		widget_text.set_wrap_mode(gtk.WRAP_WORD) # nastaveni zalamovani radku na sloav pokud je okno vetsi
		textbuffer = widget_text.get_buffer()
		
		# nacteni dat z entry
		entry_id_text  = openscap.cve_entry_get_id(entry)
		if entry_id_text <> None:
			text = "Vulnerability Summary for " + entry_id_text + "\n"
		
		entry_publihed_text = openscap.cve_entry_get_published(entry)
		if entry_publihed_text <> None:
			text = text +  "Original release date: " + entry_publihed_text + "\n"
		
		entry_lastModify_text = openscap.cve_entry_get_modified(entry)
		if entry_lastModify_text <> None:
			text = text +  "Last revised: " + entry_lastModify_text + "\n"
		
		entry_cwe_text = openscap.cve_entry_get_cwe(entry)
		if entry_cwe_text <> None:
			text = text +  "CWE: " + entry_cwe_text + "\n"
		
		entry_protection_text = openscap.cve_entry_get_sec_protection(entry)
		if entry_protection_text  <> None:
			text = text +  "protection: " + entry_protection_text + "\n"
		
		# nacteni summary
		entry_summary_iter = openscap.cve_entry_get_summaries(entry)
		text = text +  "Overview\n\t"
		while openscap.cve_summary_iterator_has_more (entry_summary_iter):
			entry_summary = openscap.cve_summary_iterator_next(entry_summary_iter)
			entry_summary_text = openscap.cve_summary_get_summary(entry_summary)
			text = text + entry_summary_text + "\n"
		openscap.cve_summary_iterator_free(entry_summary_iter)
		
		#nacti cvss
		text =text + "Impact\n"
		cvss_entry = openscap.cve_entry_get_cvss(entry)
		if cvss_entry <> None:
			cvss_entry_score_text = openscap.cvss_entry_get_score(cvss_entry)
			if cvss_entry_score_text <> None:
				text = text +  "CVSS score: " + cvss_entry_score_text + "\n"
			cvss_entry_AV_text = openscap.cvss_entry_get_AV(cvss_entry)
			if cvss_entry_AV_text <> None:
				text = text +  "AV vector: " + cvss_entry_AV_text + "\n"
			cvss_entry_AC_text = openscap.cvss_entry_get_AC (cvss_entry)
			if cvss_entry_AC_text <> None:
				text = text +  "AC vector: " + cvss_entry_AC_text + "\n"
			cvss_entry_authentication_text = openscap.cvss_entry_get_authentication(cvss_entry)
			if cvss_entry_AC_text <> None:
				text = text +  "authentication: " + cvss_entry_authentication_text + "\n"
			cvss_entry_confidentiality_text = openscap.cvss_entry_get_imp_confidentiality(cvss_entry)
			cvss_entry_integrity_text = openscap.cvss_entry_get_imp_integrity (cvss_entry)
			cvss_entry_availability_text = openscap.cvss_entry_get_imp_availability(cvss_entry)
			cvss_entry_source_text = openscap.cvss_entry_get_source(cvss_entry)
			cvss_entry_generated_text = openscap.cvss_entry_get_generated(cvss_entry)
			cvss_entry_supported_text = openscap.cvss_model_supported()
		
		#Impact
		
		#nacti reference
		entry_reference_iter = openscap.cve_entry_get_references(entry)
		while openscap.cve_reference_iterator_has_more(entry_reference_iter):
			entry_reference = openscap.cve_reference_iterator_next(entry_reference_iter)
			entry_reference_valu_text  = openscap.cve_reference_get_value(entry_reference)
			entry_reference_href_text  = openscap.cve_reference_get_href(entry_reference)
			entry_reference_typ_text  = openscap.cve_reference_get_type(entry_reference)
			entry_reference_source_text  = openscap.cve_reference_get_source(entry_reference)
		openscap.cve_reference_iterator_free(entry_reference_iter)
		
		# nacti produkt
		entry_product_iter = openscap.cve_entry_get_products(entry)
		while openscap.cve_product_iterator_has_more(entry_product_iter):
			entry_product = openscap.cve_product_iterator_next(entry_product_iter) 
			entry_product_text = openscap.cve_product_get_value(entry_product)
		openscap.cve_product_iterator_free(entry_product_iter)
		
			
		#zobrazi data do textview
		textbuffer.set_text(text)
		widget_text.set_buffer(textbuffer)
		
		# nacti
		"""entry_config_iter = openscap.cve_entry_get_configurations(entry)
		while openscap.cve_configuration_iterator_has_more(entry_config_iter):
			entry_config = opnscap.cve_configuration_iterator_next(entry_config_iter)
			cpe_entry = openscap.cve_configuration_get_expr(entry_config)"""
			
		
if __name__ == "__main__":

	interface_GUI_glade = Create_interface_GUI_from_glade("dip.glade")
	tree_model_list = Imp_CVE_to_treeModelList(Interface_GUI.treeview_seznamCVE,Interface_GUI.textview_detailCVE,"CVE/cve.xml")
	
	gtk.main()
