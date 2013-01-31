cmake_minimum_required(VERSION 2.8)

project(scap_workbench)

find_package(Qt4 REQUIRED)

file(GLOB scap_workbench_HEADERS "include/*.h")
qt4_wrap_cpp(scap_workbench_HEADERS_MOC ${scap_workbench_HEADERS})

file(GLOB scap_workbench_UIS "ui/*.ui")
qt4_wrap_ui(scap_workbench_UIS_HEADERS ${scap_workbench_UIS})

file(GLOB scap_workbench_SOURCES "src/*.cpp")

add_executable(scap_workbench
    ${scap_workbench_SOURCES}

    ${scap_workbench_HEADERS_MOC}
    ${scap_workbench_UIS_HEADERS}
)
#set_target_properties(scap_workbench PROPERTIES LINKER_LANGUAGE CXX)
# TODO: Find openscap as part of the configuration step
target_link_libraries(scap_workbench ${QT_QTCORE_LIBRARY} ${QT_QTGUI_LIBRARY} /usr/lib/libopenscap.so)
# TODO: Find openscap as part of the configuration step
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include ${CMAKE_CURRENT_BINARY_DIR} ${QT_QTCORE_INCLUDE_DIR} ${QT_QTGUI_INCLUDE_DIR} "/usr/include/openscap")
