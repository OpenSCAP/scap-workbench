cmake_minimum_required(VERSION 2.8)

project(scap_workbench)
set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_SOURCE_DIR}/cmake/")

find_package(Qt4 REQUIRED)
find_package(OpenSCAP REQUIRED)

file(GLOB scap_workbench_HEADERS "${CMAKE_SOURCE_DIR}/include/*.h")
qt4_wrap_cpp(scap_workbench_HEADERS_MOC ${scap_workbench_HEADERS})

file(GLOB scap_workbench_UIS "${CMAKE_SOURCE_DIR}/ui/*.ui")
qt4_wrap_ui(scap_workbench_UIS_HEADERS ${scap_workbench_UIS})

file(GLOB scap_workbench_SOURCES "${CMAKE_SOURCE_DIR}/src/*.cpp")

add_executable(scap_workbench
    ${scap_workbench_HEADERS}
    ${scap_workbench_SOURCES}

    ${scap_workbench_HEADERS_MOC}
    ${scap_workbench_UIS_HEADERS}
)

target_link_libraries(scap_workbench
    ${QT_QTCORE_LIBRARY} ${QT_QTGUI_LIBRARY} ${QT_QTWEBKIT_LIBRARY}
    ${LIBOPENSCAP_LIBRARY})

include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include ${CMAKE_CURRENT_BINARY_DIR}
    ${QT_QTCORE_INCLUDE_DIR} ${QT_QTGUI_INCLUDE_DIR} ${QT_QTWEBKIT_INCLUDE_DIR}
    ${LIBOPENSCAP_INCLUDE_DIR}
)
