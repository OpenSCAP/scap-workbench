PKG=scap-workbench
WRK_PKG=scap_workbench
VERSION := $(shell python src/scap_workbench/version.py)

PY_LIB  := $(shell python -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")
PY_VER  := python$(shell python -c "import sys; print sys.version[:3]")

PREFIX=$(DESTDIR)/usr
BINDIR=$(PREFIX)/bin
SBINDIR=$(PREFIX)/sbin
DATADIR=$(PREFIX)/share
MANDIR=$(DATADIR)/man
PKGDATADIR=$(DATADIR)/$(WRK_PKG)
PKGIMAGESDIR=$(PKGDATADIR)/images
LIBEXECDIR=$(PREFIX)/libexec
SYSCONFDIR=$(DESTDIR)/etc
PYTHON_LIB=$(DESTDIR)$(PY_LIB)
PYTHON_LIB_PKG=$(PYTHON_LIB)/$(WRK_PKG)

INSTALL=/usr/bin/install -c
MODE_DIR = -m 755
MODE_EXEC = -m 755
MODE_REG = -m 644

all:

install:
	test -d $(BINDIR) || $(INSTALL) $(MODE_DIR) -d $(BINDIR)
	test -d $(SYSCONFDIR)/$(PKG) || $(INSTALL) $(MODE_DIR) -d $(SYSCONFDIR)/$(PKG)
	test -d $(DATADIR)/$(PKG) || $(INSTALL) $(MODE_DIR) -d $(DATADIR)/$(PKG)
	test -d $(DATADIR)/$(PKG)/glade || $(INSTALL) $(MODE_DIR) -d $(DATADIR)/$(PKG)/glade
	test -d $(DATADIR)/$(PKG)/glade/dialogs || $(INSTALL) $(MODE_DIR) -d $(DATADIR)/$(PKG)/glade/dialogs
	test -d $(DATADIR)/$(PKG)/filters || $(INSTALL) $(MODE_DIR) -d $(DATADIR)/$(PKG)/filters
	test -d $(MANDIR)/man8 || $(INSTALL) $(MODE_DIR) -d $(MANDIR)/man8
	test -d $(DATADIR)/pixmaps || $(INSTALL) $(MODE_DIR) -d $(DATADIR)/pixmaps
	test -d $(DATADIR)/applications || $(INSTALL) $(MODE_DIR) -d $(DATADIR)/applications
	test -d $(PYTHON_LIB) || $(INSTALL) $(MODE_DIR) -d $(PYTHON_LIB)
	test -d $(PYTHON_LIB_PKG) || $(INSTALL) $(MODE_DIR) -d $(PYTHON_LIB_PKG)
	test -d $(PYTHON_LIB_PKG)/core || $(INSTALL) $(MODE_DIR) -d $(PYTHON_LIB_PKG)/core
	test -d $(PYTHON_LIB_PKG)/scanner || $(INSTALL) $(MODE_DIR) -d $(PYTHON_LIB_PKG)/scanner
	$(INSTALL) $(MODE_EXEC) src/bin/$(PKG) $(BINDIR)/$(PKG)
	$(INSTALL) $(MODE_REG) src/$(WRK_PKG)/*.py $(PYTHON_LIB_PKG)
	$(INSTALL) $(MODE_REG) src/$(WRK_PKG)/core/*.py $(PYTHON_LIB_PKG)/core
	$(INSTALL) $(MODE_REG) src/$(WRK_PKG)/scanner/*.py $(PYTHON_LIB_PKG)/scanner
	$(INSTALL) $(MODE_REG) src/etc/$(PKG)/logger.conf $(SYSCONFDIR)/$(PKG)/logger.conf
	$(INSTALL) $(MODE_REG) src/share/$(PKG)/glade/*.glade $(DATADIR)/$(PKG)/glade
	$(INSTALL) $(MODE_REG) src/share/$(PKG)/glade/dialogs/*.glade $(DATADIR)/$(PKG)/glade/dialogs
	$(INSTALL) $(MODE_REG) src/share/$(PKG)/filters/*.py $(DATADIR)/$(PKG)/filters
	$(INSTALL) $(MODE_REG) src/man/scap-workbench.8 $(MANDIR)/man8
	gzip -f $(MANDIR)/man8/scap-workbench.8
	$(INSTALL) $(MODE_REG) src/share/pixmaps/*.png $(DATADIR)/pixmaps
	$(INSTALL) $(MODE_REG) scap-workbench.desktop $(DATADIR)/applications/scap-workbench.desktop

archive: clean
	@rm -rf $(PKG)-$(VERSION).tar.bz2
	@rm -rf /tmp/$(PKG)-$(VERSION)
	@mkdir /tmp/$(PKG)-$(VERSION)
	@cp -a COPYING README Makefile scap-workbench.desktop src /tmp/$(PKG)-$(VERSION)
	@rm -f /tmp/$(PKG)-$(VERSION)/src/bin/runwrapper.sh
	@rm -f /tmp/$(PKG)-$(VERSION)/src/{pylint.cfg,perform-pylint,pylint-output}
	@find /tmp/$(PKG)-$(VERSION) -type f -name "*.pyc" | xargs rm -f
	@find /tmp/$(PKG)-$(VERSION) -type f -name "*~" | xargs rm -f
	@dir=$$PWD; cd /tmp; tar --bzip2 -cSpf $$dir/$(PKG)-$(VERSION).tar.bz2 $(PKG)-$(VERSION)
	@rm -rf /tmp/$(PKG)-$(VERSION)
	@echo "The archive is in $(PKG)-$(VERSION).tar.bz2"

clean:
	@rm -rfv *.pyc

