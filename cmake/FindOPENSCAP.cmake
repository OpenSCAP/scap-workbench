# - Try to find OpenSCAP
# Once done, this will define
#
#  OPENSCAP_FOUND - system has OpenSCAP
#  OPENSCAP_INCLUDE_DIRS - the OpenSCAP include directories
#  OPENSCAP_LIBRARIES - link these to use OpenSCAP

include(LibFindMacros)

# Use pkg-config to get hints about paths
libfind_pkg_check_modules(OPENSCAP_PKGCONF libopenscap)

# Include dir
find_path(OPENSCAP_INCLUDE_DIR
	NAMES xccdf_session.h
	PATHS ${OPENSCAP_PKGCONF_INCLUDE_DIRS}
	PATH_SUFFIXES openscap
)

# Finally the library itself
find_library(OPENSCAP_LIBRARY
	NAMES openscap
	PATHS ${OPENSCAP_PKGCONF_LIBRARY_DIRS}
)

# Set the include dir variables and the libraries and let libfind_process do the rest.
# NOTE: Singular variables for this library, plural for libraries this this lib depends on.
set(OPENSCAP_PROCESS_INCLUDES OPENSCAP_INCLUDE_DIR)
set(OPENSCAP_PROCESS_LIBS OPENSCAP_LIBRARY)
libfind_process(OPENSCAP)
