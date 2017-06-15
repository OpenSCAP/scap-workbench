cmake_minimum_required(VERSION 2.6)

project("scap-workbench")
set(SCAP_WORKBENCH_VERSION_MAJOR "1")
set(SCAP_WORKBENCH_VERSION_MINOR "1")
set(SCAP_WORKBENCH_VERSION_PATCH "5")
set(SCAP_WORKBENCH_VERSION "${SCAP_WORKBENCH_VERSION_MAJOR}.${SCAP_WORKBENCH_VERSION_MINOR}.${SCAP_WORKBENCH_VERSION_PATCH}")
set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_SOURCE_DIR}/cmake/")

include(GNUInstallDirs)

find_package(Qt4 REQUIRED QtCore QtGui QtXmlPatterns)
include(${QT_USE_FILE})

# This conditional is here to avoid checking openscap version if user supplies
# custom openscap parameters.
if (NOT DEFINED OPENSCAP_LIBRARIES OR NOT DEFINED OPENSCAP_INCLUDE_DIRS)
    include("${CMAKE_ROOT}/Modules/FindPkgConfig.cmake")
    pkg_check_modules(OPENSCAP REQUIRED libopenscap>=1.2.0)
endif()

# Gather info about openscap version
if (DEFINED OPENSCAP_VERSION)
    # pkg_check_modules() defines the string OPENSCAP_VERSION, lets use it
    string(REPLACE "." ";" OPENSCAP_VERSION_LIST ${OPENSCAP_VERSION})
    list(GET OPENSCAP_VERSION_LIST 0 OPENSCAP_VERSION_MAJOR)
    list(GET OPENSCAP_VERSION_LIST 1 OPENSCAP_VERSION_MINOR)
    list(GET OPENSCAP_VERSION_LIST 2 OPENSCAP_VERSION_PATCH)
else()
    # If OPENSCAP_VERSION is not defined, user has specified its own OpenSCAP library to use
    # So, zero out the version info as there is no easy way to know which version the library is
    set(OPENSCAP_VERSION "0.0.0")
    set(OPENSCAP_VERSION_MAJOR 0)
    set(OPENSCAP_VERSION_MINOR 0)
    set(OPENSCAP_VERSION_PATCH 0)
endif()

# Local scanning tools
option(SCAP_WORKBENCH_LOCAL_SCAN_ENABLED "If enabled, scanning of local machine is possible from workbench. Else the option is disabled in the GUI." TRUE)

find_program(NICE_EXECUTABLE NAMES nice) # fully optional, local scan still available when missing
if (NICE_EXECUTABLE)
    set(SCAP_WORKBENCH_LOCAL_NICE_FOUND 1)
endif()

# Remote scanning tools
find_program(SSH_EXECUTABLE NAMES ssh) # required for remote scan, if missing remote scan is not available
if (SSH_EXECUTABLE)
    set(SCAP_WORKBENCH_LOCAL_SSH_FOUND 1)
endif()
find_program(SETSID_EXECUTABLE NAMES setsid) # optional for remote scan, makes sure ssh always spawns GUI dialog
if (SETSID_EXECUTABLE)
    set(SCAP_WORKBENCH_LOCAL_SETSID_FOUND 1)
    execute_process(
        COMMAND ${SETSID_EXECUTABLE} --wait ${CMAKE_COMMAND} -E sleep 0
        ERROR_QUIET # suppress help message of setsid in case it doesn't support --wait
        RESULT_VARIABLE SETSID_EXECUTABLE_WAIT_EC
    )
    if (${SETSID_EXECUTABLE_WAIT_EC} EQUAL 0)
        set(SCAP_WORKBENCH_LOCAL_SETSID_SUPPORTS_WAIT 1)
    else()
        set(SCAP_WORKBENCH_LOCAL_SETSID_SUPPORTS_WAIT 0)
    endif()
endif()

# Save as RPM tools, optional but required for saving content as RPM
find_program(SCAP_AS_RPM_EXECUTABLE NAMES scap-as-rpm)
if (SCAP_AS_RPM_EXECUTABLE)
    set(SCAP_WORKBENCH_LOCAL_SCAP_AS_RPM_FOUND 1)
endif()

# This is optional, only required if user wants documentation rebuilt
find_program(ASCIIDOCTOR_EXECUTABLE NAMES asciidoctor)
option(SCAP_WORKBENCH_REBUILD_MANUAL "If enabled, user manual will be rebuilt (requires asciidoctor to be installed)" TRUE)
option(SCAP_WORKBENCH_USE_NATIVE_FILE_DIALOGS "If enabled, native desktop environment file dialogs are used (disable if you have crashes at startup)" TRUE)
if (SCAP_WORKBENCH_REBUILD_MANUAL AND NOT ASCIIDOCTOR_EXECUTABLE)
    message("asciidoctor has not been found, user manual won't be rebuilt even though SCAP_WORKBENCH_REBUILD_MANUAL has been enabled.")
endif()
if (NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/doc/user_manual.html")
    if (NOT ASCIIDOCTOR_EXECUTABLE)
        message(FATAL_ERROR "You seem to be using scap-workbench from the repository ('${CMAKE_SOURCE_DIR}/doc/user_manual.html' hasn't been found). Please install asciidoctor to build the manual! You can use `gem install asciidoctor` if asciidoctor is not in your distribution package repository. If you don't have access to asciidoctor and don't mind not having a manual, run `touch ${CMAKE_SOURCE_DIR}/doc/user_manual.html` and rerun cmake.")
    endif()
    set(SCAP_WORKBENCH_REBUILD_MANUAL TRUE)
endif()
# This is optional, only required if user wants to run cppcheck (unlikely)
find_program(CPPCHECK_EXECUTABLE NAMES cppcheck)

set(SCAP_WORKBENCH_SSG_DIRECTORY "/usr/share/xml/scap/ssg/content" CACHE FILEPATH
    "Path to the base scap-security-guide directory. The directory where 'fedora', 'rhel6', 'rhel7', ... reside.")
set(SCAP_WORKBENCH_SCAP_CONTENT_DIRECTORY "/usr/share/xml/scap" CACHE PATH
    "Directory where SCAP content is *usually* stored. This is the default directory when opening a file via file open dialog.")

file(GLOB scap_workbench_HEADERS "${CMAKE_SOURCE_DIR}/include/*.h")
qt4_wrap_cpp(scap_workbench_HEADERS_MOC ${scap_workbench_HEADERS})

file(GLOB scap_workbench_UIS "${CMAKE_SOURCE_DIR}/ui/*.ui")
qt4_wrap_ui(scap_workbench_UIS_HEADERS ${scap_workbench_UIS})

file(GLOB scap_workbench_SOURCES "${CMAKE_SOURCE_DIR}/src/*.cpp")

set(SCAP_WORKBENCH_INCLUDE_DIRS
    ${CMAKE_CURRENT_SOURCE_DIR}/include ${CMAKE_CURRENT_BINARY_DIR}
    # Qt4 is handled by ${QT_USE_FILE} above
    ${OPENSCAP_INCLUDE_DIRS})

set(SCAP_WORKBENCH_LINK_LIBRARIES
    ${QT_LIBRARIES}
    ${OPENSCAP_LIBRARIES})

configure_file("include/Config.h.in" "${CMAKE_CURRENT_BINARY_DIR}/Config.h")
# It is not trivial to make the resulting file executable :-(
# People will have to `bash runwrapper.sh ...` in the meantime.
configure_file("runwrapper.sh.in" "${CMAKE_CURRENT_BINARY_DIR}/runwrapper.sh")
configure_file("scap-workbench-oscap.policy.in" "${CMAKE_CURRENT_BINARY_DIR}/scap-workbench-oscap.policy")
if (WIN32)
    configure_file("win32-resource.rc.in" "${CMAKE_CURRENT_BINARY_DIR}/win32-resource.rc")
    configure_file("scap-workbench.wxs.in" "${CMAKE_CURRENT_BINARY_DIR}/scap-workbench.wxs")
endif()

include_directories(${SCAP_WORKBENCH_INCLUDE_DIRS})

# Which languages we want generated
#set(scap_workbench_LANGUAGES de_DE fr_FR)
set(scap_workbench_LANGUAGES)
set(scap_workbench_LANGUAGE_TS_FILES)

foreach(LANGUAGE ${scap_workbench_LANGUAGES})
    set(TS_FILE "${CMAKE_CURRENT_SOURCE_DIR}/i18n/${LANGUAGE}.ts")
    set(scap_workbench_LANGUAGE_TS_FILES ${scap_workbench_LANGUAGE_TS_FILES} ${TS_FILE})
    set_source_files_properties(${TS_FILE} PROPERTIES OUTPUT_LOCATION "${CMAKE_CURRENT_BINARY_DIR}/i18n")
endforeach()

if (scap_workbench_LANGUAGE_TS_FILES)
    set(TRANSLATION_SOURCES ${scap_workbench_HEADERS} ${scap_workbench_SOURCES} ${scap_workbench_UIS_HEADERS})
    qt4_create_translation(qm_files ${TRANSLATION_SOURCES} ${scap_workbench_LANGUAGE_TS_FILES})
endif()

if (APPLE)
    set(scap_workbench_SOURCES ${scap_workbench_SOURCES} AppIcon.icns)
    set_source_files_properties(AppIcon.icns PROPERTIES MACOSX_PACKAGE_LOCATION Resources)
endif()
if (WIN32)
    set(scap_workbench_SOURCES ${scap_workbench_SOURCES} ${CMAKE_BINARY_DIR}/win32-resource.rc)
endif()

add_executable("scap-workbench" MACOSX_BUNDLE
    ${scap_workbench_HEADERS}
    ${scap_workbench_SOURCES}

    ${scap_workbench_HEADERS_MOC}
    ${scap_workbench_UIS_HEADERS}
    ${scap_workbench_LANGUAGE_TS_FILES}
)

set_target_properties("scap-workbench" PROPERTIES MACOSX_BUNDLE_INFO_PLIST MacOSXBundleInfo.plist.in)
set(MACOSX_BUNDLE_BUNDLE_NAME "SCAP Workbench")
set(MACOSX_BUNDLE_BUNDLE_VERSION "${SCAP_WORKBENCH_VERSION}")
set(MACOSX_BUNDLE_LONG_VERSION_STRING "${SCAP_WORKBENCH_VERSION}")
set(MACOSX_BUNDLE_SHORT_VERSION_STRING "${SCAP_WORKBENCH_VERSION}")
set(MACOSX_BUNDLE_COPYRIGHT "Copyright (c) 2015 Red Hat, Inc.")
set(MACOSX_BUNDLE_GUI_IDENTIFIER "org.open-scap.scap-workbench")
set(MACOSX_BUNDLE_ICON_FILE AppIcon)

target_link_libraries("scap-workbench" ${SCAP_WORKBENCH_LINK_LIBRARIES})

if (APPLE)
    if (SETSID_EXECUTABLE)
        add_custom_command(TARGET "scap-workbench" POST_BUILD
            COMMAND cp "${SETSID_EXECUTABLE}" "scap-workbench.app/Contents/MacOS/"
            COMMENT "Copying ${SETSID_EXECUTABLE} to application bundle")
    endif()

    add_custom_command(TARGET "scap-workbench" POST_BUILD
        COMMAND cp "${CMAKE_SOURCE_DIR}/scap-workbench-osx-ssh-askpass.sh" "scap-workbench.app/Contents/MacOS/"
        COMMENT "Copying scap-workbench-osx-ssh-askpass.sh to application bundle")

    add_custom_command(TARGET "scap-workbench" POST_BUILD
        COMMAND cp -r "${CMAKE_SOURCE_DIR}/share" "scap-workbench.app/Contents/Resources/"
        COMMENT "Copying the share folder to application bundle")

    add_custom_command(TARGET "scap-workbench" POST_BUILD
        COMMAND cp -r "${CMAKE_SOURCE_DIR}/doc" "scap-workbench.app/Contents/Resources/"
        COMMENT "Copying the doc folder to application bundle")

    configure_file("osx-create-dmg.sh.in" "${CMAKE_CURRENT_BINARY_DIR}/osx-create-dmg.sh" @ONLY)
endif()

if (WIN32)
    add_custom_command(TARGET "scap-workbench" POST_BUILD
        COMMAND mkdir -p "scap-workbench/"
        COMMENT "Creating the application folder")
    add_custom_command(TARGET "scap-workbench" POST_BUILD
        COMMAND cp "scap-workbench.exe" "scap-workbench/"
        COMMENT "Copying scap-workbench.exe to application folder")

    add_custom_command(TARGET "scap-workbench" POST_BUILD
        COMMAND cp -r "${CMAKE_SOURCE_DIR}/share" "scap-workbench/"
        COMMENT "Copying the share folder to application folder")

    add_custom_command(TARGET "scap-workbench" POST_BUILD
        COMMAND cp -r "${CMAKE_SOURCE_DIR}/doc" "scap-workbench/"
        COMMENT "Copying the doc folder to application folder")
endif()

install(TARGETS "scap-workbench"
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    BUNDLE DESTINATION .
)

install(PROGRAMS "scap-workbench-oscap.sh"
    DESTINATION ${CMAKE_INSTALL_LIBEXECDIR})

install(PROGRAMS "scap-workbench-pkexec-oscap.sh"
    DESTINATION ${CMAKE_INSTALL_LIBEXECDIR})

install(PROGRAMS "scap-workbench-rpm-extract.sh"
    DESTINATION ${CMAKE_INSTALL_LIBEXECDIR})

if (APPLE)
    install(PROGRAMS "scap-workbench-osx-ssh-askpass.sh"
        DESTINATION ${CMAKE_INSTALL_LIBEXECDIR})
endif()

install(FILES "${CMAKE_CURRENT_BINARY_DIR}/scap-workbench-oscap.policy"
    DESTINATION "${CMAKE_INSTALL_DATADIR}/polkit-1/actions")

install(FILES "man/scap-workbench.8"
    DESTINATION "${CMAKE_INSTALL_MANDIR}/man8")

install(DIRECTORY "share/scap-workbench"
    DESTINATION "${CMAKE_INSTALL_DATADIR}")
install(FILES "scap-workbench.desktop"
    DESTINATION "${CMAKE_INSTALL_DATADIR}/applications")
install(FILES "share/pixmaps/scap-workbench.png"
    DESTINATION "${CMAKE_INSTALL_DATADIR}/pixmaps")
install(FILES "share/pixmaps/scap-workbench.svg"
    DESTINATION "${CMAKE_INSTALL_DATADIR}/pixmaps")
install(FILES "scap-workbench.appdata.xml"
    DESTINATION "${CMAKE_INSTALL_DATADIR}/appdata")

if (ASCIIDOCTOR_EXECUTABLE)
    file(GLOB USER_MANUAL_SCREENSHOTS "${CMAKE_CURRENT_SOURCE_DIR}/doc/user_manual/*.png")
    add_custom_command(
        OUTPUT doc/user_manual.html
        COMMAND ${CMAKE_COMMAND} -E make_directory ${CMAKE_CURRENT_BINARY_DIR}/doc
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

install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/COPYING"
    DESTINATION ${CMAKE_INSTALL_DOCDIR})

install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/README.md"
    DESTINATION ${CMAKE_INSTALL_DOCDIR})

if (CPPCHECK_EXECUTABLE)
    set(CPPCHECK_INCL_PARAMS -I /usr/include)
    foreach(DIR ${SCAP_WORKBENCH_INCLUDE_DIRS})
        set(CPPCHECK_INCL_PARAMS ${CPPCHECK_INCL_PARAMS} -I ${DIR})
    endforeach()

    add_custom_command(
        OUTPUT cppcheck.txt
        COMMAND ${CPPCHECK_EXECUTABLE} ${CPPCHECK_INCL_PARAMS} --language=c++ --std=c++03 --library=std,qt --enable=all --force --suppress=*:/usr/include/Qt*/* ${scap_workbench_SOURCES} 2> ${CMAKE_CURRENT_BINARY_DIR}/cppcheck.txt
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

"\\\\CMakeLists.txt.user"
)
include(CPack)
