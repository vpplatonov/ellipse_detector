cmake_minimum_required(VERSION 3.17)
project(ellipse_detector)

set(CMAKE_CXX_STANDARD 14)

# OpenCV 3.4.11
SET(OpenCV_DIR /usr/local/share/OpenCV)

include_directories(src)

find_package( OpenCV REQUIRED )
include_directories( ${OpenCV_INCLUDE_DIRS})

add_executable(ellipse_detector ellipse_detector.cpp
        src/CNEllipseDetector.cpp
        src/CNEllipseDetector.h
        src/common.cpp
        src/common.h
        include/dirent.h
        src/stdafx.h
        src/tools.cpp
        src/tools.h)

target_link_libraries( ellipse_detector ${OpenCV_LIBS} )
