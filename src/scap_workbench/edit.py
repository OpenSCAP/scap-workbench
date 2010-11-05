# -*- coding: utf-8 -*-
#
# Copyright 2010 Red Hat Inc., Durham, North Carolina.
# All Rights Reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
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
from threads import thread as threadSave

logger = logging.getLogger("OSCAPEditor")

class ItemList(abstract.List):

    def __init__(self, widget, core, progress=None, filter=None):
        self.core = core
        self.filter = filter
        self.data_model = commands.DHItemsTree("gui:edit:DHItemsTree", core, progress, True)
        abstract.List.__init__(self, "gui:edit:item_list", core, widget)
        self.get_TreeView().set_enable_tree_lines(True)

        selection = self.get_TreeView().get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)

        # actions
        self.add_receiver("gui:btn:menu:edit", "update", self.__update)
        #self.add_receiver("gui:btn:edit", "update", self.__update)
        self.add_receiver("gui:btn:edit:filter", "search", self.__search)
        self.add_receiver("gui:btn:edit:filter", "filter_add", self.__filter_add)
        self.add_receiver("gui:btn:edit:filter", "filter_del", self.__filter_del)
        self.add_receiver("gui:edit:DHItemsTree", "filled", self.__filter_refresh)

        selection.connect("changed", self.__cb_item_changed, self.get_TreeView())
        self.add_sender(self.id, "item_changed")

        self.init_filters(self.filter, self.data_model.model, self.data_model.new_model())

    def __update(self):
        self.get_TreeView().set_model(self.data_model.model)
        self.data_model.fill()
        # Select the last one selected if there is one
        self.get_TreeView().get_model().foreach(self.set_selected, (self.core.selected_item_edit, self.get_TreeView()))
        self.core.force_reload_items = False

    def __search(self):
        self.search(self.filter.get_search_text(),1)
        
    def __filter_add(self):
        self.data_model.map_filter = self.filter_add(self.filter.filters)
        self.get_TreeView().get_model().foreach(self.set_selected, (self.core.selected_item, self.get_TreeView()))

    def __filter_del(self):
        self.data_model.map_filter = self.filter_del(self.filter.filters)
        self.get_TreeView().get_model().foreach(self.set_selected, (self.core.selected_item, self.get_TreeView()))

    def __filter_refresh(self):
        self.data_model.map_filter = self.filter_del(self.filter.filters)
        self.get_TreeView().get_model().foreach(self.set_selected, (self.core.selected_item, self.get_TreeView()))


    @threadSave
    def __cb_item_changed(self, widget, treeView):
        """Make all changes in application in separate threads: workaround for annoying
        blinking when redrawing treeView
        """
        gtk.gdk.threads_enter()
        selection = treeView.get_selection( )
        if selection != None: 
            (model, iter) = selection.get_selected( )
            if iter: 
                self.core.selected_item_edit = model.get_value(iter, 0)
                self.emit("update")
        treeView.columns_autosize()
        gtk.gdk.threads_leave()

class MenuButtonEdit(abstract.MenuButton):
    """
    GUI for refines.
    """
    def __init__(self, builder, widget, core):
        abstract.MenuButton.__init__(self, "gui:btn:menu:edit", widget, core)
        self.builder = builder
        self.core = core
        self.data_model = commands.DataHandler(self.core)
        
        #draw body
        self.body = self.builder.get_object("edit:box")
        self.progress = self.builder.get_object("edit:progress")
        self.progress.hide()
        self.filter = filter.ItemFilter(self.core, self.builder,"edit:box_filter", "gui:btn:edit:filter")
        self.rules_list = ItemList(self.builder.get_object("edit:tw_items"), self.core, self.progress, self.filter)
        self.filter.expander.cb_changed()

        # set signals
        self.add_sender(self.id, "update")
        
        """Get widget for details
        """
        #main
        self.btn_revert = self.builder.get_object("edit:btn_revert")
        self.btn_save = self.builder.get_object("edit:btn_save")
        self.btn_item_remove = self.builder.get_object("edit:item:btn_remove")
        self.btn_item_add = self.builder.get_object("edit:item:btn_add")
        
        self.btn_revert.connect("clicked", self.__cb_revert)
        self.btn_save.connect("clicked", self.__cb_save)
        self.btn_item_remove.connect("clicked", self.__cb_item_remove)
        self.btn_item_add.connect("clicked", self.__cb_item_add)
        
        #general
        self.item_id = self.builder.get_object("edit:general:lbl_id")
        self.lv_version = self.builder.get_object("edit:general:lv_version")
        self.chbox_hidden = self.builder.get_object("edit:general:chbox_hidden")
        self.chbox_prohibit = self.builder.get_object("edit:general:chbox_prohibit")
        self.chbox_abstract = self.builder.get_object("edit:general:chbox_abstract")
        self.entry_cluster_id = self.builder.get_object("edit:general:entry_cluster_id")
        
        #status
        self.lv_status = self.builder.get_object("edit:general:lv_status")
        self.status_model = commands.DHEditStatus(self.core, self.lv_status)
        
        #question
        self.lv_question = self.builder.get_object("edit:general:lv_question")
        self.guestion_model = commands.DHEditQuestion(self.core, self.lv_question)
        
        #references
        self.lv_reference = self.builder.get_object("edit:general:lv_reference")
        self.ref_model = commands.DHEditReferences(self.core, self.lv_reference)
        
        #rationale
        self.lv_rationale = self.builder.get_object("edit:general:lv_rationale")
        self.rationale_model = commands.DHEditRationale(self.core, self.lv_rationale)
        
        #title
        self.lv_title = self.builder.get_object("edit:general:lv_title")
        self.title_model = commands.DHEditTitle(self.core, self.lv_title)
        
        #description
        self.lv_description = self.builder.get_object("edit:general:lv_description")
        self.sw_description = self.builder.get_object("edit:general:sw_description")
        self.description_model = commands.DHEditDescription(self.core, self.lv_description, self.sw_description)
        
        #warning
        self.lv_warning = self.builder.get_object("edit:general:lv_warning")
        self.sw_warning = self.builder.get_object("edit:general:sw_warning")
        self.warning_model = commands.DHEditWarning(self.core, self.lv_warning, self.sw_warning)
        
        #extends
        self.lbl_extends = self.builder.get_object("edit:dependencies:lbl_extends")
        
        #Conflicts
        self.lv_conflicts = self.builder.get_object("edit:dependencies:lv_conflicts")
        self.conflict_model = commands.DHEditConflicts(self.core, self.lv_conflicts)
        
        self.lv_reguires = self.builder.get_object("edit:dependencies:lv_reguires")
        self.lv_platform = self.builder.get_object("edit:dependencies:lv_platform")
        self.lv_ident = self.builder.get_object("edit:dependencies:lv_ident")
        
        #operations
        #self.chbox_selected = self.builder.get_object("edit:operations:chbox_selected")
        self.combo_severity = self.builder.get_object("edit:operations:combo_severity")
        self.entry_impact_metric = self.builder.get_object("edit:operations:entry_impact_metric")
        self.lv_fixtext = self.builder.get_object("edit:operations:lv_fixtext")
        self.lv_fix = self.builder.get_object("edit:operations:lv_fix")
        self.lv_fix = self.builder.get_object("edit:operations:lv_check")
        
        #others
        self.chbox_multipl = self.builder.get_object("edit:other:chbox_multipl")
        self.combo_role = self.builder.get_object("edit:other:combo_role")
        self.lv_profile_note = self.builder.get_object("edit:other:lv_profile_note")
        
        #values
        self.tv_values = self.builder.get_object("edit:values:tv_values")
        self.btn_value_edit = self.builder.get_object("edit:values:btn_edit")
        self.btn_value_add = self.builder.get_object("edit:values:btn_add")
        self.btn_value_remove = self.builder.get_object("edit:values:btn_remove")
        
        self.btn_value_edit.connect("clicked", self.__cd_value_edit)
        self.btn_value_add.connect("clicked", self.__cd_value_add)
        self.btn_value_remove.connect("clicked", self.__cd_value_remove)

        self.add_receiver("gui:edit:item_list", "update", self.__update)
        self.add_receiver("gui:edit:item_list", "changed", self.__update)
        
            
    def __cb_revert(self, widget):
        pass

    def __cb_save(self, widget):
        pass

    def __cb_item_remove(self, widget):
        pass

    def __cb_item_add(self, widget):
        pass

    def __cd_value_edit(self, widget):
        pass

    def __cd_value_add(self, widget):
        pass

    def __cd_value_remove(self, widget):
        pass

    def __update(self):

        details = self.data_model.get_item_details(self.core.selected_item_edit)
        if details != None:
            self.item_id.set_text(details["id"])
            self.chbox_hidden.set_active(details["hidden"])
            self.chbox_prohibit.set_active(details["prohibit_changes"])
            self.chbox_abstract.set_active(details["abstract"])
            self.description_model.fill(details["descriptions"])
            self.ref_model.fill(details["references"])
            self.guestion_model.fill(details["questions"])
            self.status_model.fill(details["statuses"])
            self.conflict_model.fill(details["conflicts"])
            self.rationale_model.fill(details["rationale"])
            self.title_model.fill(details["titles"])
            self.warning_model.fill(details["warnings"])
            
            if details["cluster_id"] != None:
                self.entry_cluster_id.set_text(details["cluster_id"])
            else:
                self.entry_cluster_id.set_text("")

            if details["extends"] != None:
                self.lbl_extends.set_text(details["extends"])
            else:
                self.lbl_extends.set_text("")

            
            # dat only for rule
            if details["typetext"] == "Rule":
                self.entry_impact_metric.set_sensitive(True)
                if details["imapct_metric"] != None:
                    self.entry_impact_metric.set_text(details["imapct_metric"])
                else:
                    self.entry_impact_metric.set_text("")

                self.chbox_multipl.set_sensitive(True)
                self.chbox_multipl.set_active(details["multiple"])
                
                # clean data only group and set insensitive
            #data only for Group
            else:
                
                
                
                # clean data only for rule and set insensitive
                self.entry_impact_metric.set_sensitive(False)
                self.chbox_multipl.set_sensitive(False)
                self.entry_impact_metric.set_text("")
        else:
            return