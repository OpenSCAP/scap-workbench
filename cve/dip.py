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
		Interface_GUI.treeview_seznamCVE = self.__wTree.get_widget("treeview_seznamCVE")    # komponenta treeview, do ktere se nahraje seznam CVE
		Interface_GUI.textview_detailCVE = self.__wTree.get_widget("textview_detailCVE")	# komponenta ktera slouzi pro zobrazeni detailu CVE ze seznamu

	def btnHelloWorld_clicked(self, widget):
		print "Hello World!"


class Imp_CVE_to_treeModelList:
	""" Nacte soubor s CVE do treeModelou ve tvaru: CVE;info;entry
		a pri poklepu na konkretni CVE nacte jeho detail do wiget_text"""
	
	def __init__(self,widget_tree,widget_text,imp_cve):
		
		# nacteni zdroje dat CVE do modelu
		self.__widget_text = widget_text
		self.entry_to_text = Entry_to_text(self.__widget_text)
		try:
			src = openscap.oscap_import_source_new_file(imp_cve, "UTF-8")
			model = openscap.cve_model_import(src)
			entry_iter = openscap.cve_model_get_entries(model)
		except:
			print "ERROR: Incorect format xml file with CVE"
			exit(1)
		
		# create a ListStore (model) wirh cve (cve- id, cve summary, cve-entry)
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
			
			# data move to list store (model)
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
		column = gtk.TreeViewColumn('CVE ID', gtk.CellRendererText(),text=0) # text: je nastaveni sloupce z modelu, ktery se pouzije
		column.set_sort_column_id(0)           # poradi sloupce ve view
		widget_tree.append_column(column)
		
		# column for score CVESS
		cell = gtk.CellRendererText()
		column = gtk.TreeViewColumn('CVSS score', cell)
		column.set_cell_data_func(cell, self.entry_score)
		column.set_sort_column_id(1)
		widget_tree.append_column(column)
		
		# column for cve description
		cell = gtk.CellRendererText()
		#cell.set_property('stretch',1)
		column = gtk.TreeViewColumn('CVE description', cell,text=1) 
		column.set_sort_column_id(2)
		widget_tree.append_column(column)
		
		# nastaven reakce na vyber radku v treeview
		selection = widget_tree.get_selection()
		selection.set_mode(gtk.SELECTION_SINGLE)
		selection.connect("changed", self.on_selection_changed)
		return
		
	#call_back for select row in treeview 
	def on_selection_changed(self, selection):
		treeview = selection.get_tree_view()
		model, iter = selection.get_selected()
		if iter:
			entry = model.get_value(iter, 2)    # vezme pole vybraneho radku
			self.entry_to_text.entry_to_text(entry)
		return
	
	# renderer column for score, provede pro kazdou bunku pri vykresleni
	def entry_score(self, column, cell, model, iter):
		score =  model.get_value(iter, 3)				# vybrani sloupce z modelu
		cell.set_property('text','%.2f'%(score))
		return

class Entry_to_text:
	""" vezme entry zaznam a vypise jej do textoveho pole"""
	def __init__(self,widget_text):
		self.__widget_text = widget_text
		
		# nastaveni zalamovani radku na sloava pokud je okno vetsi
		self.__widget_text.set_wrap_mode(gtk.WRAP_WORD) 
		self.__textbuffer = self.__widget_text.get_buffer()
		
		# vytvoreni typu formatovani pro text
		tag = self.__textbuffer.create_tag('title')
		tag.set_property('weight',pango.WEIGHT_BOLD)
		tag.set_property('justification',gtk.JUSTIFY_CENTER )
		tag.set_property('size-points',14)
		tag.set_property('pixels-above-lines',15)
		tag.set_property('pixels-below-lines',15)

		# vytvoreni typu formatovani pro text
		tag = self.__textbuffer.create_tag('head1')
		tag.set_property('weight',pango.WEIGHT_BOLD)
		tag.set_property('left-margin',20)
		tag.set_property('size-points',12)
		tag.set_property('pixels-above-lines',10)
		tag.set_property('pixels-below-lines',10)

		# vytvoreni typu formatovani pro text
		tag = self.__textbuffer.create_tag('head2')
		tag.set_property('weight',pango.WEIGHT_BOLD)
		
		tag = self.__textbuffer.create_tag('text')
		
		return
	
	def entry_to_text(self,entry):
		
		#pripraveni dat do textbufferr
		self.__textbuffer.set_text("")
		enditer = self.__textbuffer.get_end_iter()

		# nacteni dat z entry
		entry_id_text  = openscap.cve_entry_get_id(entry)
		if entry_id_text <> None:
			self.__textbuffer.insert_with_tags_by_name(enditer,"Vulnerability Summary for " + entry_id_text + "\n",'title')
		
		entry_publihed_text = openscap.cve_entry_get_published(entry)
		if entry_publihed_text <> None:
			self.__textbuffer.insert_with_tags_by_name(enditer,"Original release date: ",'head2')
			self.__textbuffer.insert_with_tags_by_name(enditer,self.parse_date(entry_publihed_text) + "\n",'text')
		
		entry_lastModify_text = openscap.cve_entry_get_modified(entry)
		if entry_lastModify_text <> None:
			self.__textbuffer.insert_with_tags_by_name(enditer,"Last revised: ",'head2')
			self.__textbuffer.insert_with_tags_by_name(enditer,self.parse_date(entry_lastModify_text) + "\n",'text')
		
		entry_cwe_text = openscap.cve_entry_get_cwe(entry)
		if entry_cwe_text <> None:
			self.__textbuffer.insert_with_tags_by_name(enditer,"CWE: ",'head2')
			self.__textbuffer.insert_with_tags_by_name(enditer,entry_cwe_text + "\n",'text')
			
		entry_protection_text = openscap.cve_entry_get_sec_protection(entry)
		if entry_protection_text  <> None:
			self.__textbuffer.insert_with_tags_by_name(enditer,"Protection: ",'head2')
			self.__textbuffer.insert_with_tags_by_name(enditer,entry_protection_text + "\n",'text')
		
		# nacteni summary
		entry_summary_iter = openscap.cve_entry_get_summaries(entry)
		self.__textbuffer.insert_with_tags_by_name(enditer,"Overview\n",'head1')
		while openscap.cve_summary_iterator_has_more (entry_summary_iter):
			entry_summary = openscap.cve_summary_iterator_next(entry_summary_iter)
			entry_summary_text = openscap.cve_summary_get_summary(entry_summary)
			self.__textbuffer.insert_with_tags_by_name(enditer,entry_summary_text + '\n' ,'text')
		openscap.cve_summary_iterator_free(entry_summary_iter)
		
		#nacti cvss
		self.__textbuffer.insert_with_tags_by_name(enditer,"Impact\n",'head1')
		cvss_entry = openscap.cve_entry_get_cvss(entry)
		if cvss_entry <> None:
			cvss_entry_source_text = openscap.cvss_entry_get_source(cvss_entry)
			if cvss_entry_source_text <> None:
				self.__textbuffer.insert_with_tags_by_name(enditer,"Source: ",'head2')
				self.__textbuffer.insert_with_tags_by_name(enditer,cvss_entry_source_text + "\n",'text')
			
			cvss_entry_generated_text = openscap.cvss_entry_get_generated(cvss_entry)
			if cvss_entry_generated_text <> None:
				self.__textbuffer.insert_with_tags_by_name(enditer,"Generated: ",'head2')
				self.__textbuffer.insert_with_tags_by_name(enditer,self.parse_date(cvss_entry_generated_text) + "\n",'text')
				
			cvss_entry_score_text = openscap.cvss_entry_get_score(cvss_entry)
			if cvss_entry_score_text <> None:
				self.__textbuffer.insert_with_tags_by_name(enditer,"CVSS score: ",'head2')
				self.__textbuffer.insert_with_tags_by_name(enditer,cvss_entry_score_text + "\n",'text')
				
			cvss_entry_supported_text = openscap.cvss_model_supported()
			if cvss_entry_supported_text <> None:
				self.__textbuffer.insert_with_tags_by_name(enditer,"Supported: ",'head2')
				self.__textbuffer.insert_with_tags_by_name(enditer,cvss_entry_supported_text+ "\n",'text')
				
			# basic vectror
			cvss_vector = self.cvss_get_vectro(cvss_entry)
			self.__textbuffer.insert_with_tags_by_name(enditer,"Basic vector: ",'head2')
			self.__textbuffer.insert_with_tags_by_name(enditer,cvss_vector+ "\n",'text')

		
		#nacti reference
		self.__textbuffer.insert_with_tags_by_name(enditer,"References to Advisories, Solutions, and Tools\n",'head1')
		entry_reference_iter = openscap.cve_entry_get_references(entry)
		while openscap.cve_reference_iterator_has_more(entry_reference_iter):
			entry_reference = openscap.cve_reference_iterator_next(entry_reference_iter)
			
			entry_reference_source_text  = openscap.cve_reference_get_source(entry_reference)
			if entry_reference_source_text <> None:
				self.__textbuffer.insert_with_tags_by_name(enditer,"Source: ",'head2')
				self.__textbuffer.insert_with_tags_by_name(enditer,entry_reference_source_text+ "\n",'text')

			entry_reference_typ_text  = openscap.cve_reference_get_type(entry_reference)
			if entry_reference_typ_text <> None:
				self.__textbuffer.insert_with_tags_by_name(enditer,"Type: ",'head2')
				self.__textbuffer.insert_with_tags_by_name(enditer,entry_reference_typ_text+ "\n",'text')

			entry_reference_valu_text  = openscap.cve_reference_get_value(entry_reference)
			if entry_reference_valu_text <> None:
				self.__textbuffer.insert_with_tags_by_name(enditer,"Name: ",'head2')
				self.__textbuffer.insert_with_tags_by_name(enditer,entry_reference_valu_text + "\n",'text')
				
			entry_reference_href_text  = openscap.cve_reference_get_href(entry_reference)
			if entry_reference_href_text <> None:
				self.__textbuffer.insert_with_tags_by_name(enditer,"Hyperlink: ",'head2')
				self.__textbuffer.insert_with_tags_by_name(enditer,entry_reference_href_text+ "\n",'text')
				self.__textbuffer.insert_with_tags_by_name(enditer,"\n",'text')
		openscap.cve_reference_iterator_free(entry_reference_iter)
		
		# nacti produkt
		self.__textbuffer.insert_with_tags_by_name(enditer,"Vulnerable software and versions\n",'head1')
		entry_product_iter = openscap.cve_entry_get_products(entry)
		while openscap.cve_product_iterator_has_more(entry_product_iter):
			entry_product = openscap.cve_product_iterator_next(entry_product_iter) 
			entry_product_text = openscap.cve_product_get_value(entry_product)
			if entry_product_text <> None:
				self.__textbuffer.insert_with_tags_by_name(enditer,"Product: ",'head2')
				self.__textbuffer.insert_with_tags_by_name(enditer,entry_product_text + "\n",'text')
				""" nacteni a parsrovani CPE na jednotlive prvky "cpe_name"
				name_product = openscap.cpe_name_new (entry_product_text)
				entry_product_product_text = openscap.cpe_name_get_product (name_product)
				if entry_product_product_text  <> None:
					text = text +"Product: "+ entry_product_product_text + ";  " 
				entry_product_version_text = openscap.cpe_name_get_version (name_product)
				if entry_product_version_text  <> None:
					text = text + "Version: " + entry_product_version_text + ";  " 
				entry_product_version_text = openscap.cpe_name_get_part (name_product)
				if entry_product_version_text  <> None:
					text = text + "Part: " + str(entry_product_version_text) + ";  " """
		openscap.cve_product_iterator_free(entry_product_iter)
		
		#zobrazi data do textview
		self.__widget_text.set_buffer(self.__textbuffer)
		return
		
	def cvss_get_vectro(self,cvss_entry):
		""" read and create basic vectrot vfrom cve_entry"""
		
		cvss_entry_AV_text = openscap.cvss_entry_get_AV(cvss_entry)
		text = '(AV:' + cvss_entry_AV_text[0]

		cvss_entry_AC_text = openscap.cvss_entry_get_AC (cvss_entry)
		text = text +'/AC:' + cvss_entry_AC_text[0]
			
		cvss_entry_authentication_text = openscap.cvss_entry_get_authentication(cvss_entry)
		text = text + '/Au:' + cvss_entry_authentication_text[0]

		cvss_entry_confidentiality_text = openscap.cvss_entry_get_imp_confidentiality(cvss_entry)
		text = text + '/C:' + cvss_entry_confidentiality_text[0]

		cvss_entry_integrity_text = openscap.cvss_entry_get_imp_integrity (cvss_entry)
		text = text + '/I:' + cvss_entry_integrity_text[0]
			
		cvss_entry_availability_text = openscap.cvss_entry_get_imp_integrity (cvss_entry)
		text = text + '/A:' + cvss_entry_availability_text[0] + ')'
		return text
		
	def parse_date(self,date):
		""" parse date from cve XML"""
		text = date[8:10]
		text = text + '/' + date[5:7]
		text = text + '/' + date[0:4]
		return text
		
if __name__ == "__main__":

	interface_GUI_glade = Create_interface_GUI_from_glade("dip.glade")
	tree_model_list = Imp_CVE_to_treeModelList(Interface_GUI.treeview_seznamCVE,Interface_GUI.textview_detailCVE,"/tmp/scap/usr/local/lib/python2.6/site-packages/otool/CVE/cve.xml")
	
	gtk.main()
