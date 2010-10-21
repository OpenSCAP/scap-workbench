%if ! (0%{?fedora} > 12 || 0%{?rhel} > 5)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python_sitearch: %global python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}
%endif


Summary: Scanning, tailoring, editing and validation tool for SCAP content
Name: scap-workbench
URL: https://fedorahosted.org/scap-workbench/
Version: 0.1.0
Release: 1%{?dist}
License: GPLv3
Group: System Environment/Base
Source0: https://fedorahosted.org/releases/s/c/scap-workbench/%{name}-%{version}.tar.bz2
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}
BuildArch: noarch
BuildRequires: python2-devel
Requires: openscap-python

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

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
%doc COPYING README
%config(noreplace) %{_sysconfdir}/scap-workbench/logger.conf
%{_bindir}/scap-workbench
%dir %{python_sitelib}/scap_workbench
%{python_sitelib}/scap_workbench/*
%dir /usr/share/scap-workbench/
/usr/share/scap-workbench/*

%changelog
* Thu Oct 21 2010 Peter Vrabec <pvrabec@redhat.com> 0.1.0-1
- the first official release

