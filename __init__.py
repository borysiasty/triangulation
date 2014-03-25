# -*- coding: utf-8 -*-
########################################################
#                                         __init__.py  #
########################################################
#    AniMove project
#    Triangulation plugin
#    Quantum GIS plugin for telemetry trangulation
#    Copyright (C) 2010-2011 Borys Jurgiel for Faunalia and University of Evora
#    email: info@borysjurgiel.pl
########################################################
# 
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    A copy of the GNU General Public License is available at 
#    http://www.gnu.org/licenses/gpl.txt, or can be requested to the Free
#    Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
#    Boston, MA 02110-1301 USA.
#
########################################################

def name():
  return 'Triangulation'

def description():
  return 'AniMove: Triangulation of telemetry bearings'

def version():
  return 'Version 0.1.5'

def qgisMinimumVersion():
  return '1.5'

def authorName():
  return 'Borys Jurgiel for Faunalia and University of Evora'

def icon():
  return "icons/triangulationIcon.png"

def homepage():
  return 'http://www.faunalia.it/animove'

def classFactory(iface):
  from triangulation_plugin import Triangulation
  return Triangulation(iface)
