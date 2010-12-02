## Copyright (C) 2009, 2010 Aldebaran Robotics

get_filename_component(_ROOT_DIR ${CMAKE_CURRENT_LIST_FILE} PATH)
include("${_ROOT_DIR}/qtutils.cmake")

set(_suffix "QTGUI")
set(_libame "QtGui")

qt_flib(${_suffix} ${_libame})
export_lib(QT_${_suffix})
set(_ROOT_DIR)
