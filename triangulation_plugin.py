# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
#
# Triangulation
# Copyright (C) 2010-2011 Borys Jurgiel for Faunalia and University of Evora
#
#----------------------------------------------------------------------------
#
# licensed under the terms of GNU GPL 2
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#----------------------------------------------------------------------------

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
from qgis.utils import plugins

from triangulation_gui import *

import resources_rc


class Triangulation:

  def __init__(self, iface):
    self.iface = iface


  def initGui(self):
    # create action
    self.action = QAction(QIcon(':/plugins/triangulation/icons/triangulationIcon.png'), 'Triangulation', self.iface.mainWindow())
    self.action.setWhatsThis('AniMove: Triangulation')
    QObject.connect(self.action, SIGNAL('triggered()'), self.run)
    self.iface.addPluginToMenu('&AniMove', self.action)
    self.toolBar = self.iface.mainWindow().findChild(QObject, 'AniMoveToolBar')
    if not self.toolBar:
      self.toolBar = self.iface.addToolBar("AniMove")
      self.toolBar.setObjectName('AniMoveToolBar')
    self.toolBar.addAction(self.action)


  def unload(self):
    self.iface.removePluginMenu('&AniMove',self.action)
    self.toolBar.removeAction(self.action)
    if not self.toolBar.actions():
      del self.toolBar


  def run(self):
    dialog = TriangulationDialog(self.iface)
    dialog.exec_()
