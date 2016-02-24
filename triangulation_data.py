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

from PyQt4.QtCore import QDateTime
from math import *
#from datetime import datetime


def dadd(dictionary,key,value):
  """add a value to a dictionary; create key if not exists """
  if dictionary.has_key(key):
    dictionary[key] += value
  else:
    dictionary[key] = value



def bearing2rad(bearing):
  if bearing < 0 or bearing > 360:
    return None
  if bearing < 90:
    return (90 - bearing) * (pi/180)
  else:
    return (90 - bearing) * (pi/180) + 2 * pi



def triang(fix1, fix2):
  x1 = fix1[0]
  y1 = fix1[1]
  x2 = fix2[0]
  y2 = fix2[1]
  bearing1 = fix1[2]
  bearing2 = fix2[2]
  beta1 = bearing2rad(bearing1)
  beta2 = bearing2rad(bearing2)
  # aren't the bearings parallel? (+- pi/90)
#  if (abs(beta1 - beta2) < pi/90) or (abs(abs(beta1 - beta2) - pi) < pi/90):
  if beta1 == beta2:
    return (-999,-999)
  # do it now!
  x = (x1 * tan(beta1) - x2 * tan(beta2) + y2 - y1) / (tan(beta1) - tan(beta2))
  y = ((x2 - x1) * tan(beta1) * tan(beta2) - y2 * tan(beta1) + y1 * tan(beta2)) / (tan(beta2) - tan(beta1))
  # test if the bearings are convergent!
  if   x>=x1 and y>y1 : ok1 = (bearing1 < 90)                    #the intersection is for NE from the point 1
  elif x>x1  and y<=y1: ok1 = (bearing1 >= 90 and bearing1 < 180)  #the intersection is for SE from the point 1
  elif x<=x1 and y<y1 : ok1 = (bearing1 >= 180 and bearing1 < 270) #the intersection is for SW from the point 1
  else:                 ok1 = (bearing1 >= 270)                  #the intersection is for NW from the point 1
  if   x>=x2 and y>y2 : ok2 = (bearing2 < 90)                    #the intersection is for NE from the point 2
  elif x>x2  and y<=y2: ok2 = (bearing2 >= 90 and bearing2 < 180)  #the intersection is for SE from the point 2
  elif x<=x2 and y<y2 : ok2 = (bearing2 >= 180 and bearing2 < 270) #the intersection is for SW from the point 2
  else:                 ok2 = (bearing2 >= 270)                  #the intersection is for NW from the point 2
  if ok1 and ok2:
    return(x,y)
  else:
    return (-999,-999)



def parseDateTime(s):
  #QDateTime.fromString('2000-01-03 02:5','yyyy-M-d h:m')
  #allowed order: yyy-M-d or M-d-y
  #allowed date separator: / - .
  #allowed main separator: T or space
  if not s:
    return None
  if type(s) is QDateTime:
    return s
  s = s.strip()
  if '-' in s: dsep = '-'
  elif '/' in s: dsep = '/'
  elif '.' in s: dsep = '.'
  else: return None
  tsep = ':'
  if 'T' in s: sep = 'T'
  elif ' ' in s: sep = ' '
  else: return None
  try:
    if int(s[0:4]) in range(1800,2100):
      #year first
      dformat = 'yyyy%sM%sd%sh%sm' % (dsep, dsep, sep, tsep)
    else:
      #strange data...
      return None
  except:
    # the year isn't first - let's assume it's the month then
    dformat = 'M%sd%syyyy%sh%sm' % (dsep, dsep, sep, tsep)
  d = QDateTime.fromString(s, dformat)
  if d<1000:
    return None
  return d
