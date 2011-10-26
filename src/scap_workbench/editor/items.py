# -*- coding: utf-8 -*-
#
# Copyright 2011 Red Hat Inc., Durham, North Carolina.
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
#      Maros Barabas        <xbarry@gmail.com>
#      Vladimir Oberreiter  <xoberr01@stud.fit.vutbr.cz>
#      Martin Preisler      <mpreisle@redhat.com>

from scap_workbench import core
from scap_workbench.core import paths
from scap_workbench.core import abstract
from scap_workbench.core.events import EventObject
from scap_workbench.editor.edit import *

import gtk
import glib

import logging

# Initializing Logger
logger = logging.getLogger("scap-workbench")


class AddItem(EventObject):
    
    COMBO_COLUMN_DATA = 0
    COMBO_COLUMN_VIEW = 1
    COMBO_COLUMN_INFO = 2
    
    def __init__(self, core, data_model, list_item):
        super(AddItem, self).__init__(core)
        
        self.data_model = data_model
        self.list_item = list_item
        self.view = list_item.get_TreeView()
        
    def dialog(self):

        builder = gtk.Builder()
        builder.add_from_file(os.path.join(paths.glade_dialog_prefix, "add_item.glade"))
        
        self.window = builder.get_object("dialog:add_item")
        self.window.connect("delete-event", self.__delete_event)
        
        btn_ok = builder.get_object("dialog:add_item:btn_ok")
        btn_ok.connect("clicked", self.__cb_do)
        btn_cancel = builder.get_object("dialog:add_item:btn_cancel")
        btn_cancel.connect("clicked", self.__delete_event)

        self.itype = builder.get_object("dialog:add_item:type")
        self.itype.connect("changed", self.__cb_changed_type)
        self.vtype_lbl = builder.get_object("dialog:add_item:value_type:lbl")
        self.vtype = builder.get_object("dialog:add_item:value_type")
        self.iid = builder.get_object("dialog:add_item:id")
        self.lang = builder.get_object("dialog:add_item:lang")
        self.lang.set_text(self.core.selected_lang)
        self.lang.set_sensitive(False)
        self.title = builder.get_object("dialog:add_item:title")
        self.relation = builder.get_object("dialog:add_item:relation")
        self.relation.connect("changed", self.__cb_changed_relation)
        self.info_box = builder.get_object("dialog:add_item:info_box")

        self.__entry_style = self.iid.get_style().base[gtk.STATE_NORMAL]

        self.window.set_transient_for(self.core.main_window)
        self.window.show()

    def __cb_changed_relation(self, widget):

        self.core.notify_destroy("notify:relation")
        (model, iter) = self.view.get_selection().get_selected()
        if not iter:
            if widget.get_active() in [self.data_model.RELATION_PARENT, self.data_model.RELATION_SIBLING]:
                self.core.notify("Item can't be a parent or sibling of benchmark !",
                        core.Notification.ERROR, self.info_box, msg_id="notify:relation")
                widget.grab_focus()
                return False
        else:
            self.core.notify_destroy("dialog:add_item")
            if model[iter][self.data_model.COLUMN_TYPE] in ["value", "rule"] and widget.get_active() == self.data_model.RELATION_CHILD:
                self.core.notify("Item types VALUE and RULE can't be a parent !",
                        core.Notification.ERROR, self.info_box, msg_id="notify:relation")
                widget.grab_focus()
                return False

        return True

    def __cb_changed_type(self, widget):

        self.core.notify_destroy("dialog:add_item")
        self.vtype_lbl.set_property("visible", widget.get_active() == self.data_model.TYPE_VALUE)
        self.vtype.set_property('visible', widget.get_active() == self.data_model.TYPE_VALUE)

    def __cb_do(self, widget):

        self.core.notify_destroy("dialog:add_item")
        tagOK = True
        itype = self.itype.get_active()
        vtype = self.vtype.get_active()
        relation = self.relation.get_active()
        if not self.__cb_changed_relation(self.relation):
            return

        if itype == -1:
            self.core.notify("Relation has to be chosen",
                    core.Notification.ERROR, self.info_box, msg_id="dialog:add_item")
            self.itype.grab_focus()
            return

        if itype == self.data_model.TYPE_VALUE:
            if vtype == -1:
                self.core.notify("Type of value has to be choosen",
                        core.Notification.ERROR, self.info_box, msg_id="dialog:add_item")
                self.vtype.grab_focus()
                return

        if relation == -1:
            self.core.notify("Relation has to be chosen",
                    core.Notification.ERROR, self.info_box, msg_id="dialog:add_item")
            self.relation.grab_focus()
            return

        if self.iid.get_text() == "":
            self.core.notify("The ID of item is mandatory !",
                    core.Notification.ERROR, self.info_box, msg_id="dialog:add_item")
            self.iid.grab_focus()
            self.iid.modify_base(gtk.STATE_NORMAL, gtk.gdk.Color("#FFC1C2"))
            return
        elif self.data_model.get_item_details(self.iid.get_text()):
            self.core.notify("ID already exists",
                    core.Notification.ERROR, self.info_box, msg_id="dialog:add_item")
            self.iid.grab_focus()
            self.iid.modify_base(gtk.STATE_NORMAL, gtk.gdk.Color("#FFC1C2"))
            return
        else: 
            self.iid.modify_base(gtk.STATE_NORMAL, self.__entry_style)

        if self.title.get_text() == "":
            self.core.notify("The title of item is mandatory !",
                    core.Notification.ERROR, self.info_box, msg_id="dialog:add_item")
            self.title.grab_focus()
            self.title.modify_base(gtk.STATE_NORMAL, gtk.gdk.Color("#FFC1C2"))
            return
        else: 
            self.title.modify_base(gtk.STATE_NORMAL, self.__entry_style)

        if relation == self.data_model.RELATION_PARENT:
            self.core.notify("Relation PARENT is not implemented yet",
                    core.Notification.ERROR, self.info_box, msg_id="dialog:add_item")
            self.relation.grab_focus()
            return

        item = {"id": self.iid.get_text(),
                "lang": self.lang.get_text(),
                "title": self.title.get_text()}
        retval = self.data_model.add_item(item, itype, relation, vtype)
        if retval: self.list_item.emit("update") # TODO: HACK
        self.window.destroy()

    def __delete_event(self, widget, event=None):
        self.core.notify_destroy("dialog:add_item")
        self.window.destroy()

class ItemList(abstract.List):

    """ List of Rules, Groups and Values.

    This class represents TreeView in editor window which contains
    list of XCCDF Items as Rules, Groups and Values. Each Group contains
    its content.
    """

    def __init__(self, widget, core, builder=None, progress=None):
        """ Constructor of ProfileList.
        """
        self.data_model = commands.DHItemsTree("gui:edit:DHItemsTree", core, progress, None, True, no_checks=True)
        super(ItemList, self).__init__("gui:edit:item_list", core, widget)
        
        self.loaded = False
        self.filter = filter
        self.builder = builder

        """ Register signals that can be emited by this class.
        All signals are registered in EventObject (abstract class) and
        are emited by other objects to trigger the async event.
        """
        self.add_sender(self.id, "update")
        self.add_sender(self.id, "delete")
        self.add_receiver("gui:btn:menu:edit:items", "update", self.__update)
        self.add_receiver("gui:btn:menu:edit:XCCDF", "load", self.__clear_update)


        """ Set objects from Glade files and connect signals
        """
        selection = self.get_TreeView().get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)
        selection.connect("changed", self.__cb_item_changed, self.get_TreeView())
        self.section_list = self.builder.get_object("edit:section_list")
        self.itemsList = self.builder.get_object("edit:tw_items:sw")
        self.with_values = self.builder.get_object("xccdf:items:popup:show_values")
        self.with_values.connect("toggled", self.__update)
        # Popup Menu
        self.builder.get_object("xccdf:items:popup:add").connect("activate", self.__cb_item_add)
        self.builder.get_object("xccdf:items:popup:remove").connect("activate", self.__cb_item_remove)
        widget.connect("button_press_event", self.__cb_button_pressed, self.builder.get_object("xccdf:items:popup"))

        self.add_dialog = AddItem(self.core, self.data_model, self) # TODO
        self.get_TreeView().connect("key-press-event", self.__cb_key_press)
        
        # if True an idle worker that will perform the update (after selection changes) is already pending
        self.item_changed_worker_pending = False

    def __clear_update(self):
        """ Remove all items from the list and update model
        """
        self.data_model.model.clear()
        self.__update(force=True)

    def __update(self, force=False):
        """ Update items in the list. Parameter 'force' is used to force
        the fill function upon the list."""
        if not self.loaded or force:
            self.data_model.fill(with_values=self.with_values.get_active())
            self.loaded = True

        # Select the last one selected if there is one
        self.get_TreeView().get_model().foreach(self.set_selected, (self.core.selected_item, self.get_TreeView(), 1))

    def __cb_button_pressed(self, treeview, event, menu):
        """ Mouse button has been pressed. If the button is 3rd: show
        popup menu"""
        if event.button == 3:
            time = event.time
            menu.popup(None, None, None, event.button, event.time)

    def __cb_key_press(self, widget, event):
        """ The key-press event has occured upon the list.
        If key == delete: Delete the selected item from the list and model"""
        if event and event.type == gtk.gdk.KEY_PRESS and event.keyval == gtk.keysyms.Delete:
            selection = self.get_TreeView().get_selection()
            (model,iter) = selection.get_selected()
            if iter: self.__cb_item_remove()

    def __cb_item_remove(self, widget=None):
        """ Remove selected item from the list and model.
        """
        selection = self.get_TreeView().get_selection()
        (model, iter) = selection.get_selected()
        if iter:
            iter_next = model.iter_next(iter)
            self.data_model.remove_item(model[iter][1])
            model.remove(iter)

            """ If the removed item has successor, let's select it so we can
            continue in deleting or other actions without need to click the
            list again to select next item """
            if iter_next:
                self.core.selected_item = model[iter_next][1]
                self.__update(False)
            self.emit("delete") 
        else: raise AttributeError, "Removing non-selected item or nothing selected."

    def __cb_item_add(self, widget=None):
        """ Add item to the list and model
        """
        self.add_dialog.dialog()

    def __cb_item_changed(self, widget, treeView):
        """Callback called whenever item selection changes. Performs updates of the property box.
        """
        
        def worker():
            details = self.data_model.get_item_details(self.core.selected_item)
            selection = treeView.get_selection( )
            if selection != None: 
                (model, iter) = selection.get_selected( )
                if iter: self.core.selected_item = model.get_value(iter, commands.DHItemsTree.COLUMN_ID)
                else: self.core.selected_item = None
    
            # Selection has changed, trigger all events connected to this signal
            self.emit("update")
            treeView.columns_autosize()
            
            self.item_changed_worker_pending = False
        
        # The reason for the item_changed_worker_pending attribute is to avoid stacking up
        # many update requests that would all query the selection state again and do repeated
        # work. This way the update happens only once even though the selection changes many times.
        if not self.item_changed_worker_pending:
            # we handle this in the idle function when no higher priority events are to be handled
            glib.idle_add(worker)
            self.item_changed_worker_pending = True
            
            
class MenuButtonEditItems(abstract.MenuButton, abstract.Func):

    def __init__(self, builder, widget, core):
        abstract.MenuButton.__init__(self, "gui:btn:menu:edit:items", widget, core)
        abstract.Func.__init__(self, core)
        
        self.builder = builder
        self.data_model = commands.DHEditItems(self.core)
        self.item = None
        # FIXME: Instantiating abstract class
        # FIXME: We inherit Func and we are composed of it
        self.func = abstract.Func()
        self.current_page = 0

        #draw body
        self.body = self.builder.get_object("items:box")
        self.progress = self.builder.get_object("edit:progress")
        self.progress.hide()
        #self.filter = filter.ItemFilter(self.core, self.builder,"edit:box_filter", "gui:btn:edit:filter")
        #self.filter.set_active(False)
        self.filter = None
        self.tw_items = self.builder.get_object("edit:tw_items")
        titles = self.data_model.get_benchmark_titles()
        self.list_item = ItemList(self.tw_items, self.core, builder, self.progress)
        self.ref_model = self.list_item.get_TreeView().get_model() # original model (not filtered)
        
        # set signals
        self.add_sender(self.id, "update")
        
        # remove just for now (missing implementations and so..)
        self.items = self.builder.get_object("edit:xccdf:items")
        self.items.remove_page(4)

        # Get widgets from GLADE
        self.item_id = self.builder.get_object("edit:general:entry_id")
        self.item_id.connect("focus-out-event", self.__change)
        self.item_id.connect("key-press-event", self.__change)
        self.version = self.builder.get_object("edit:general:entry_version")
        self.version.connect("focus-out-event", self.__change)
        self.version.connect("key-press-event", self.__change)
        self.version_time = self.builder.get_object("edit:general:entry_version_time")
        self.version_time.connect("focus-out-event", self.__change)
        self.version_time.connect("key-press-event", self.__change)
        self.selected = self.builder.get_object("edit:general:chbox_selected")
        self.selected.connect("toggled", self.__change)
        self.hidden = self.builder.get_object("edit:general:chbox_hidden")
        self.hidden.connect("toggled", self.__change)
        self.prohibit = self.builder.get_object("edit:general:chbox_prohibit")
        self.prohibit.connect("toggled", self.__change)
        self.abstract = self.builder.get_object("edit:general:chbox_abstract")
        self.abstract.connect("toggled", self.__change)
        self.cluster_id = self.builder.get_object("edit:general:entry_cluster_id")
        self.cluster_id.connect("focus-out-event", self.__change)
        self.cluster_id.connect("key-press-event", self.__change)
        self.weight = self.builder.get_object("edit:general:entry_weight")
        self.weight.connect("focus-out-event", self.__change)
        self.weight.connect("key-press-event", self.__change)
        self.operations = self.builder.get_object("edit:xccdf:items:operations")
        self.extends = self.builder.get_object("edit:dependencies:lbl_extends")
        self.content_ref = self.builder.get_object("edit:xccdf:items:evaluation:content_ref")
        self.content_ref.connect("focus-out-event", self.__change)
        self.content_ref.connect("key-press-event", self.__change)
        self.content_ref_find = self.builder.get_object("edit:xccdf:items:evaluation:content_ref:find")
        self.href = self.builder.get_object("edit:xccdf:items:evaluation:href")
        self.href.connect("changed", self.__change)
        self.href_dialog = self.builder.get_object("edit:xccdf:items:evaluation:href:dialog")
        self.href_dialog.connect("file-set", self.__cb_href_file_set)
        self.item_values_main = self.builder.get_object("edit:values:sw_main")
        self.ident_box = self.builder.get_object("xccdf:items:ident:box")
        
        # -- TITLES --
        self.titles = EditTitle(self.core, "gui:edit:xccdf:items:titles", builder.get_object("edit:general:lv_title"), self.data_model)
        builder.get_object("edit:general:btn_title_add").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:general:btn_title_edit").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:general:btn_title_del").connect("clicked", self.titles.dialog, self.data_model.CMD_OPER_DEL)

        # -- DESCRIPTIONS --
        self.descriptions = EditDescription(self.core, "gui:edit:xccdf:items:descriptions", builder.get_object("edit:general:lv_description"), self.data_model)
        builder.get_object("edit:general:btn_description_add").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:general:btn_description_edit").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:general:btn_description_del").connect("clicked", self.descriptions.dialog, self.data_model.CMD_OPER_DEL)
        builder.get_object("edit:general:btn_description_preview").connect("clicked", self.descriptions.preview)

        # -- WARNINGS --
        self.warnings = EditWarning(self.core, "gui:edit:items:general:warning", builder.get_object("edit:general:lv_warning"), self.data_model)
        builder.get_object("edit:general:btn_warning_add").connect("clicked", self.warnings.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:general:btn_warning_edit").connect("clicked", self.warnings.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:general:btn_warning_del").connect("clicked", self.warnings.dialog, self.data_model.CMD_OPER_DEL)

        # -- STATUSES --
        self.statuses = EditStatus(self.core, "gui:edit:items:general:status", builder.get_object("edit:general:lv_status"), self.data_model)
        builder.get_object("edit:general:btn_status_add").connect("clicked", self.statuses.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:general:btn_status_edit").connect("clicked", self.statuses.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:general:btn_status_del").connect("clicked", self.statuses.dialog, self.data_model.CMD_OPER_DEL)

        # -- QUESTIONS --
        self.questions = EditQuestion(self.core, "gui:edit:items:general:questions", builder.get_object("edit:items:questions"), self.data_model)
        builder.get_object("edit:items:questions:btn_add").connect("clicked", self.questions.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:items:questions:btn_edit").connect("clicked", self.questions.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:items:questions:btn_del").connect("clicked", self.questions.dialog, self.data_model.CMD_OPER_DEL)

        # -- RATIONALES --
        self.rationales = EditRationale(self.core, "gui:edit:items:general:rationales", builder.get_object("edit:items:rationales"), self.data_model)
        builder.get_object("edit:items:rationales:btn_add").connect("clicked", self.rationales.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:items:rationales:btn_edit").connect("clicked", self.rationales.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:items:rationales:btn_del").connect("clicked", self.rationales.dialog, self.data_model.CMD_OPER_DEL)

        # -- VALUES --
        self.item_values = EditItemValues(self.core, "gui:edit:items:values", builder.get_object("edit:xccdf:items:values"), self.data_model)
        builder.get_object("edit:xccdf:items:values:btn_add").connect("clicked", self.item_values.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:xccdf:items:values:btn_edit").connect("clicked", self.item_values.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:xccdf:items:values:btn_del").connect("clicked", self.item_values.dialog, self.data_model.CMD_OPER_DEL)
        builder.get_object("edit:xccdf:items:values").connect("button-press-event", self.__cb_value_clicked) # Double-click makes the editor to look for the value in items

        # -- PLATFORMS --
        self.platforms = EditPlatform(self.core, "gui:edit:dependencies:platforms", builder.get_object("edit:xccdf:dependencies:platforms"), self.data_model)
        builder.get_object("edit:xccdf:dependencies:platforms:btn_add").connect("clicked", self.platforms.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("edit:xccdf:dependencies:platforms:btn_edit").connect("clicked", self.platforms.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("edit:xccdf:dependencies:platforms:btn_del").connect("clicked", self.platforms.dialog, self.data_model.CMD_OPER_DEL)

        # -- CONTENT REF --
        self.content_ref_dialog = FindOvalDef(self.core, "gui:edit:evaluation:content_ref:dialog", self.data_model)
        self.content_ref_find.connect("clicked", self.__cb_find_oval_definition)

        # -- FIXTEXTS --
        self.fixtext = EditFixtext(self.core, "id:edit:xccdf:items:fixtext", builder.get_object("xccdf:items:fixtext"), self.data_model, builder)
        builder.get_object("xccdf:items:fixtext:btn_add").connect("clicked", self.fixtext.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("xccdf:items:fixtext:btn_edit").connect("clicked", self.fixtext.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("xccdf:items:fixtext:btn_del").connect("clicked", self.fixtext.dialog, self.data_model.CMD_OPER_DEL)
        builder.get_object("xccdf:items:fixtext:btn_preview").connect("clicked", self.fixtext.preview)

        # -- FIXES --
        self.fix = EditFix(self.core, "id:edit:xccdf:items:fix", builder.get_object("xccdf:items:fix"), self.data_model, builder)
        builder.get_object("xccdf:items:fix:btn_add").connect("clicked", self.fix.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("xccdf:items:fix:btn_edit").connect("clicked", self.fix.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("xccdf:items:fix:btn_del").connect("clicked", self.fix.dialog, self.data_model.CMD_OPER_DEL)

        # -- IDENTS --
        self.ident = EditIdent(self.core, "id:edit:xccdf:items:ident", builder.get_object("xccdf:items:ident"), self.data_model)
        builder.get_object("xccdf:items:ident:btn_add").connect("clicked", self.ident.dialog, self.data_model.CMD_OPER_ADD)
        builder.get_object("xccdf:items:ident:btn_edit").connect("clicked", self.ident.dialog, self.data_model.CMD_OPER_EDIT)
        builder.get_object("xccdf:items:ident:btn_del").connect("clicked", self.ident.dialog, self.data_model.CMD_OPER_DEL)
        # -------------

        """Get widgets from Glade: Part editor.glade in edit
        """
        self.conflicts = EditConflicts(self.core, self.builder,self.list_item.get_TreeView().get_model())
        self.requires = EditRequires(self.core, self.builder,self.list_item.get_TreeView().get_model())
        self.values = EditValues(self.core, "gui:edit:xccdf:values", self.builder)
        
        self.severity = self.builder.get_object("edit:operations:combo_severity")
        self.severity.set_model(ENUM.LEVEL.get_model())
        self.severity.connect( "changed", self.__change)
        self.impact_metric = self.builder.get_object("edit:operations:entry_impact_metric")
        self.impact_metric.connect("focus-out-event", self.cb_control_impact_metric)
        self.check = self.builder.get_object("edit:operations:lv_check")

        self.add_receiver("gui:edit:item_list", "update", self.__update)
        self.add_receiver("gui:edit:evaluation:content_ref:dialog", "update", self.__update)
        self.add_receiver("gui:edit:xccdf:values:titles", "update", self.__update_item)
        self.add_receiver("gui:edit:xccdf:items:titles", "update", self.__update_item)
        self.add_receiver("gui:edit:xccdf:values", "update_item", self.__update_item)

    def __cb_find_oval_definition(self, widget):

        model = self.href.get_model()
        if self.href.get_active() == -1:
            self.notifications.append(self.core.notify("No definition file available", core.Notification.WARNING, msg_id="notify:definition_available"))
            return
        self.content_ref_dialog.dialog(None, model[self.href.get_active()][0])

    def __change(self, widget, event=None):

        if event and event.type == gtk.gdk.KEY_PRESS and event.keyval != gtk.keysyms.Return:
            return

        if widget == self.item_id:
            self.core.notify_destroy("notify:xccdf:id")
            text = widget.get_text()
            if len(text) != 0 and re.search("[A-Za-z_]", text[0]) == None:
                self.notifications.append(self.core.notify("First character of ID has to be from A-Z (case insensitive) or \"_\"",
                    core.Notification.ERROR, msg_id="notify:xccdf:id"))
                return
            else: retval = self.data_model.update(id=text)
            if not retval:
                self.notifications.append(self.core.notify("Setting ID failed: ID \"%s\" already exists." % (widget.get_text(),),
                    core.Notification.ERROR, msg_id="notify:not_selected"))
                widget.set_text(self.core.selected_item)
                return
            self.__update_item()
        elif widget == self.version:
            self.data_model.update(version=widget.get_text())
        elif widget == self.version_time:
            timestamp = self.controlDate(widget.get_text())
            if timestamp > 0:
                self.data_model.update(version_time=timestamp)
        elif widget == self.selected:
            self.data_model.update(selected=widget.get_active())
        elif widget == self.hidden:
            self.data_model.update(hidden=widget.get_active())
        elif widget == self.prohibit:
            self.data_model.update(prohibit=widget.get_active())
        elif widget == self.abstract:
            self.data_model.update(abstract=widget.get_active())
        elif widget == self.cluster_id:
            self.data_model.update(cluster_id=widget.get_text())
        elif widget == self.weight:
            weight = self.controlFloat(widget.get_text(), "Weight")
            if weight:
                self.data_model.update(weight=weight)
        elif widget == self.content_ref:
            ret, err = self.data_model.set_item_content(name=widget.get_text())
            if not ret:
                self.notifications.append(self.core.notify(err, core.Notification.ERROR, msg_id="notify:edit:content_href"))
        elif widget == self.href:
            if self.href.get_active() == -1 or len(self.href.get_model()) == 0:
                return
            iter = self.href.get_model()[self.href.get_active()]
            if iter:
                href = iter[1]
                self.data_model.set_item_content(href=href)
                self.core.notify_destroy("notify:definition_available")
        elif widget == self.severity:
            self.data_model.update(severity=ENUM.LEVEL.value(widget.get_active()))
        else: 
            logger.error("Change of \"%s\" is not supported " % (widget,))
            return

    def __cb_href_file_set(self, widget):
        path = widget.get_filename()
        file = os.path.basename(widget.get_filename())

        self.data_model.add_oval_reference(path)
        retval, err = self.data_model.set_item_content(href=file)
        if not retval: self.notifications.append(self.core.notify(err, core.Notification.ERROR, msg_id="notify:set_content_ref"))
        self.__update()

    def __cb_value_clicked(self, widget, event):

        if event.type == gtk.gdk._2BUTTON_PRESS and event.button == 1:
            selection = widget.get_selection()
            if selection:
                (model, iter) = selection.get_selected()
                if not iter: return
                id = model[iter][0]# Should be ID of value
                if not id: return
            else: return
            self.list_item.search(id, 1)

    def __section_list_load(self):
        self.section_list.get_model().clear()
        titles = self.data_model.get_benchmark_titles()
        if len(titles.keys()) != 0:
            if self.core.selected_lang in titles: 
                title = self.data_model.get_benchmark_titles()[self.core.selected_lang]
            else: 
                self.data_model.get_benchmark_titles()[0]
            self.section_list.get_model().append(["XCCDF", "XCCDF: "+title])
            self.section_list.get_model().append(["PROFILES", "XCCDF: "+title+" (Profiles)"])
            self.section_list.set_active(0)

    def cb_control_impact_metric(self, widget, event):
        text = widget.get_text()
        if text != "" and self.controlImpactMetric(text, self.core):
            self.data_model.DHEditImpactMetric(self.item, text)

    def show(self, sensitive):
        self.items.set_sensitive(sensitive)
        self.items.set_property("visible", sensitive)

    def __set_profile_description(self, description):
        """
        Set description to the textView.
        @param text Text with description
        """
        self.profile_description.get_buffer().set_text("")
        if description == "": description = "No description"
        description = "<body>"+description+"</body>"
        self.profile_description.display_html(description)

    def __update_item(self):
        selection = self.tw_items.get_selection()
        (model, iter) = selection.get_selected()
        if iter:
            item = self.data_model.get_item(model[iter][1])
            if item == None:
                item = self.data_model.get_item(self.core.selected_item)
            if item == None:
                logger.error("Can't find item with ID: \"%s\"" % (model[iter][1],))
                return
            model[iter][1] = item.id

            # Get the title of item
            title = self.data_model.get_title(item.title) or "%s (ID)" % (item.id,)

            model[iter][2] = title
            model[iter][4] = ""+title

    def __block_signals(self):
        self.hidden.handler_block_by_func(self.__change)
        self.selected.handler_block_by_func(self.__change)
        self.prohibit.handler_block_by_func(self.__change)
        self.abstract.handler_block_by_func(self.__change)
        self.severity.handler_block_by_func(self.__change)
        self.content_ref.handler_block_by_func(self.__change)
        self.href.handler_block_by_func(self.__change)
        #self.multiple.handler_block_by_func(self.__change)
        #self.role.handler_block_by_func(self.__change)

    def __unblock_signals(self):
        self.hidden.handler_unblock_by_func(self.__change)
        self.selected.handler_unblock_by_func(self.__change)
        self.prohibit.handler_unblock_by_func(self.__change)
        self.abstract.handler_unblock_by_func(self.__change)
        self.severity.handler_unblock_by_func(self.__change)
        self.content_ref.handler_unblock_by_func(self.__change)
        self.href.handler_unblock_by_func(self.__change)
        #self.chbox_multiple.handler_unblock_by_func(self.__change)
        #self.cBox_role.handler_unblock_by_func(self.__change)

    def __clear(self):
        self.__block_signals()
        self.item_id.set_text("")
        self.hidden.set_active(False)
        self.selected.set_active(False)
        self.prohibit.set_active(False)
        self.abstract.set_active(False)
        self.version.set_text("")
        self.version_time.set_text("")
        self.cluster_id.set_text("")
        #self.extends.set_text("None")
        self.content_ref.set_text("")
        self.href.get_model().clear()
        self.severity.set_active(-1)

        self.titles.clear()
        self.descriptions.clear()
        self.warnings.clear()
        self.statuses.clear()
        self.questions.clear()
        self.rationales.clear()
        self.item_values.clear()
        self.conflicts.fill(None)
        self.requires.fill(None)
        self.platforms.fill()
        self.fix.fill()
        self.fixtext.fill()
        self.__unblock_signals()

    def __update(self):
 
        if self.core.selected_item != None:
            details = self.data_model.get_item_details(self.core.selected_item)
        else:
            details = None
            #self.item = None
        
        self.__clear()
        if details == None:
            self.items.set_sensitive(False)
            return

        # Check if the item is value and change widgets
        if details["type"] == openscap.OSCAP.XCCDF_VALUE:
            self.show(False)
            self.values.show(True)
            self.values.update()
            return
        else: 
            self.show(True)
            self.values.show(False)

        # Item is not value, continue
        self.__block_signals()
        self.item_id.set_text(details["id"] or "")
        self.weight.set_text(str(details["weight"] or ""))
        self.version.set_text(details["version"] or "")
        self.version_time.set_text("" if details["version_time"] <= 0 else str(datetime.date.fromtimestamp(details["version_time"])))
        self.cluster_id.set_text(details["cluster_id"] or "")
        self.extends.set_text(details["extends"] or "")
        self.titles.fill()
        self.descriptions.fill()
        self.warnings.fill()
        self.statuses.fill()
        self.questions.fill()
        self.rationales.fill()
        self.conflicts.fill(details)
        self.requires.fill(details["item"])
        self.platforms.fill()

        self.abstract.set_active(details["abstract"])
        self.selected.set_active(details["selected"])
        self.hidden.set_active(details["hidden"])
        self.prohibit.set_active(details["prohibit_changes"])

        self.items.set_sensitive(True)

        # Set sensitivity for rule / group
        self.ident_box.set_sensitive(details["type"] == openscap.OSCAP.XCCDF_RULE)
        self.item_values_main.set_sensitive(details["type"] == openscap.OSCAP.XCCDF_RULE)
        self.operations.set_sensitive(details["type"] == openscap.OSCAP.XCCDF_RULE)
        self.severity.set_sensitive(details["type"] == openscap.OSCAP.XCCDF_RULE)

        if details["type"] == openscap.OSCAP.XCCDF_RULE: # Item is Rule
            self.severity.set_active(ENUM.LEVEL.pos(details["severity"]))
            self.impact_metric.set_text(details["imapct_metric"] or "")
            self.fixtext.fill()
            self.fix.fill()
            self.ident.fill()
            content = self.data_model.get_item_content()
 
            if len(self.core.lib.files) > 0:
                self.href.get_model().clear()
                for name in self.core.lib.files.keys():
                    self.href.get_model().append([name, name])
            if content != None and len(content) > 0:
                self.content_ref.set_text(content[0][0] or "")
                for i, item in enumerate(self.href.get_model()):
                    if item[0] == content[0][1]: self.href.set_active(i)
            self.item_values.fill()
            
        else: # Item is GROUP
            self.severity.set_active(-1)
            self.impact_metric.set_text("")
            self.fixtext.fill()
            self.fix.fill()
            self.ident.fill()

        self.__unblock_signals()
        