SCAP Workbench
==============

A GUI tool that provides scanning, tailoring and validation functionality for SCAP content

About
-----

SCAP Workbench is a GUI tool that provides scanning, tailoring
and validation functionality for SCAP content. It uses openscap library
to access SCAP functionalities.

Homepage of the project is https://www.open-scap.org/tools/scap-workbench/

How to run it out of the box
----------------------------

1) Make sure you have installed all prerequisites

required dependencies:
```console
# yum install cmake gcc-c++ openssh-clients util-linux openscap-devel qt5-qtbase-devel qt5-qtxmlpatterns-devel openssh-askpass
```

required dependencies (only for the git repo, not required for released tarballs):
```console
# yum install asciidoc
```

optional dependencies:
```console
# yum install polkit
```

On Ubuntu this is roughly equivalent to:

```console
# apt install build-essential openssh-client libopenscap-dev libqt5xmlpatterns5-dev ssh-askpass
# apt install asciidoc
# apt install libpolkit-agent-1-0
```

2) Build SCAP Workbench:
```console
$ mkdir build; cd build
$ cmake ../
$ make
```
To build against locally built OpenSCAP library export following variables:

```console
$ export PKG_CONFIG_PATH="$PKG_CONFIG_PATH:/PATH/TO/DIR/WITH/.pcFILE/"
$ export LIBRARY_PATH=/PATH/TO/DIR/WITH/openscap.soFILE/
```

Additionally it is possible to use custom CMake definitions instead of exporting environment variables:

```console
$ cmake -DOPENSCAP_LIBRARIES:PATH=/local/openscap.so/filepath/ \
    -DOPENSCAP_INCLUDE_DIRS:PATH=/local/openscap/include/path \
    -DOPENSCAP_VERSION:STRING="X.Y.Z" \
    ../
$ make
```

3) Install SCAP Workbench: (optional)

(inside the build folder):
```console
$ # may require superuser privileges if you didn't set different installation
$ # prefix (CMAKE_INSTALL_PREFIX)
$ make install
```

4a) Run SCAP Workbench: (if it was installed)

spawning open file dialog:
```console
$ scap-workbench
```

with an XCCDF file to load:
```console
$ scap-workbench /path/to/xccdf-file.xml
```

with a source datastream (SDS) to load:
```console
$ scap-workbench /path/to/sds-file
```

4b) Run SCAP Workbench: (straight from build dir, without installation)

Note: If you have built SCAP-Workbench against locally built OpenSCAP library, then run one of the following commands:

```console
$ ldconfig /PATH/TO/DIR/WITH/openscap.soFILE/
```
or
```console
$ export LD_LIBRARY_PATH=/PATH/TO/DIR/WITH/openscap.soFILE/
```

and then:

```console
$ cd build/
$ bash runwrapper.sh ./scap-workbench
```

What now?
---------

You should have a built SCAP Workbench executable by now. Please refer to the user manual for documentation on how to use it.

There are 3 ways to get the user manual:

 * Click `Help -> User Manual` in the application
 * Open `/usr/share/doc/scap-workbench/user_manual.html` (installed system-wide) or `doc/user_manual.html` (from the tarball) in your browser
 * Open or download [user manual from the website](https://static.open-scap.org/scap-workbench-1.1/)

How to make a tarball
---------------------
```console
$ mkdir build; cd build
$ cmake ../
$ make package_source
```
