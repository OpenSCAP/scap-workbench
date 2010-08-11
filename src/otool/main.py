#!/usr/bin/env python
# -*- coding: utf-8 -*-

import render
import sys
import gtk

sys.path.append("/tmp/scap/usr/local/lib64/python2.6/site-packages")
try:
    import openscap_api as openscap
except Exception as ex:
    print ex
    openscap=None


if __name__ == "__main__":
    render.Main_window()
    gtk.main()
