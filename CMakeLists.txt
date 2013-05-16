cmake_minimum_required(VERSION 2.8)

include(GNUInstallDirs)

project(scap_workbench)
set(SCAP_WORKBENCH_VERSION_MAJOR "0")
set(SCAP_WORKBENCH_VERSION_MINOR "8")
set(SCAP_WORKBENCH_VERSION_PATCH "0")
set(SCAP_WORKBENCH_SHORT_VERSION "${SCAP_WORKBENCH_VERSION_MAJOR}.${SCAP_WORKBENCH_VERSION_MINOR}.${SCAP_WORKBENCH_VERSION_PATCH}")

set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_SOURCE_DIR}/cmake/")

find_package(Qt4 REQUIRED)
find_package(OpenSCAP REQUIRED)

file(GLOB scap_workbench_HEADERS "${CMAKE_SOURCE_DIR}/include/*.h")
qt4_wrap_cpp(scap_workbench_HEADERS_MOC ${scap_workbench_HEADERS})

file(GLOB scap_workbench_UIS "${CMAKE_SOURCE_DIR}/ui/*.ui")
qt4_wrap_ui(scap_workbench_UIS_HEADERS ${scap_workbench_UIS})

file(GLOB scap_workbench_SOURCES "${CMAKE_SOURCE_DIR}/src/*.cpp")

include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include ${CMAKE_CURRENT_BINARY_DIR}
    ${QT_QTCORE_INCLUDE_DIR} ${QT_QTGUI_INCLUDE_DIR} ${QT_QTWEBKIT_INCLUDE_DIR}
    ${LIBOPENSCAP_INCLUDE_DIR}
)

add_executable(scap_workbench
    ${scap_workbench_HEADERS}
    ${scap_workbench_SOURCES}

    ${scap_workbench_HEADERS_MOC}
    ${scap_workbench_UIS_HEADERS}
)

target_link_libraries(scap_workbench
    ${QT_QTCORE_LIBRARY} ${QT_QTGUI_LIBRARY} ${QT_QTWEBKIT_LIBRARY}
    ${LIBOPENSCAP_LIBRARY})

install(TARGETS scap_workbench
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})

install(FILES man/scap_workbench.8
    DESTINATION ${CMAKE_INSTALL_MANDIR}/man8)

install(FILES share/pixmaps/scap_workbench.png
    DESTINATION ${CMAKE_INSTALL_DATADIR}/pixmaps)

# only CPack should follow
set(CPACK_CMAKE_GENERATOR "Unix Makefiles")
set(CPACK_SOURCE_GENERATOR "TBZ2")
set(CPACK_SOURCE_PACKAGE_FILE_NAME "scap_workbench-${SCAP_WORKBENCH_SHORT_VERSION}" CACHE INTERNAL "tarball basename")
set(CPACK_SOURCE_IGNORE_FILES
"\\\\.git.*"

"build/"
"~$"
)
include(CPack)
