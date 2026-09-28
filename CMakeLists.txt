# Plugin build (the core's AC_PLUGIN_SOURCE_DIRS). A static module build (modules/mod-lonelyice-waystones) does not
# use this file.
file(GLOB_RECURSE WAYSTONES_SOURCES CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp" "${CMAKE_CURRENT_SOURCE_DIR}/src/*.h")
AddPlugin(mod-lonelyice-waystones SOURCES ${WAYSTONES_SOURCES} plugin/plugin.cpp)
