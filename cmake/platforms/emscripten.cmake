# Emscripten specific settings

if(NOT EMSCRIPTEN)
    return()
endif()

set(CMAKE_EXECUTABLE_SUFFIX ".js")
set(CMAKE_SHARED_LIBRARY_SUFFIX ".wasm")

option(IOQ3_WEB_TEST_OBSERVER "Include read-only gameplay state for browser tests (not release)" OFF)

# Disable options that don't make sense for emscripten
set(BUILD_SERVER OFF CACHE INTERNAL "")
set(BUILD_RENDERER_GL1 OFF CACHE INTERNAL "")
set(USE_RENDERER_DLOPEN OFF CACHE INTERNAL "")
set(USE_OPENAL_DLOPEN OFF CACHE INTERNAL "")
set(BUILD_GAME_LIBRARIES OFF CACHE INTERNAL "")
set(USE_HTTP OFF CACHE INTERNAL "")

# Disable LTO since the libraries Emscripten provides aren't LTO enabled
set(CMAKE_INTERPROCEDURAL_OPTIMIZATION FALSE)

list(APPEND CLIENT_LINK_OPTIONS
    -sTOTAL_MEMORY=256MB
    -sSTACK_SIZE=5MB
    -sMIN_WEBGL_VERSION=2
    -sMAX_WEBGL_VERSION=2
    -sEXPORTED_RUNTIME_METHODS=FS,IDBFS,callMain
    -sEXPORTED_FUNCTIONS=_main,_OG_WebLoseFocus,_OG_WebResumeAudio
    -lidbfs.js
    -sEXIT_RUNTIME=1
    -sEXPORT_ES6
    -sEXPORT_NAME=${CLIENT_NAME}
)

# Production loads verified assets through game-manifest.json, keeping read-only
# packages separate from the persistent player home. Do not silently ignore a
# developer's old preload option.
if(EMSCRIPTEN_PRELOAD_FILE)
    message(FATAL_ERROR "Use code/web/make-manifest.mjs instead of EMSCRIPTEN_PRELOAD_FILE")
endif()

list(APPEND POST_CONFIGURE_FUNCTIONS deploy_shell_files)

function(deploy_shell_files)
    target_sources(${CLIENT_BINARY} PRIVATE ${SOURCE_DIR}/web/web_bridge.c)
    if(IOQ3_WEB_TEST_OBSERVER)
        target_sources(${CLIENT_BINARY} PRIVATE ${SOURCE_DIR}/client/cl_web_test.c)
        target_compile_definitions(${CLIENT_BINARY} PRIVATE IOQ3_WEB_TEST_OBSERVER=1)
    endif()
    configure_file(${SOURCE_DIR}/web/client.html.in
        ${CMAKE_BINARY_DIR}/${CMAKE_BUILD_TYPE}/engine.html @ONLY)
    configure_file(${SOURCE_DIR}/web/launcher.html.in
        ${CMAKE_BINARY_DIR}/${CMAKE_BUILD_TYPE}/index.html @ONLY)
    foreach(file host.mjs app.mjs menu.mjs hud.mjs lobby.mjs play.mjs shell.css launcher.mjs launcher.css lifecycle.mjs)
        configure_file(${SOURCE_DIR}/web/${file}
            ${CMAKE_BINARY_DIR}/${CMAKE_BUILD_TYPE}/${file} COPYONLY)
    endforeach()
    file(MAKE_DIRECTORY ${CMAKE_BINARY_DIR}/${CMAKE_BUILD_TYPE}/ui)
    configure_file(${CMAKE_SOURCE_DIR}/assets/remaster/ui/hangar.webp
        ${CMAKE_BINARY_DIR}/${CMAKE_BUILD_TYPE}/ui/hangar.webp COPYONLY)
    # Preserve a locally prepared manifest during incremental reconfiguration.
    if(NOT EXISTS ${CMAKE_BINARY_DIR}/${CMAKE_BUILD_TYPE}/game-manifest.json)
        configure_file(${SOURCE_DIR}/web/client-config.json
            ${CMAKE_BINARY_DIR}/${CMAKE_BUILD_TYPE}/game-manifest.json COPYONLY)
    endif()
endfunction()
