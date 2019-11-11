%{!?_pkgdocdir: %global _pkgdocdir %{_docdir}/%{name}-%{version}}

Name:       scap-workbench
Version:    1.2.0
Release:    3%{?dist}
Summary:    Scanning, tailoring, editing and validation tool for SCAP content

License:    GPLv3+
URL:        http://www.open-scap.org/tools/scap-workbench
Source0:    https://github.com/OpenSCAP/scap-workbench/releases/download/%{version}/scap-workbench-%{version}.tar.bz2

BuildRequires:  cmake >= 2.6
BuildRequires:  qt5-devel >= 5.0.0

BuildRequires:  openscap-devel >= 1.2.11
BuildRequires:  openscap-utils >= 1.2.11
Requires:       openscap-utils >= 1.2.11
# ssh to scan remote machines
BuildRequires:  openssh-clients
Requires:       openssh-clients
Requires:       openssh-askpass
# because of 'setsid' which we use to force ssh to use GUI askpass
BuildRequires:  util-linux
Requires:       util-linux
# for privileged local scanning
Requires:       polkit
# default content
Requires:       scap-security-guide
# fonts, see https://bugzilla.redhat.com/show_bug.cgi?id=1134418
Requires:       font(:lang=en)

%description
scap-workbench is GUI tool that provides scanning functionality for SCAP
content. The tool is based on OpenSCAP library.

%prep
%setup -q

%build
%cmake -D CMAKE_INSTALL_DOCDIR=%{_pkgdocdir} .
make %{?_smp_mflags}

%install
make install DESTDIR=%{buildroot}

%files
%{_bindir}/scap-workbench
%{_datadir}/applications/scap-workbench.desktop
%{_datadir}/scap-workbench/*.png
%{_datadir}/scap-workbench/translations/*
%{_libexecdir}/scap-workbench-oscap.sh
%{_libexecdir}/scap-workbench-pkexec-oscap.sh
%{_libexecdir}/scap-workbench-rpm-extract.sh
%{_datadir}/polkit-1/actions/scap-workbench-oscap.policy
%{_datadir}/pixmaps/scap-workbench.png
%{_datadir}/pixmaps/scap-workbench.svg
%{_datadir}/appdata/scap-workbench.appdata.xml
%doc %{_mandir}/man8/scap-workbench.8.gz
%doc %{_pkgdocdir}/user_manual.html
%doc %{_pkgdocdir}/COPYING
%doc %{_pkgdocdir}/README.md

%changelog
* Fri Jul 26 2019 Fedora Release Engineering <releng@fedoraproject.org> - 1.2.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_31_Mass_Rebuild

* Sat Feb 02 2019 Fedora Release Engineering <releng@fedoraproject.org> - 1.2.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_30_Mass_Rebuild

* Wed Jul 18 2018 Martin Preisler <mpreisle@redhat.com> 1.2.0-1
- Updated to new upstream release 1.2.0
- Now using Qt5

* Sat Jul 14 2018 Fedora Release Engineering <releng@fedoraproject.org> - 1.1.6-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_29_Mass_Rebuild

* Fri Feb 09 2018 Fedora Release Engineering <releng@fedoraproject.org> - 1.1.6-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_28_Mass_Rebuild

* Fri Nov 10 2017 Martin Preisler <mpreisle@redhat.com> 1.1.6-1
- Updated to new upstream release 1.1.6

* Thu Aug 03 2017 Fedora Release Engineering <releng@fedoraproject.org> - 1.1.5-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Binutils_Mass_Rebuild

* Thu Jul 27 2017 Fedora Release Engineering <releng@fedoraproject.org> - 1.1.5-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Mon Jun 19 2017 Martin Preisler <mpreisle@redhat.com> 1.1.5-1
- Updated to new upstream release 1.1.5

* Sat Feb 11 2017 Fedora Release Engineering <releng@fedoraproject.org> - 1.1.4-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Tue Jan 17 2017 Martin Preisler <mpreisle@redhat.com> - 1.1.4-2
- Rebuilt for OpenSCAP 1.2.13

* Mon Jan 02 2017 Martin Preisler <mpreisle@redhat.com> 1.1.4-1
- Updated to new upstream release 1.1.4

* Mon Dec 12 2016 Martin Preisler <mpreisle@redhat.com> 1.1.3-1
- Updated to new upstream release 1.1.3
- Bumped openscap requirement to 1.2.11 because of the remote resource warning

* Mon Jun 20 2016 Martin Preisler <mpreisle@redhat.com> 1.1.2-1
- Updated to new upstream release 1.1.2
- Removed SCL related bits

* Thu Feb 04 2016 Fedora Release Engineering <releng@fedoraproject.org> - 1.1.1-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Mon Nov 02 2015 Martin Preisler <mpreisle@redhat.com> 1.1.1-2
- Require English fonts (bz#1134418)
- Updated with latest upstream URLs
- Reorganized the spec a little

* Tue Sep 29 2015 Martin Preisler <mpreisle@redhat.com> 1.1.1-1
- Updated to new upstream release 1.1.1-1

* Wed Jul 29 2015 Martin Preisler <mpreisle@redhat.com> 1.1.0-4
- Make BuildRequires more explicit by requiring qt >= 4.0.0 and cmake >= 2.6

* Fri Jun 19 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.1.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Sat May 02 2015 Kalev Lember <kalevlember@gmail.com> - 1.1.0-2
- Rebuilt for GCC 5 C++11 ABI change

* Tue Mar 24 2015 Martin Preisler <mpreisle@redhat.com> 1.1.0-1
- Updated to new upstream release 1.1.0
- Added openssh-clients and util-linux to BuildRequires, workbench checks those
  at configure time now
- Added scap-security-guide to Requires

* Fri Jan 09 2015 Martin Preisler <mpreisle@redhat.com> 1.0.3-1
- Updated to new upstream release 1.0.3

* Thu Oct 30 2014 Martin Preisler <mpreisle@redhat.com> 1.0.2-2
- Fix RPM open functionality, see rhbz#1154039

* Wed Sep 24 2014 Martin Preisler <mpreisle@redhat.com> 1.0.2-1
- Updated to new upstream release 1.0.2

* Fri Sep 05 2014 Martin Preisler <mpreisle@redhat.com> 1.0.1-1
- Updated to new upstream release 1.0.1

* Mon Aug 18 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_22_Mass_Rebuild

* Fri Jun 27 2014 Martin Preisler <mpreisle@redhat.com> 1.0.0-1
- Updated to new version

* Tue Jun 10 2014 Martin Preisler <mpreisle@redhat.com> 0.8.9-1
- Updated to new version
- appdata is now available

* Sun Jun 08 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.8.8-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Wed Mar 26 2014 Martin Preisler <mpreisle@redhat.com> 0.8.8-1
- Updated to new version

* Wed Feb 19 2014 Martin Preisler <mpreisle@redhat.com> 0.8.7-1
- Updated to new version

* Thu Jan 30 2014 Martin Preisler <mpreisle@redhat.com> 0.8.6-1
- Updated to new version
- Require polkit

* Mon Jan 20 2014 Martin Preisler <mpreisle@redhat.com> 0.8.5-2
- Require openssh-askpass for GUI openssh challenge responses

* Fri Jan 10 2014 Martin Preisler <mpreisle@redhat.com> 0.8.5-1
- Updated to new version

* Mon Dec 09 2013 Martin Preisler <mpreisle@redhat.com> 0.8.4-1
- Updated to new version

* Fri Nov 29 2013 Martin Preisler <mpreisle@redhat.com> 0.8.3-1
- Updated to new version
- Added measures to deal with unversioned pkgdocdir in Fedora 20+

* Mon Nov 18 2013 Martin Preisler <mpreisle@redhat.com> 0.8.2-2
- Removed the openscap detection workaround, it is no longer needed with openscap 0.9.13

* Wed Oct 30 2013 Martin Preisler <mpreisle@redhat.com> 0.8.2-1
- Updated to new version
- Added a workaround to the cmake invocation because of faulty openscap .pc file

* Fri Sep 20 2013 Martin Preisler <mpreisle@redhat.com> 0.8.1-1
- Updated to new version

* Sun Aug 04 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.8.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Thu Jul 04 2013 Martin Preisler <mpreisle@redhat.com> 0.8.0-1
- Initial release of the rewritten workbench
