from scap_workbench import filter
import re

class TailoringFilter1(filter.Filter):

    TYPE="gui:btn:tailoring:filter"

    def __init__(self, renderer):
        
        filter.Filter.__init__(self)
        self.name = "Hide groups"
        self.description = "Show all rules in list, hide groups."
        self.func = self.__search_func
        self.params = {}
        self.istree = False
        self.renderer = renderer

    def __search_func(self, model, iter, params):
        pattern = re.compile("rule", re.IGNORECASE)
        return pattern.search(model.get_value(iter, 0), 0, 4) != None

class TailoringFilter2(filter.Filter):

    TYPE="gui:btn:tailoring:filter"

    def __init__(self, renderer):
        
        filter.Filter.__init__(self)
        self.name = "Show only groups with rules"
        self.description = "Hide all groups that has no rules."
        self.func = self.__search_func
        self.params = {}
        self.istree = True
        self.renderer = renderer

    def __search_func(self, model, iter, params):
        pattern = re.compile("rule", re.IGNORECASE)
        return pattern.search(model.get_value(iter, 0), 0, 4) != None


class TailoringFilter3(filter.Filter):

    TYPE="gui:btn:tailoring:filter"

    def __init__(self, renderer):
        
        filter.Filter.__init__(self)
        self.name = "Show only selected rules/groups"
        self.description = "Hide all groups and rules that are not selected."
        self.func = self.__search_func
        self.params = {"selected": True}
        self.istree = True
        self.renderer = renderer

    def __search_func(self, model, iter, params):
        pattern = re.compile("rule", re.IGNORECASE)
        return pattern.search(model.get_value(iter, 0), 0, 4) != None


class ScanFilter1(filter.Filter):

    TYPE="gui:btn:menu:scan:filter"

    def __init__(self, renderer):
        
        filter.Filter.__init__(self)
        self.name = "Only tests with result PASS"
        self.description = "Show tests that has result PASS"
        self.func = self.__search_func
        self.params = ["PASS"]
        self.istree = False
        self.renderer = renderer

    def __search_func(self, model, iter, params):
        pattern = re.compile(params[0],re.IGNORECASE)
        return pattern.search(model.get_value(iter, filter.ScanFilter.COLUMN_RESULT)) != None

class ScanFilter2(filter.Filter):

    TYPE="gui:btn:menu:scan:filter"

    def __init__(self, renderer):
        
        filter.Filter.__init__(self)
        self.name = "Only tests with result ERROR"
        self.description = "Show tests that has result ERROR"
        self.func = self.__search_func
        self.params = ["ERROR"]
        self.istree = False
        self.renderer = renderer

    def __search_func(self, model, iter, params):
        pattern = re.compile(params[0],re.IGNORECASE)
        return pattern.search(model.get_value(iter, filter.ScanFilter.COLUMN_RESULT)) != None

class ScanFilter3(filter.Filter):

    TYPE="gui:btn:menu:scan:filter"

    def __init__(self, renderer):
        
        filter.Filter.__init__(self)
        self.name = "Only tests with result FAIL"
        self.description = "Show tests that has result FAIL"
        self.func = self.__search_func
        self.params = ["FAIL"]
        self.istree = False
        self.renderer = renderer

    def __search_func(self, model, iter, params):
        pattern = re.compile(params[0],re.IGNORECASE)
        return pattern.search(model.get_value(iter, filter.ScanFilter.COLUMN_RESULT)) != None
