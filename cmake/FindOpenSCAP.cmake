# - Try to find libopenscap
# Once done this will define
#  LIBOPENSCAP_INCLUDE_DIR - The OpenSCAP include directories
#  LIBOPENSCAP_LIBRARY - The libraries needed to use OpenSCAP

find_package(PkgConfig)
pkg_check_modules(PC_LIBOPENSCAP QUIET openscap)
set(LIBOPENSCAP_DEFINITIONS ${PC_LIBOPENSCAP_CFLAGS_OTHER})

find_path(LIBOPENSCAP_INCLUDE_DIR xccdf_session.h
    HINTS ${PC_LIBOPENSCAP_INCLUDEDIR} ${PC_LIBOPENSCAP_INCLUDE_DIRS}
    PATH_SUFFIXES openscap)

find_library(LIBOPENSCAP_LIBRARY NAMES openscap libopenscap
    HINTS ${PC_LIBOPENSCAP_LIBDIR} ${PC_LIBOPENSCAP_LIBRARY_DIRS} )

set(LIBOPENSCAP_LIBRARIES ${LIBOPENSCAP_LIBRARY})
set(LIBOPENSCAP_INCLUDE_DIRS ${LIBOPENSCAP_INCLUDE_DIR})

include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(OpenSCAP  DEFAULT_MSG
    LIBOPENSCAP_LIBRARY LIBOPENSCAP_INCLUDE_DIR)

mark_as_advanced(LIBOPENSCAP_INCLUDE_DIR LIBOPENSCAP_LIBRARY )
