cmake_minimum_required(VERSION 3.18)
project(imagegpt_core VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

option(IMGGPT_ENABLE_RAW "Enable LibRaw RAW decode support" ON)
option(IMGGPT_ENABLE_ICC "Enable LittleCMS2 ICC transforms" ON)

find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
find_package(pybind11 CONFIG REQUIRED)
find_package(OpenImageIO QUIET)

if(OpenImageIO_FOUND)
  message(STATUS "OpenImageIO found: ${OpenImageIO_VERSION}")
  set(IMGGPT_HAS_OIIO TRUE)
else()
  message(WARNING "OpenImageIO not found. Native engine image I/O will be unavailable.")
  set(IMGGPT_HAS_OIIO FALSE)
endif()

if(IMGGPT_ENABLE_RAW)
  find_path(LIBRAW_INCLUDE_DIR libraw/libraw.h)
  find_library(LIBRAW_LIBRARY NAMES raw_r raw libraw)
  if(LIBRAW_INCLUDE_DIR AND LIBRAW_LIBRARY)
    message(STATUS "LibRaw found: ${LIBRAW_LIBRARY}")
    set(IMGGPT_HAS_LIBRAW TRUE)
  else()
    message(WARNING "LibRaw not found. RAW support disabled in native core.")
    set(IMGGPT_HAS_LIBRAW FALSE)
  endif()
else()
  set(IMGGPT_HAS_LIBRAW FALSE)
endif()

if(IMGGPT_ENABLE_ICC)
  find_path(LCMS2_INCLUDE_DIR lcms2.h)
  find_library(LCMS2_LIBRARY NAMES lcms2 liblcms2)
  if(LCMS2_INCLUDE_DIR AND LCMS2_LIBRARY)
    message(STATUS "LittleCMS2 found: ${LCMS2_LIBRARY}")
    set(IMGGPT_HAS_LCMS2 TRUE)
  else()
    message(WARNING "LittleCMS2 not found. ICC transforms disabled in native core.")
    set(IMGGPT_HAS_LCMS2 FALSE)
  endif()
else()
  set(IMGGPT_HAS_LCMS2 FALSE)
endif()

pybind11_add_module(imagegpt_core MODULE
  src/bindings.cpp
  src/engine.cpp
  src/io.cpp
  src/pipeline.cpp
  src/raw.cpp
  src/color_management.cpp
)

target_include_directories(imagegpt_core PRIVATE
  ${PROJECT_SOURCE_DIR}/include
)

if(IMGGPT_HAS_OIIO)
  target_compile_definitions(imagegpt_core PRIVATE IMGGPT_HAS_OIIO=1)
  target_link_libraries(imagegpt_core PRIVATE OpenImageIO::OpenImageIO)
endif()

if(IMGGPT_HAS_LIBRAW)
  target_compile_definitions(imagegpt_core PRIVATE IMGGPT_HAS_LIBRAW=1)
  target_include_directories(imagegpt_core PRIVATE ${LIBRAW_INCLUDE_DIR})
  target_link_libraries(imagegpt_core PRIVATE ${LIBRAW_LIBRARY})
endif()

if(IMGGPT_HAS_LCMS2)
  target_compile_definitions(imagegpt_core PRIVATE IMGGPT_HAS_LCMS2=1)
  target_include_directories(imagegpt_core PRIVATE ${LCMS2_INCLUDE_DIR})
  target_link_libraries(imagegpt_core PRIVATE ${LCMS2_LIBRARY})
endif()

if(MSVC)
  target_compile_options(imagegpt_core PRIVATE /W4)
else()
  target_compile_options(imagegpt_core PRIVATE -Wall -Wextra -Wpedantic)
endif()

