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
from PyQt4.QtXml import QDomDocument
from qgis.core import *
from qgis.gui import *

from triangulationbase_ui import Ui_TriangulationDialog

from triangulation_data import *

import os
from math import *

#----------------------------------------------------------------------------

class TriangulationDialog(QDialog, Ui_TriangulationDialog):
  def __init__(self, iface):
    QDialog.__init__(self)
    self.iface = iface
    self.setupUi(self)
    self.nfields = None
    self.dfields = None # string fields with datetime
    self.fieldIndexes = None
    self.cmbXField.setEnabled(False)
    self.cmbYField.setEnabled(False)
    #hide X,Y controls for now
    self.cmbXField.hide()
    self.cmbYField.hide()
    self.label.hide()
    self.label_9.hide()
    QObject.connect(self.ckbAddPointsToCanvas, SIGNAL("toggled ( bool )"), self.outputModeChanged)
    QObject.connect(self.ckbSavePoints, SIGNAL("toggled ( bool )"), self.outputModeChanged)
    QObject.connect(self.ckbAddPolygonsToCanvas, SIGNAL("toggled ( bool )"), self.outputModeChanged)
    QObject.connect(self.ckbSavePolygons, SIGNAL("toggled ( bool )"), self.outputModeChanged)
    QObject.connect(self.cmbInLayer, SIGNAL("currentIndexChanged ( int )"), self.inputLayerChanged)
    QObject.connect(self.butAbout, SIGNAL("released ()"), self.about)
    QObject.connect(self.butPointFileName, SIGNAL("released ()"), self.setPointFileName)
    QObject.connect(self.butPolygonFileName, SIGNAL("released ()"), self.setPolygonFileName)
   
    # restore last settings
    settings = QSettings()
    self.lastFixIdField = settings.value('/AniMove/triangulation/fixIdField', QVariant('id')).toString()
    self.lastBearingField = settings.value('/AniMove/triangulation/bearingField', QVariant('bearing')).toString()
    self.lastDateTimeField = settings.value('/AniMove/triangulation/datetimeField', QVariant('datetime')).toString()
    self.lastOutputPointDir = settings.value('/AniMove/triangulation/outputPointDir', QVariant('.')).toString()
    self.lastOutputPolygonDir = settings.value('/AniMove/triangulation/outputPolygonDir', QVariant('.')).toString()
    self.lastXField = settings.value('/AniMove/triangulation/xField', QVariant('x')).toString()
    self.lastYField = settings.value('/AniMove/triangulation/yField', QVariant('y')).toString()
    self.ckbDiscardDivergent.setChecked( settings.value('/AniMove/triangulation/discardDivergent', QVariant(False)).toBool() )
    self.ckbDiscardTooBigAreas.setChecked( settings.value('/AniMove/triangulation/discardTooBigAreas', QVariant(False)).toBool() )
    self.sbAreaThreshold.setValue( settings.value('/AniMove/triangulation/areaThreshold', QVariant(10000)).toInt()[0] )    
    self.ckbShowSummary.setChecked( settings.value('/AniMove/triangulation/showSummary', QVariant(False)).toBool() )
    self.ckbShowLines.setChecked( settings.value('/AniMove/triangulation/showLines', QVariant(False)).toBool() )
    self.ckbAddPointsToCanvas.setChecked( settings.value('/AniMove/triangulation/addPointsToCanvas', QVariant(True)).toBool() )
    self.ckbSavePoints.setChecked( settings.value('/AniMove/triangulation/savePoints', QVariant(False)).toBool() )
    self.ckbAddPolygonsToCanvas.setChecked( settings.value('/AniMove/triangulation/AddPolygonsToCanvas', QVariant(True)).toBool() )
    self.ckbSavePolygons.setChecked( settings.value('/AniMove/triangulation/savePolygons', QVariant(False)).toBool() )
    self.outputPointDir = settings.value('/AniMove/triangulation/outputPointDir', QVariant('.')).toString()
    self.outputPolygonDir = settings.value('/AniMove/triangulation/outputPolygonDir', QVariant('.')).toString()
    self.outputEncoding = settings.value('/AniMove/triangulation/outputEncoding', QVariant('UTF-8')).toString()
    self.outputFilter = settings.value('/AniMove/triangulation/outputFilter', QVariant('[OGR] Geography Markup Language (*.gml *.GML)')).toString()

    # fill the input layer combobox and set to current layer if valid
    self.layers=[]
    indx=0
    for layer in self.iface.mapCanvas().layers():
      if layer.type() == layer.VectorLayer and layer.geometryType() == QGis.Point:
        self.layers+=[layer]
        self.cmbInLayer.addItem(layer.name())
        if layer == self.iface.mapCanvas().currentLayer():
          indx = self.cmbInLayer.count() - 1
    self.cmbInLayer.setCurrentIndex(indx)
    if not indx:
      self.inputLayerChanged(indx) # force reloading comboboxes if indx=0


  def accept(self):
    #validate
    if not self.cmbInLayer.count():
      QMessageBox.warning(self,'AniMove Triangulation','No data no fun...\nPlease select a point layer containing all the required fields: fix id and the bearing.')
      return
    if not self.cmbFixIdField.count() or not self.cmbBearingField.count() or not self.cmbXField.count() or not self.cmbYField.count():
      QMessageBox.warning(self,'AniMove Triangulation','Please select required fields: id and bearing')
      return
    if self.cmbFixIdField.currentText() == self.cmbBearingField.currentText():
      QMessageBox.warning(self,'AniMove Triangulation','Please select correct fields: id and bearing')
      return
    if not self.ckbShowSummary.isChecked() and not self.ckbSavePoints.isChecked() and not self.ckbAddPointsToCanvas.isChecked() and not self.ckbSavePolygons.isChecked() and not self.ckbAddPolygonsToCanvas.isChecked() and not self.ckbShowLines.isChecked():
      QMessageBox.warning(self,'AniMove Triangulation','Is there any sense in running the process while all the output channels are disabled? Please enable anything! :)')
      return
    if self.ckbSavePoints.isChecked() and not self.driverName(self.linePointFileName.text()):
      return
    if self.ckbSavePolygons.isChecked() and not self.driverName(self.linePolygonFileName.text()):
      return
      
    if self.iface.mapCanvas().hasCrsTransformEnabled():
      # get crs from the projct
      self.crs = self.iface.mapCanvas().mapRenderer().destinationSrs()
      if self.crs.mapUnits() == 1: 
        # feets
        QMessageBox.warning(self,'AniMove Triangulation','Current project distance units are feet, while the Triangulation plugins works with meters only. Please choose a metric coordinate reference system.')
        return
      if self.crs.mapUnits() > 1: 
        # degrees
        QMessageBox.warning(self,'AniMove Triangulation','Current project works with geographic coordinate reference system. Please switch to a projected CRS.')
        return
    else:
      # get crs from the source layer
      self.crs = self.layer.crs()
      if self.crs.mapUnits() == 1: 
        # feets
        QMessageBox.warning(self,'AniMove Triangulation','The source layer units are feet, while the Triangulation plugins works with meters only. Please enable On-The-Fly Reprojection and switch to any metric system.')
        return
      if self.crs.mapUnits() > 1: 
        # degrees
        QMessageBox.warning(self,'AniMove Triangulation','The source layer units are reported as degrees. If they are meters, please adjust the layer CRS declaration. If the layer really uses unprojected CRS, please enable On-The-Fly Reprojection and switch to a projected CRS.')
        return
      
    # save QSettings
    settings = QSettings()
    settings.setValue('/AniMove/triangulation/fixIdField', QVariant(self.cmbFixIdField.currentText()))
    settings.setValue('/AniMove/triangulation/bearingField', QVariant(self.cmbBearingField.currentText()))
    settings.setValue('/AniMove/triangulation/datetimeField', QVariant(self.cmbDateTimeField.currentText()))
    settings.setValue('/AniMove/triangulation/xField', QVariant(self.cmbXField.currentText()))
    settings.setValue('/AniMove/triangulation/yField', QVariant(self.cmbYField.currentText()))
    settings.setValue('/AniMove/triangulation/discardDivergent', QVariant(self.ckbDiscardDivergent.isChecked()))
    settings.setValue('/AniMove/triangulation/discardTooBigAreas', QVariant(self.ckbDiscardTooBigAreas.isChecked()))
    settings.setValue('/AniMove/triangulation/areaThreshold', QVariant(self.sbAreaThreshold.value()))
    settings.setValue('/AniMove/triangulation/showSummary', QVariant(self.ckbShowSummary.isChecked()))
    settings.setValue('/AniMove/triangulation/showLines', QVariant(self.ckbShowLines.isChecked()))
    settings.setValue('/AniMove/triangulation/addPointsToCanvas', QVariant(self.ckbAddPointsToCanvas.isChecked()))
    settings.setValue('/AniMove/triangulation/savePoints', QVariant(self.ckbSavePoints.isChecked()))
    settings.setValue('/AniMove/triangulation/AddPolygonsToCanvas', QVariant(self.ckbAddPolygonsToCanvas.isChecked()))
    settings.setValue('/AniMove/triangulation/savePolygons', QVariant(self.ckbSavePolygons.isChecked()))
    settings.setValue('/AniMove/triangulation/outputPointDir', QVariant(self.outputPointDir))
    settings.setValue('/AniMove/triangulation/outputPolygonDir', QVariant(self.outputPolygonDir))
    settings.setValue('/AniMove/triangulation/outputEncoding', QVariant(self.outputEncoding))
    settings.setValue('/AniMove/triangulation/outputFilter', QVariant(self.outputFilter))
    # set field indexes
    self.fieldIndexes = {'id': self.nfields[self.cmbFixIdField.currentIndex()],
      'bearing': self.nfields[self.cmbBearingField.currentIndex()],
      'datetime': -1,
      'x': self.nfields[self.cmbXField.currentIndex()],
      'y': self.nfields[self.cmbYField.currentIndex()]}
    if self.cmbDateTimeField.currentIndex() >=0:
      self.fieldIndexes['datetime'] = self.dfields[self.cmbDateTimeField.currentIndex()]

    # perform real work
    self.doProcess()
    # close the dialog
    QDialog.accept(self)
    
    if self.ckbShowSummary.isChecked():
      summary = "<b>Input:</b><br/>"
      summary+= "<b>%d</b> unique subsets (fix identifiers)<br/>" % stats['total subsets']
      summary+= "<b>%d</b> total bearings<br/>" % stats['total bearings']
      summary+= "<br/><b>Data errors:</b><br/>"
      if not sum(errors.values()):
        summary+="no errors found<br/>"
      if errors['invalid bearings']:
        summary+= "<b>%d</b> bearings discarded due to invalid values<br/>" % errors['invalid bearings']
      if errors['too less bearings']:
        summary+= "<b>%d</b> subsets discarded due to insufficent number of valid bearings<br/>" % errors['too less bearings']
      if errors['divergent bearings']:
        summary+= "<b>%d</b> pairs of bearings divergent<br/>" % errors['divergent bearings']
      if errors['locations discarded because of divergency']:
        summary+= "<b>%d</b> subsets discarded due to divergent bearings<br/>" % errors['locations discarded because of divergency']
      if errors['too big areas']:
        summary+= "<b>%d</b> subsets discarded due to too big polygon area<br/>" % errors['too big areas']
      summary+= "<br/><b>Output:</b><br/>"
      summary+= "<b>%d</b> locations generated<br/>" % len(centroids)
      if stats['areas']:
        summary +="Smallest polygon area: <b>%f</b><br/>Mean polygon area: <b>%f</b><br/>Greatest polygon area: <b>%f</b>" % ( min(stats['areas']), sum(stats['areas'])/len(stats['areas']), max(stats['areas']) )
      QMessageBox.information(self,'AniMove: Triangulation summary',summary)


  def inputLayerChanged(self, indx):
    if not self.layers: return
    self.layer = self.layers[indx]
    self.cmbFixIdField.clear()
    self.cmbBearingField.clear()
    self.cmbDateTimeField.clear()
    self.cmbXField.clear()
    self.cmbYField.clear()
    allFields = self.layer.dataProvider().fields()
    # take attributes of first feature (for testing strings)
    provider = self.layer.dataProvider()
    provider.select( provider.attributeIndexes() )
    feat = QgsFeature()
    provider.nextFeature(feat)
    attrs = feat.attributeMap()
    # collect numerical and data fields separately. self.nfields = dict(combobox item : source index)
    self.nfields={}
    self.dfields={}
    for i in allFields:
      if allFields[i].type()<10:
        self.nfields[len(self.nfields)] = i
      elif attrs.has_key(i) and parseDateTime( attrs[i].toString() ):
        self.dfields[len(self.dfields)] = i
    # fill the field comboboxes and set to last/default values if possible
    for i in self.nfields.values():
      self.cmbFixIdField.addItem(allFields[i].name())
      self.cmbBearingField.addItem(allFields[i].name())
      self.cmbXField.addItem(allFields[i].name())
      self.cmbYField.addItem(allFields[i].name())
    for i in self.dfields.values():
        self.cmbDateTimeField.addItem(allFields[i].name())
    for i in self.nfields:
      if not QString.compare( allFields[self.nfields[i]].name(), self.lastFixIdField, Qt.CaseInsensitive): self.cmbFixIdField.setCurrentIndex(i)
      if not QString.compare( allFields[self.nfields[i]].name(), self.lastBearingField, Qt.CaseInsensitive): self.cmbBearingField.setCurrentIndex(i)
      if not QString.compare( allFields[self.nfields[i]].name(), self.lastXField, Qt.CaseInsensitive): self.cmbXField.setCurrentIndex(i)
      if not QString.compare( allFields[self.nfields[i]].name(), self.lastYField, Qt.CaseInsensitive): self.cmbYField.setCurrentIndex(i)
    for i in self.dfields:
      if not QString.compare( allFields[self.dfields[i]].name(), self.lastDateTimeField, Qt.CaseInsensitive): self.cmbDateTimeField.setCurrentIndex(i)
    # fill the output layer names
    ext = self.outputFilter.section('*',1,1).section(' ',0,0)
    self.linePointLayerName.setText(self.layer.name() + '_locations')
    self.linePolygonLayerName.setText(self.layer.name() + '_polygons')
    self.linePointFileName.setText(self.layer.name() + '_locations' + ext)
    self.linePolygonFileName.setText(self.layer.name() + '_polygons'+ ext)
   
    
  def outputModeChanged(self, *args):
    if self.ckbSavePoints.isChecked():
      self.linePointLayerName.setEnabled(False)
      self.linePointFileName.setEnabled(True)
      self.butPointFileName.setEnabled(True)
    elif self.ckbAddPointsToCanvas.isChecked():
      self.linePointLayerName.setEnabled(True)
      self.linePointFileName.setEnabled(False)
      self.butPointFileName.setEnabled(False)
    else:
      self.linePointLayerName.setEnabled(False)
      self.linePointFileName.setEnabled(False)
      self.butPointFileName.setEnabled(False)
    if self.ckbSavePolygons.isChecked():
      self.linePolygonLayerName.setEnabled(False)
      self.linePolygonFileName.setEnabled(True)
      self.butPolygonFileName.setEnabled(True)
    elif self.ckbAddPolygonsToCanvas.isChecked():
      self.linePolygonLayerName.setEnabled(True)
      self.linePolygonFileName.setEnabled(False)
      self.butPolygonFileName.setEnabled(False)
    else:
      self.linePolygonLayerName.setEnabled(False)
      self.linePolygonFileName.setEnabled(False)
      self.butPolygonFileName.setEnabled(False)
      

  def setPointFileName(self):
    self.setFileName('POINTS')


  def setPolygonFileName(self):
    self.setFileName('POLYGONS')


  def setFileName(self, mode): # 'POINT' | 'POLYGON'
    formats = QgsVectorFileWriter.supportedFiltersAndFormats().keys()
    formats.sort()
    filters = ''
    for i in formats:
      filters += i + ';;'
    if mode == 'POLYGONS': 
      title = 'Save polygons as'
      outputDir = self.outputPolygonDir
    else:
      title = 'Save points as'
      outputDir = self.outputPointDir  
    fileDialog = QgsEncodingFileDialog(self, title, outputDir, filters, self.outputEncoding)
    fileDialog.setAcceptMode(QFileDialog.AcceptSave)
    if self.outputFilter:
      fileDialog.selectNameFilter( self.outputFilter )
    if fileDialog.exec_() != QDialog.Accepted:
      return
    fileName = unicode(fileDialog.selectedFiles().first())
    if not fileName:
      return
    filePath = QFileInfo(fileName).absoluteFilePath()
    if filePath.isEmpty():
      return
    self.outputEncoding = str(fileDialog.encoding())
    self.outputFilter = fileDialog.selectedNameFilter()
    driverName = QgsVectorFileWriter.supportedFiltersAndFormats()[ self.outputFilter ]
    if driverName == 'ESRI Shapefile' and QFileInfo(filePath).suffix().toUpper() != 'SHP':
      filePath = filePath + '.shp'
    if driverName == 'KML' and QFileInfo(filePath).suffix().toUpper() != 'KML':
      filePath = filePath + '.kml'
    if mode == 'POLYGONS':
      self.outputPolygonDir = QFileInfo(fileName).absolutePath()
      self.linePolygonFileName.setText(filePath)
    else:
      self.outputPointDir = QFileInfo(fileName).absolutePath()
      self.linePointFileName.setText(filePath)

    
  def driverName(self, filePath):
    outputFormats={ 'BNA': '[OGR] Atlas BNA (*.bna *.BNA)',
                    'DXF': '[OGR] AutoCAD DXF (*.dxf *.DXF)',
                    'CSV': '[OGR] Comma Separated Value (*.csv *.CSV)',
                    'SHP': '[OGR] ESRI Shapefile (*.shp *.SHP)',
                    'GPX': '[OGR] GPS eXchange Format (*.gpx *.GPX)',
                    'GMT': '[OGR] Generic Mapping Tools (*.gmt *.GMT)',
                    'GEOJSON': '[OGR] GeoJSON (*.geojson *.GEOJSON)',
                    'GXT': '[OGR] Geoconcept (*.gxt *.txt *.GXT *.TXT)',
                    'GML': '[OGR] Geography Markup Language (*.gml *.GML)',
                    'ITF': '[OGR] INTERLIS 2 (*.itf *.xml *.ili *.ITF *.XML *.ILI)',
                    'ILI': '[OGR] INTERLIS 2 (*.itf *.xml *.ili *.ITF *.XML *.ILI)',
                    'KML': '[OGR] Keyhole Markup Language (*.kml *.KML)',
                    'MIF': '[OGR] Mapinfo File (*.mif *.tab *.MIF *.TAB)',
                    'TAB': '[OGR] Mapinfo File (*.mif *.tab *.MIF *.TAB)',
                    'DGN': '[OGR] Microstation DGN (*.dgn *.DGN)',
                    'SQLITE': '[OGR] SQLite (*.sqlite *.SQLITE)'}
    if not filePath.contains('.'):
      QMessageBox.warning(self,'I\'m sorry', 'Please add an extension to the output file name(s)')
      return None
    ext = unicode(filePath.section('.',-1).toUpper())
    if not outputFormats.has_key(ext):
      QMessageBox.warning(self,'I\'m sorry', 'I can\'t recognize the <b>.%s</b> file extension. Please use one of supported formats.' % ext)
      return None
    return QgsVectorFileWriter.supportedFiltersAndFormats()[ QString(outputFormats[ext]) ]


  def saveAs(self, layer, filePath, mode): # 'POINT' | 'POLYGON'
    if unicode(filePath.section('.',-1).toUpper())=='SHP' and QFile(filePath).exists():
      try:
        QgsVectorFileWriter.deleteShapeFile(filePath)
      except:
        pass
    errorMsg = QString()
    if QgsVectorFileWriter.writeAsVectorFormat(layer, filePath, self.outputEncoding, layer.crs(), self.driverName(filePath), False, errorMsg):
      QMessageBox.warning(self,'I\'m sorry', errorMsg)
    

  def about(self):
    from DlgAbout import DlgAbout
    dialog = DlgAbout(self)
    dialog.exec_()


  def loadStyle(self, layer, fileName):  
    errorMsg = QString()
    domdoc = QDomDocument()
    qml = QFile( os.path.join(os.path.dirname(__file__), 'styles' , fileName) )
    if not qml.exists():
      QMessageBox.warning(self, 'I\'m sorry', 'Can\'t find style definition for layer %s:\n%s\nProbably plugin installation is broken, a random style will be used instead.' % (layer.name(), qml.fileName()))
      return
    domdoc.setContent(qml)
    n = domdoc.firstChildElement( "qgis" );
    layer.readSymbology(n, errorMsg)


  def doProcess(self):
    global bearings, errors, stats, intersections, centroids 
    
    discardDivergent = self.ckbDiscardDivergent.isChecked()
    discardTooBigAreas = self.ckbDiscardTooBigAreas.isChecked()
    areaThreshold = self.sbAreaThreshold.value()
    includeDateTime = ( self.fieldIndexes['datetime'] > -1 )
        
    provider = self.layer.dataProvider()
    provider.select( provider.attributeIndexes() )
    bearings = {}               # dict( fixIx: [(x1,y1,b1,datetime), (x2,y2,b2,datetime), ...] )
    validBearings = {}          # dict( fixId: [datetime, datetime] )
    errors = {'invalid bearings':0, 'too less bearings':0, 'divergent bearings':0, 'locations discarded because of divergency':0, 'too big areas':0}
    intersections = {}          # dict( fixIx: [(x1,y1,j1,j2), (x2,y2,j1,j2), ...] )   # j1,j2 - bearing indexes
    centroids = {}              # dict( fixIx: (x1,y1,number_of_bearings,area) )
    stats = {}

    # populate the bearings dict
    feat = QgsFeature()
    while provider.nextFeature(feat):
      geom = feat.geometry()
      if self.iface.mapCanvas().hasCrsTransformEnabled():
        geom = QgsGeometry(geom)
        if geom.transform( QgsCoordinateTransform(self.layer.crs(), self.crs) ):
          QMessageBox.warning(self,'I\'m sorry', 'Very strange! Transforming a feature from the layer CRS to project CRS failed.\nPlease try disable OTFR and contact the authors!')
          return
      coor = geom.asPoint()
      attrs = feat.attributeMap()
      fixId = attrs[self.fieldIndexes["id"]].toInt()[0]
      bearing = attrs[self.fieldIndexes["bearing"]].toDouble()
      datetime = None
      if includeDateTime:
        datetime = parseDateTime(attrs[self.fieldIndexes['datetime']].toString())
      if not bearing[1] or bearing[0]<0 or bearing[0]>360:
        errors['invalid bearings'] += 1
      else:
        dadd(bearings, fixId, [(coor.x(), coor.y(), bearing[0], datetime)] )
    stats['total subsets'] = len(bearings)
    stats['total bearings'] = provider.featureCount()
    self.progressBar.setMaximum(len(bearings) * 5)
    self.progressBar.setEnabled(True)
    self.setEnabled(False)
    
    # remove invalid subsets - only one bearing for fixId
    for i in bearings.keys():
      if len(bearings[i]) < 2:
        bearings.pop(i)
        errors['too less bearings'] += 1

    # compute intersections
    for i in bearings.keys():
      isDivergent = False
      for j1 in range(len(bearings[i])):
        for j2 in range(j1+1, len(bearings[i])):
          (x,y) = triang(bearings[i][j1], bearings[i][j2])
          if (x,y) == (-999,-999):
            # divergent bearings!
            errors['divergent bearings'] += 1
            isDivergent = True
          else:
            # convergent bearings
            dadd(intersections, i, [(x,y,j1,j2)])
      if discardDivergent and isDivergent:
        # remove all intersections related to the subset (if inserted already)
        if intersections.has_key(i):
          intersections.pop(i)
        errors['locations discarded because of divergency'] += 1
      self.progressBar.setValue( self.progressBar.value()+1 )
      
    # copy valid bearings only (do not remove anything - the index!)
    for i in bearings.keys():
      for j in range(len(bearings[i])):
        if intersections.has_key(i) and ( j in [c[2] for c in intersections[i]] or j in [c[3] for c in intersections[i]] ):
          dadd(validBearings, i, [bearings[i][j][3]])
        
    # put lines and crossings onto a memory layer
    layerIntersections = QgsVectorLayer('Point', self.layer.name() + '_intersections', 'memory')
    layerIntersections.startEditing()
    layerIntersections.setCrs(self.crs)
    provIntersections = layerIntersections.dataProvider()
    provIntersections.addAttributes( [ QgsField("fixId", QVariant.Int) ] )
    layerBearings = QgsVectorLayer('LineString', self.layer.name() + '_bearings', 'memory')
    layerBearings.startEditing()
    layerBearings.setCrs(self.crs)
    provBearings = layerBearings.dataProvider()
    provBearings.addAttributes( [ QgsField("fixId", QVariant.Int) ] )
    if includeDateTime:
      provIntersections.addAttributes( [ QgsField("time_diff", QVariant.Int),
                                         QgsField("time_mean", QVariant.String) ] )
      provBearings.addAttributes( [ QgsField("datetime", QVariant.String) ] )
    for i in intersections.keys(): #fixId
      for j in intersections[i]:   #tuple
        feat = QgsFeature()
        attrMap = { 0 : QVariant(i) }
        if includeDateTime:
          try:
            timestamps = [bearings[i][j[2]][3].toTime_t(), bearings[i][j[3]][3].toTime_t()]
            mt = QDateTime()
            mt.setTime_t(sum(timestamps)/len(timestamps))
            mt = mt.toString('yyyy/MM/dd hh:mm')
            dt = (max(timestamps)-min(timestamps))/60
          except:
            mt = ''
            dt = -999
          attrMap[1] = QVariant(dt)
          attrMap[2] = QVariant(mt)
        feat.setAttributeMap( attrMap )
        feat.setGeometry( QgsGeometry.fromPoint(QgsPoint(j[0],j[1])) )
        provIntersections.addFeatures([feat])
        if bearings[i][j[2]][3]:
          datetime = bearings[i][j[2]][3].toString('yyyy/MM/dd hh:mm')
        else:
          datetime = ''
        feat.setAttributeMap( { 0 : QVariant(i), 1 : QVariant(datetime) } )
        feat.setGeometry( QgsGeometry.fromPolyline( [QgsPoint(bearings[i][j[2]][0],bearings[i][j[2]][1]), QgsPoint(j[0],j[1])] ))
        provBearings.addFeatures([feat])
        if bearings[i][j[3]][3]:
          datetime = bearings[i][j[3]][3].toString('yyyy/MM/dd hh:mm')
        else:
          datetime = ''
        feat.setAttributeMap( { 0 : QVariant(i), 1 : QVariant(datetime) } )
        feat.setGeometry( QgsGeometry.fromPolyline( [QgsPoint(bearings[i][j[3]][0],bearings[i][j[3]][1]), QgsPoint(j[0],j[1])] ))
        provBearings.addFeatures([feat])
      self.progressBar.setValue( self.progressBar.value()+1 )  
    layerIntersections.updateExtents()
    layerBearings.updateExtents()
    layerIntersections.commitChanges()
    layerBearings.commitChanges()


    # compute polygons and put them onto a memory layer
    areas = {}
    layerPolygons = QgsVectorLayer('Polygon', self.linePolygonLayerName.text(), 'memory')
    layerPolygons.startEditing()
    layerPolygons.setCrs(self.crs)
    provPolygons = layerPolygons.dataProvider()
    provPolygons.addAttributes( [ QgsField("fixId", QVariant.Int),
                                  QgsField("n",  QVariant.Int),
                                  QgsField("area", QVariant.Double) ] )
    if includeDateTime:
      provPolygons.addAttributes( [ QgsField("time_diff", QVariant.Int),
                                    QgsField("time_mean", QVariant.String) ] )
    for i in intersections.keys(): #fixId
      if len(intersections[i]) > 2: # don't create bigons!
        vertices = []
        feat = QgsFeature()
        for j in intersections[i]:   #tuple
          vertices.append(QgsPoint(j[0],j[1]))
        geom = QgsGeometry.fromMultiPoint(vertices).convexHull()
        areas[i] = QgsDistanceArea().measure(geom)
        if discardTooBigAreas and areas[i] > areaThreshold:
          #don't create polygon AND ALSO remove all the related intersections!
          intersections.pop(i)
          errors['too big areas'] += 1
        else:
          feat.setGeometry( geom )
          attrMap = { 0 : QVariant(i),
                      1 : QVariant( len(intersections[i]) ),
                      2 : QVariant( areas[i] ) }
          if includeDateTime:
            try:
              timestamps = [t.toTime_t() for t in validBearings[i]]
              mt = QDateTime()
              mt.setTime_t(sum(timestamps)/len(timestamps))
              mt = mt.toString('yyyy/MM/dd hh:mm')
              dt = (max(timestamps)-min(timestamps))/60
            except:
              mt = ''
              dt = -999
            attrMap[3] = QVariant(dt)
            attrMap[4] = QVariant(mt)
          feat.setAttributeMap( attrMap )
          provPolygons.addFeatures([feat])
      self.progressBar.setValue( self.progressBar.value()+1 )  
    layerPolygons.updateExtents()
    layerPolygons.commitChanges()
    #copy non-zero areas to stats (currently there's no zero areas though)
    stats["areas"] = []
    for i in areas.values():
      if i>0 and (i <= areaThreshold or not discardTooBigAreas):
        stats["areas"]+=[i]

    # compute centroids        
    for i in intersections.keys():
      if len(intersections[i]) == 1:
        # one intersection found
        centroids[i] = (intersections[i][0][0],intersections[i][0][1],1,0)
      else:
        # more than one intersection found
        x = sum([coor[0] for coor in intersections[i]]) / len(intersections[i])
        y = sum([coor[1] for coor in intersections[i]]) / len(intersections[i])
        n = len(intersections[i])
        if areas.has_key(i):
          a = areas[i]
        else:
          a = 0
        centroids[i] = (x,y,n,a)
      self.progressBar.setValue( self.progressBar.value()+1 )  
        
    # put centroids onto a memory layer
    layerCentroids = QgsVectorLayer('Point', self.linePointLayerName.text(), 'memory')
    layerCentroids.startEditing()
    layerCentroids.setCrs(self.crs)
    provCentroids = layerCentroids.dataProvider()
    provCentroids.addAttributes( [ QgsField("fixId", QVariant.Int),
                                   QgsField("n",  QVariant.Int),
                                   QgsField("area", QVariant.Double) ] )
    if includeDateTime:
      provCentroids.addAttributes( [ QgsField("time_diff", QVariant.Int),
                                     QgsField("time_mean", QVariant.String) ] )                                   
    for i in centroids.keys(): #fixId
      feat = QgsFeature()
      feat.setGeometry( QgsGeometry.fromPoint(QgsPoint(centroids[i][0],centroids[i][1])) )
      attrMap = { 0 : QVariant(i),
                  1 : QVariant( centroids[i][2] ),
                  2 : QVariant( centroids[i][3] ) }
      if includeDateTime:
        try:
          timestamps = [t.toTime_t() for t in validBearings[i]]
          mt = QDateTime()
          mt.setTime_t(sum(timestamps)/len(timestamps))
          mt = mt.toString('yyyy/MM/dd hh:mm')
          dt = (max(timestamps)-min(timestamps))/60
        except:
          mt = ''
          dt = -999
        attrMap[3] = QVariant(dt)
        attrMap[4] = QVariant(mt)
      feat.setAttributeMap( attrMap )
      provCentroids.addFeatures([feat])
      self.progressBar.setValue( self.progressBar.value()+1 )  
    layerCentroids.updateExtents()
    layerCentroids.commitChanges()
    self.progressBar.setEnabled(False)
    self.setEnabled(True)

    #save layers and/or add to mapcanvas
    if self.ckbSavePolygons.isChecked():
      filePath = self.linePolygonFileName.text()
      self.saveAs(layerPolygons, filePath,'POLYGONS')
      if self.ckbAddPolygonsToCanvas.isChecked():
        #add to canvas
        layer = QgsVectorLayer(filePath, QFileInfo(filePath).completeBaseName(), 'ogr')
        if layer.isValid():
          self.loadStyle(layer, "polygons.qml")
          QgsMapLayerRegistry.instance().addMapLayer(layer)
        else:
          QMessageBox.warning(self, 'I\'m sorry', 'The new layer seems to be created, but is invalid.\nIt won\'t be loaded.')
    elif self.ckbAddPolygonsToCanvas.isChecked():
      self.loadStyle(layerPolygons, "polygons.qml")
      QgsMapLayerRegistry.instance().addMapLayer(layerPolygons)
    if self.ckbShowLines.isChecked():
      self.loadStyle(layerBearings, "bearings.qml")
      self.loadStyle(layerIntersections, "intersections.qml")
      QgsMapLayerRegistry.instance().addMapLayer(layerBearings)
      QgsMapLayerRegistry.instance().addMapLayer(layerIntersections)
      self.iface.legendInterface().setLayerVisible(layerIntersections,False)
    if self.ckbSavePoints.isChecked():
      filePath = self.linePointFileName.text()
      self.saveAs(layerCentroids, filePath, 'POINTS')
      if self.ckbAddPointsToCanvas.isChecked():
        #add to canvas
        layer = QgsVectorLayer(filePath, QFileInfo(filePath).completeBaseName(), 'ogr')
        if layer.isValid():
          self.loadStyle(layer, "locations.qml")
          QgsMapLayerRegistry.instance().addMapLayer(layer)
        else:
          QMessageBox.warning(self, 'I\'m sorry', 'The new layer seems to be created, but is invalid.\nIt won\'t be loaded.')
    elif self.ckbAddPointsToCanvas.isChecked():
      self.loadStyle(layerCentroids, "locations.qml")
      QgsMapLayerRegistry.instance().addMapLayer(layerCentroids)
      
