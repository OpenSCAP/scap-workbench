SCAP Workbench
==============

A GUI tool that provides scanning, tailoring and validation functionality for SCAP content

About
-----

SCAP Workbench is a GUI tool that provides scanning, tailoring
and validation functionality for SCAP content. It uses openscap library
to access SCAP functionalities.

Homepage of the project is https://fedorahosted.org/scap-workbench/

How to run it out of the box
----------------------------

1) Make sure you have installed all prerequisites

required dependencies:
```bash
yum install cmake gcc-c++ openssh-clients util-linux openscap-devel qt-devel
```

required dependencies (only for the git repo, not required for released tarballs):
```bash
yum install rubygem-asciidoctor
```

optional dependencies:
```bash
yum install polkit
```

2) Build SCAP Workbench:
```bash
mkdir build; cd build
cmake ../
make
```

3) Install SCAP Workbench: (optional)

(inside the build folder):
```bash
make install
```

4a) Run SCAP Workbench: (if it was installed)

spawning open file dialog:
```bash
scap-workbench
```

with an XCCDF file to load:
```bash
scap-workbench /path/to/xccdf-file.xml
```

with a source datastream (SDS) to load:
```bash
scap-workbench /path/to/sds-file
```

4b) Run SCAP Workbench: (straight from build dir, without installation)

```bash
cd build/
bash runwrapper.sh ./scap-workbench
```

What now?
---------

You should have a built SCAP Workbench executable by now. Please refer to the user manual for documentation on how to use it.

There are 3 ways to get the user manual:

 * Click `Help -> User Manual` in the application
 * Open `/usr/share/doc/scap-workbench/user_manual.html` (installed system-wide) or `doc/user_manual.html` (from the tarball) in your browser
 * Open or download [user manual from the website](https://fedorahosted.org/scap-workbench/raw-attachment/wiki/UserManual/user_manual.html)

How to make a tarball
---------------------
```bash
mkdir build; cd build
cmake ../
make package_source
```
