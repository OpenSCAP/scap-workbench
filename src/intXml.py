#!/usr/bin/env python
# -*- coding: utf-8 -*-

from xml.dom import minidom

class Xml_ini:
	
	def __init__(self,xmlIni = "otool.ini"):
		
		try:
			xmlDoc = minidom.parse(xmlIni)
			self.new = False
		except:
			# New document 
			xmlDoc = minidom.Document()
			self.new = True
			
			# Creates init element and append to xml document
			initElem = xmlDoc.createElement("init")
			xmlDoc.appendChild(initElem)
			
			# Creates cvs element and append to initElem
			cvsElem = xmlDoc.createElement("cvs")
			initElem.appendChild(cvsElem)
			
			#Create cvsAdressXml and append to cvsElem
			cvsPathsXmlElem = xmlDoc.createElement("cvsPathsXml")
			cvsElem.appendChild(cvsPathsXmlElem)
			
			#create 5 adress and append to cvsAdressXml
			i=0
			while i < 5:
				i= i+1
				cvsPathXmlElem = xmlDoc.createElement("cvsPathXml")
				cvsPathsXmlElem.appendChild(cvsPathXmlElem)
				path = xmlDoc.createTextNode("NONE")
				cvsPathXmlElem.appendChild(path)
			# Set attributes to user element
			#userElem.setAttribute("name", "Sergio Oliveira")			
			
			#print xmlDoc.toxml("UTF-8")
			try:
				fp = open("otool.ini","w")
			except:
				print "nepodarilo se ulozit ini file"
			# writexml(self, writer, indent='', addindent='', newl='', encoding=None)
			xmlDoc.writexml(fp, "    ", "", "\n", "UTF-8")
		self.read_init(xmlDoc)
		return
		
	def read_init(self,xmlDoc):
		""" read information from xml init"""
		cvsPathsXml = xmlDoc.getElementsByTagName("cvsPathXml")
		for path in cvsPathsXml:
			self.getTextNone(path.childNodes)
		return
	
	def getTextNone(self,nodelist):
		"""value from node list to list, value NONE no add """
		node_values =[]
		for node in nodelist:
			if node.nodeType == node.TEXT_NODE:
				node_values.append (node.data)
				print node.data
		return node_values


if __name__ == "__main__":
	pokus = Xml_ini()
	print pokus.new
	pokus