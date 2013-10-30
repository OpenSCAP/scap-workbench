cmake_minimum_required(VERSION 2.6)

project("scap-workbench")
set(SCAP_WORKBENCH_VERSION_MAJOR "0")
set(SCAP_WORKBENCH_VERSION_MINOR "8")
set(SCAP_WORKBENCH_VERSION_PATCH "2")
set(SCAP_WORKBENCH_VERSION "${SCAP_WORKBENCH_VERSION_MAJOR}.${SCAP_WORKBENCH_VERSION_MINOR}.${SCAP_WORKBENCH_VERSION_PATCH}")
set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_SOURCE_DIR}/cmake/")

include(GNUInstallDirs)

find_package(Qt4 REQUIRED QtCore QtGui QtXmlPatterns)
find_package(Qt4 COMPONENTS QtWebKit) # optional

if(NOT QT_QTWEBKIT_INCLUDE_DIR)
  set(QT_USE_QTWEBKIT 0) # do not use webkit if it was not found
endif()

include("${CMAKE_ROOT}/Modules/FindPkgConfig.cmake")
pkg_check_modules(OPENSCAP REQUIRED libopenscap>=0.9.12)

set(SCAP_WORKBENCH_DEFAULT_CONTENT "/usr/share/xml/scap/ssg/fedora/ssg-fedora-xccdf.xml" CACHE FILEPATH
    "Path to XCCDF or SDS that will be opened in case user doesn't specify different content using command line arguments.")
set(SCAP_WORKBENCH_SCAP_CONTENT_DIRECTORY "/usr/share/xml/scap" CACHE PATH
    "Directory where SCAP content is *usually* stored. This is the default directory when opening a file via file open dialog.")

file(GLOB scap_workbench_HEADERS "${CMAKE_SOURCE_DIR}/include/*.h")
qt4_wrap_cpp(scap_workbench_HEADERS_MOC ${scap_workbench_HEADERS})

file(GLOB scap_workbench_UIS "${CMAKE_SOURCE_DIR}/ui/*.ui")
qt4_wrap_ui(scap_workbench_UIS_HEADERS ${scap_workbench_UIS})

file(GLOB scap_workbench_SOURCES "${CMAKE_SOURCE_DIR}/src/*.cpp")

set(SCAP_WORKBENCH_INCLUDE_DIRS
    ${CMAKE_CURRENT_SOURCE_DIR}/include ${CMAKE_CURRENT_BINARY_DIR}
    ${QT_QTCORE_INCLUDE_DIR} ${QT_QTGUI_INCLUDE_DIR} ${QT_QTXMLPATTERNS_INCLUDE_DIR}
    ${OPENSCAP_INCLUDE_DIRS})

set(SCAP_WORKBENCH_LINK_LIBRARIES
    ${QT_QTCORE_LIBRARY}
    ${QT_QTGUI_LIBRARY}
    ${QT_QTXMLPATTERNS_LIBRARY}
    ${OPENSCAP_LIBRARIES})

set(SCAP_WORKBENCH_USE_WEBKIT ${QT_USE_QTWEBKIT} CACHE BOOL "Whether we should use Qt WebKit to show reports in workbench directly.")
if(SCAP_WORKBENCH_USE_WEBKIT)
    list(APPEND SCAP_WORKBENCH_LINK_LIBRARIES ${QT_QTWEBKIT_LIBRARY})
    list(APPEND SCAP_WORKBENCH_INCLUDE_DIRS ${QT_QTWEBKIT_INCLUDE_DIR})
endif()

configure_file("include/Config.h.in" "${CMAKE_CURRENT_BINARY_DIR}/Config.h")

include_directories(${SCAP_WORKBENCH_INCLUDE_DIRS})

add_executable("scap-workbench"
    ${scap_workbench_HEADERS}
    ${scap_workbench_SOURCES}

    ${scap_workbench_HEADERS_MOC}
    ${scap_workbench_UIS_HEADERS}
)

target_link_libraries("scap-workbench" ${SCAP_WORKBENCH_LINK_LIBRARIES})

install(TARGETS "scap-workbench"
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})

install(FILES "man/scap-workbench.8"
    DESTINATION "${CMAKE_INSTALL_MANDIR}/man8")

install(FILES "scap-workbench.desktop"
    DESTINATION "${CMAKE_INSTALL_DATADIR}/applications")
install(FILES "share/pixmaps/scap-workbench.png"
    DESTINATION "${CMAKE_INSTALL_DATADIR}/pixmaps")

# only CPack should follow
set(CPACK_CMAKE_GENERATOR "Unix Makefiles")
set(CPACK_SOURCE_GENERATOR "TBZ2")
set(CPACK_SOURCE_PACKAGE_FILE_NAME "scap-workbench-${SCAP_WORKBENCH_VERSION}" CACHE INTERNAL "tarball basename")
set(CPACK_SOURCE_IGNORE_FILES
"\\\\.git.*"

"build/"
"~$"

"\\\\.settings/"
"\\\\.project"
"\\\\.cproject"
)
include(CPack)
