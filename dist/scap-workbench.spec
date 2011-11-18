%if ! (0%{?fedora} > 12 || 0%{?rhel} > 5)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}
%endif


Summary: Scanning, tailoring, editing and validation tool for SCAP content
Name: scap-workbench
URL: https://fedorahosted.org/scap-workbench/
Version: 0.5.2
Release: 1%{?dist}
License: GPLv3+
Group: System Environment/Base
Source0: https://fedorahosted.org/released/scap-workbench/%{name}-%{version}.tar.bz2
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}
BuildArch: noarch
BuildRequires: python2-devel desktop-file-utils
Requires: openscap-python >= 0.7.2
Requires: pywebkitgtk python-BeautifulSoup

%description
scap-workbench is GUI tool that provides scanning, tailoring, 
editing and validation functionality for SCAP content. The tool 
is based on OpenSCAP library.

%prep
%setup -q

%build

%install
rm -rf $RPM_BUILD_ROOT
make install DESTDIR=$RPM_BUILD_ROOT
desktop-file-validate $RPM_BUILD_ROOT%{_datadir}/applications/scap-workbench.desktop
desktop-file-validate $RPM_BUILD_ROOT%{_datadir}/applications/scap-workbench-editor.desktop

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
%doc COPYING README
%dir %{_sysconfdir}/scap-workbench
%config(noreplace) %{_sysconfdir}/scap-workbench/logger.conf
%{_bindir}/scap-workbench
%{_bindir}/scap-workbench-editor
%dir %{python_sitelib}/scap_workbench
%{python_sitelib}/scap_workbench/*
%dir %{_datadir}/scap-workbench/
%{_datadir}/scap-workbench/*
%{_mandir}/man8/scap-workbench.8.gz
%{_mandir}/man8/scap-workbench-editor.8.gz
%{_datadir}/applications/scap-workbench.desktop
%{_datadir}/applications/scap-workbench-editor.desktop
%{_datadir}/pixmaps/scap-workbench.png

%changelog
* Fri Nov 18 2011 Martin Preisler
- New upstream version 0.5.2

* Wed Oct 19 2011 Martin Preisler <mpreisle@redhat.com> 0.5.1-1
- Don't use the deprecated "gnome" module
- Only use absolute imports in intra-package modules

* Wed Oct 12 2011 Martin Preisler <mpreisle@redhat.com> 0.5.0-1
- Commenting, refactoring and code cleanup
- New uncaught exception dialog
- Version time editing
- Fixed bugs

* Thu Jun 30 2011 Maros Barabas <xbarry@gmail.com> 0.4.0-1
- Redesign of abstract classes in editor
- New dialog module
- New preview dialog
- UI improvements
- Added documentation
- Fixed bugs

* Fri Apr 29 2011 Maros Barabas <mbarabas@redhat.com> 0.3.0-1
- Split scanner and editor to two separate parts
- New import and export dialogs in Editor
- Improved HTML editing of descriptions
- New notifications
- New editing of profiles with refines
- Fixes and small changes

* Fri Mar 11 2011 Maros Barabas <mbarabas@redhat.com> 0.2.3-1
- Refactoring of editor, more code added to glade files
- Improved UI, added new classes for editing
- New handling of values items in editor
- Better thread handling of concurrent actions
- Lot of fixes

* Fri Feb 18 2011 Maros Barabas <mbarabas@redhat.com> 0.2.2-1
- Improved design of GUI
- Improved notifications and event handling
- Added OVAL metadata information
- Lot of small fixes
- Now possible to close XCCDF file from main page

* Fri Feb 11 2011 Maros Barabas <mbarabas@redhat.com> 0.2.1-1
- Improved XCCDF editor: added new panel with general options
- Fixed lot of bugs in edit and command modules

* Mon Jan 31 2011 Maros Barabas <mbarabas@redhat.com> 0.2.0-1
- Added -D option for debug mode, default logger level set to info
- Improved Tailoring page: added profile selection and refines tailoring
- Added Edit page with editing capability of XCCDF files
- Removed Profile page - editing profiles moved to Edit page
- Improved stop functionality in Scan page
- Lot of small fixes

* Thu Oct 21 2010 Peter Vrabec <pvrabec@redhat.com> 0.1.0-1
- the first official release

