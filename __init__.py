# -*- coding: utf-8 -*-
########################################################
#                                         __init__.py  #
########################################################
#    AniMove project
#    Triangulation plugin
#    Quantum GIS plugin for telemetry trangulation
#    Copyright (C) 2010-2014 Borys Jurgiel for Faunalia and University of Evora
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

def classFactory(iface):
  from triangulation_plugin import Triangulation
  return Triangulation(iface)
