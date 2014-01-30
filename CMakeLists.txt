cmake_minimum_required(VERSION 2.6)

project("scap-workbench")
set(SCAP_WORKBENCH_VERSION_MAJOR "0")
set(SCAP_WORKBENCH_VERSION_MINOR "8")
set(SCAP_WORKBENCH_VERSION_PATCH "6")
set(SCAP_WORKBENCH_VERSION "${SCAP_WORKBENCH_VERSION_MAJOR}.${SCAP_WORKBENCH_VERSION_MINOR}.${SCAP_WORKBENCH_VERSION_PATCH}")
set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_SOURCE_DIR}/cmake/")

include(GNUInstallDirs)

find_package(Qt4 REQUIRED QtCore QtGui QtXmlPatterns)
find_package(Qt4 COMPONENTS QtWebKit) # optional

if(NOT QT_QTWEBKIT_INCLUDE_DIR)
  set(QT_USE_QTWEBKIT 0) # do not use webkit if it was not found
endif()

# This conditional is here to avoid checking openscap version if user supplies
# custom openscap parameters.
if (NOT DEFINED OPENSCAP_LIBRARIES OR NOT DEFINED OPENSCAP_INCLUDE_DIRS)
    include("${CMAKE_ROOT}/Modules/FindPkgConfig.cmake")
    pkg_check_modules(OPENSCAP REQUIRED libopenscap>=0.9.12)
endif()

# This is optional, only required if user wants documentation rebuilt
find_program(ASCIIDOCTOR_EXECUTABLE NAMES asciidoctor)
option(SCAP_WORKBENCH_REBUILD_MANUAL "If enabled, user manual will be rebuilt (requires asciidoctor to be installed)" TRUE)
if (SCAP_WORKBENCH_REBUILD_MANUAL AND NOT ASCIIDOCTOR_EXECUTABLE)
    message("asciidoctor has not been found, user manual won't be rebuilt even though SCAP_WORKBENCH_REBUILD_MANUAL has been enabled.")
endif()
if (NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/doc/user_manual.html")
    if (NOT ASCIIDOCTOR_EXECUTABLE)
        message(FATAL_ERROR "You seem to be using scap-workbench from the repository ('doc/user_manual.html' hasn't been found). Please install asciidoctor to build the manual!")
    endif()
    set(SCAP_WORKBENCH_REBUILD_MANUAL TRUE)
endif()
# This is optional, only required if user wants to run cppcheck (unlikely)
find_program(CPPCHECK_EXECUTABLE NAMES cppcheck)

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
# It is not trivial to make the resulting file executable :-(
# People will have to `bash runwrapper.sh ...` in the meantime.
configure_file("runwrapper.sh.in" "${CMAKE_CURRENT_BINARY_DIR}/runwrapper.sh")
configure_file("scap-workbench-oscap.policy.in" "${CMAKE_CURRENT_BINARY_DIR}/scap-workbench-oscap.policy")

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

install(PROGRAMS "scap-workbench-oscap.sh"
    DESTINATION ${CMAKE_INSTALL_LIBEXECDIR})

install(PROGRAMS "scap-workbench-pkexec-oscap.sh"
    DESTINATION ${CMAKE_INSTALL_LIBEXECDIR})
    
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/scap-workbench-oscap.policy"
    DESTINATION "${CMAKE_INSTALL_DATADIR}/polkit-1/actions")

install(FILES "man/scap-workbench.8"
    DESTINATION "${CMAKE_INSTALL_MANDIR}/man8")

install(FILES "scap-workbench.desktop"
    DESTINATION "${CMAKE_INSTALL_DATADIR}/applications")
install(FILES "share/pixmaps/scap-workbench.png"
    DESTINATION "${CMAKE_INSTALL_DATADIR}/pixmaps")

if (ASCIIDOCTOR_EXECUTABLE)
    file(GLOB USER_MANUAL_SCREENSHOTS "${CMAKE_CURRENT_SOURCE_DIR}/doc/user_manual/*.png")
    add_custom_command(
        OUTPUT doc/user_manual.html
        COMMAND ${ASCIIDOCTOR_EXECUTABLE} --destination-dir ${CMAKE_CURRENT_BINARY_DIR}/doc -b html5 -a data-uri user_manual.adoc
        COMMAND ${CMAKE_COMMAND} -E copy ${CMAKE_CURRENT_BINARY_DIR}/doc/user_manual.html ${CMAKE_CURRENT_SOURCE_DIR}/doc/user_manual.html
        DEPENDS doc/user_manual.adoc ${USER_MANUAL_SCREENSHOTS}
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/doc
    )
    add_custom_target(
        "docs"
        DEPENDS doc/user_manual.html
    )
    if (SCAP_WORKBENCH_REBUILD_MANUAL)
        add_dependencies("scap-workbench" "docs")
    endif()
endif()

install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/doc/user_manual.html"
    DESTINATION ${CMAKE_INSTALL_DOCDIR})

if (CPPCHECK_EXECUTABLE)
    set(CPPCHECK_INCL_PARAMS -I /usr/include)
    foreach(DIR ${SCAP_WORKBENCH_INCLUDE_DIRS})
        set(CPPCHECK_INCL_PARAMS ${CPPCHECK_INCL_PARAMS} -I ${DIR})
    endforeach()

    add_custom_command(
        OUTPUT cppcheck.txt
        COMMAND ${CPPCHECK_EXECUTABLE} ${CPPCHECK_INCL_PARAMS} --enable=all --force ${scap_workbench_SOURCES} 2> ${CMAKE_CURRENT_BINARY_DIR}/cppcheck.txt
        DEPENDS ${scap_workbench_SOURCES} ${scap_workbench_HEADERS}
        VERBATIM
    )
    add_custom_target(
        cppcheck
        DEPENDS cppcheck.txt
    )
endif()

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
