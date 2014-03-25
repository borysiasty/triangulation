# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
#
# Triangulation
# Copyright (C) 2010-2014 Borys Jurgiel for Faunalia and University of Evora
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
    self.ckbAddPointsToCanvas.toggled.connect(self.outputModeChanged)
    self.ckbSavePoints.toggled.connect(self.outputModeChanged)
    self.ckbAddPolygonsToCanvas.toggled.connect(self.outputModeChanged)
    self.ckbSavePolygons.toggled.connect(self.outputModeChanged)
    self.cmbInLayer.currentIndexChanged.connect(self.inputLayerChanged)
    self.butAbout.released.connect(self.about)
    self.butPointFileName.released.connect(self.setPointFileName)
    self.butPolygonFileName.released.connect(self.setPolygonFileName)

    # restore last settings
    settings = QSettings()
    self.lastFixIdField = settings.value('/AniMove/triangulation/fixIdField', 'id', type=unicode)
    self.lastBearingField = settings.value('/AniMove/triangulation/bearingField', 'bearing', type=unicode)
    self.lastDateTimeField = settings.value('/AniMove/triangulation/datetimeField', 'datetime', type=unicode)
    self.lastOutputPointDir = settings.value('/AniMove/triangulation/outputPointDir', '.', type=unicode)
    self.lastOutputPolygonDir = settings.value('/AniMove/triangulation/outputPolygonDir', '.', type=unicode)
    self.lastXField = settings.value('/AniMove/triangulation/xField', 'x', type=unicode)
    self.lastYField = settings.value('/AniMove/triangulation/yField', 'y', type=unicode)
    self.ckbDiscardDivergent.setChecked( settings.value('/AniMove/triangulation/discardDivergent', False, type=bool) )
    self.ckbDiscardTooBigAreas.setChecked( settings.value('/AniMove/triangulation/discardTooBigAreas', False, type=bool) )
    self.sbAreaThreshold.setValue( settings.value('/AniMove/triangulation/areaThreshold', 10000, type=int) )
    self.ckbShowSummary.setChecked( settings.value('/AniMove/triangulation/showSummary', False, type=bool) )
    self.ckbShowLines.setChecked( settings.value('/AniMove/triangulation/showLines', False, type=bool) )
    self.ckbAddPointsToCanvas.setChecked( settings.value('/AniMove/triangulation/addPointsToCanvas', True, type=bool) )
    self.ckbSavePoints.setChecked( settings.value('/AniMove/triangulation/savePoints', False, type=bool) )
    self.ckbAddPolygonsToCanvas.setChecked( settings.value('/AniMove/triangulation/AddPolygonsToCanvas', True, type=bool) )
    self.ckbSavePolygons.setChecked( settings.value('/AniMove/triangulation/savePolygons', False, type=bool) )
    self.outputPointDir = settings.value('/AniMove/triangulation/outputPointDir', '.', type=unicode)
    self.outputPolygonDir = settings.value('/AniMove/triangulation/outputPolygonDir', '.', type=unicode)
    self.outputEncoding = settings.value('/AniMove/triangulation/outputEncoding', 'UTF-8', type=unicode)
    self.outputFilter = settings.value('/AniMove/triangulation/outputFilter', '[OGR] Geography Markup Language (*.gml *.GML)', type=unicode)

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
      self.crs = self.iface.mapCanvas().mapRenderer().destinationCrs()
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
    settings.setValue('/AniMove/triangulation/fixIdField', self.cmbFixIdField.currentText())
    settings.setValue('/AniMove/triangulation/bearingField', self.cmbBearingField.currentText())
    settings.setValue('/AniMove/triangulation/datetimeField', self.cmbDateTimeField.currentText())
    settings.setValue('/AniMove/triangulation/xField', self.cmbXField.currentText())
    settings.setValue('/AniMove/triangulation/yField', self.cmbYField.currentText())
    settings.setValue('/AniMove/triangulation/discardDivergent', self.ckbDiscardDivergent.isChecked())
    settings.setValue('/AniMove/triangulation/discardTooBigAreas', self.ckbDiscardTooBigAreas.isChecked())
    settings.setValue('/AniMove/triangulation/areaThreshold', self.sbAreaThreshold.value())
    settings.setValue('/AniMove/triangulation/showSummary', self.ckbShowSummary.isChecked())
    settings.setValue('/AniMove/triangulation/showLines', self.ckbShowLines.isChecked())
    settings.setValue('/AniMove/triangulation/addPointsToCanvas', self.ckbAddPointsToCanvas.isChecked())
    settings.setValue('/AniMove/triangulation/savePoints', self.ckbSavePoints.isChecked())
    settings.setValue('/AniMove/triangulation/AddPolygonsToCanvas', self.ckbAddPolygonsToCanvas.isChecked())
    settings.setValue('/AniMove/triangulation/savePolygons', self.ckbSavePolygons.isChecked())
    settings.setValue('/AniMove/triangulation/outputPointDir', self.outputPointDir)
    settings.setValue('/AniMove/triangulation/outputPolygonDir', self.outputPolygonDir)
    settings.setValue('/AniMove/triangulation/outputEncoding', self.outputEncoding)
    settings.setValue('/AniMove/triangulation/outputFilter', self.outputFilter)
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
    # take attributes of first feature (for testing strings)
    feat = QgsFeature()
    result = self.layer.getFeatures().nextFeature(feat)
    if not result:
        # make the feat empty
        feat = QgsFeature()
    allFields = feat.fields().toList()
    attrs = feat.attributes()
    # collect numerical and data fields separately. self.nfields = dict(combobox item : source index)
    self.nfields={}
    self.dfields={}
    for i in range(len(allFields)):
      if allFields[i].type()<10:
        self.nfields[len(self.nfields)] = i
      elif parseDateTime( attrs[i] ):
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
      if allFields[self.nfields[i]].name().upper() == self.lastFixIdField.upper(): self.cmbFixIdField.setCurrentIndex(i)
      if allFields[self.nfields[i]].name().upper() == self.lastBearingField.upper(): self.cmbBearingField.setCurrentIndex(i)
      if allFields[self.nfields[i]].name().upper() == self.lastXField.upper(): self.cmbXField.setCurrentIndex(i)
      if allFields[self.nfields[i]].name().upper() == self.lastYField.upper(): self.cmbYField.setCurrentIndex(i)
    for i in self.dfields:
      if allFields[self.dfields[i]].name().upper() == self.lastDateTimeField.upper(): self.cmbDateTimeField.setCurrentIndex(i)
    # fill the output layer names
    ext = self.outputFilter.split('*')[1].split(' ')[0]
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
    fileName = fileDialog.selectedFiles()[0]
    if not fileName:
      return
    filePath = QFileInfo(fileName).absoluteFilePath()
    if not filePath:
      return
    self.outputEncoding = str(fileDialog.encoding())
    self.outputFilter = fileDialog.selectedNameFilter()
    driverName = QgsVectorFileWriter.supportedFiltersAndFormats()[ self.outputFilter ]
    if driverName == 'ESRI Shapefile' and QFileInfo(filePath).suffix().upper() != 'SHP':
      filePath = filePath + '.shp'
    if driverName == 'KML' and QFileInfo(filePath).suffix().upper() != 'KML':
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
    # seems newer GDAL of QGIS verisons use another names, so we need an alternate dictionary
    alternateFormats={  'BNA': 'Atlas BNA [OGR] (*.bna *.BNA)',
                        'DXF': 'AutoCAD DXF [OGR] (*.dxf *.DXF)',
                        'CSV': 'Comma Separated Value [CSV] [OGR] (*.csv *.CSV)',
                        'SHP': 'ESRI Shapefile [OGR] (*.shp *.SHP)',
                        'GPX': 'Format GPS eXchange [GPX] [OGR] (*.gpx *.GPX)',
                        'GMT': 'Generic Mapping Tools [GMT] [OGR] (*.gmt *.GMT)',
                        'GEOJSON': 'GeoJSON [OGR] (*.geojson *.GEOJSON)',
                        'GXT': 'Geoconcept [OGR] (*.gxt *.txt *.GXT *.TXT)',
                        'GML': 'Geography Markup Language [GML] [OGR] (*.gml *.GML)',
                        'ITF': 'INTERLIS 2 [OGR] (*.itf *.xml *.ili *.ITF *.XML *.ILI)',
                        'ILI': 'INTERLIS 2 [OGR] (*.itf *.xml *.ili *.ITF *.XML *.ILI)',
                        'KML': 'Keyhole Markup Language [KML] [OGR] (*.kml *.KML)',
                        'TAB': 'MapInfo TAB [OGR] (*.tab *.TAB)',
                        'DGN': 'Microstation DGN [OGR] (*.dgn *.DGN)',
                        'SQLITE': 'SQLite [OGR] (*.sqlite *.SQLITE)'}



    if not '.' in filePath:
      QMessageBox.warning(self,'I\'m sorry', 'Please add an extension to the output file name(s)')
      return None
    ext = filePath.upper().split('.')[-1]
    if not outputFormats.has_key(ext):
      QMessageBox.warning(self,'I\'m sorry', 'I can\'t recognize the <b>.%s</b> file extension. Please use one of supported formats.' % ext)
      return None
    if outputFormats[ext] in QgsVectorFileWriter.supportedFiltersAndFormats():
        return QgsVectorFileWriter.supportedFiltersAndFormats()[ outputFormats[ext] ]
    elif alternateFormats[ext] in QgsVectorFileWriter.supportedFiltersAndFormats():
        return QgsVectorFileWriter.supportedFiltersAndFormats()[ alternateFormats[ext] ]
    else:
      QMessageBox.warning(self,'I\'m sorry', 'I can\'t handle the <b>.%s</b> file format. Please try another format.' % ext)
      return None


  def saveAs(self, layer, filePath, mode): # 'POINT' | 'POLYGON'
    if filePath.upper().split('.')[-1] == 'SHP' and QFile(filePath).exists():
      try:
        QgsVectorFileWriter.deleteShapeFile(filePath)
      except:
        pass
    errorMsg = ''
    if QgsVectorFileWriter.writeAsVectorFormat(layer, filePath, self.outputEncoding, layer.crs(), self.driverName(filePath), False, errorMsg):
      QMessageBox.warning(self,'I\'m sorry', errorMsg)


  def about(self):
    from DlgAbout import DlgAbout
    dialog = DlgAbout(self)
    dialog.exec_()


  def loadStyle(self, layer, fileName):
    errorMsg = ''
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

#    provider = self.layer.dataProvider()
#    provider.select( provider.attributeIndexes() )
    bearings = {}               # dict( fixIx: [(x1,y1,b1,datetime), (x2,y2,b2,datetime), ...] )
    validBearings = {}          # dict( fixId: [datetime, datetime] )
    errors = {'invalid bearings':0, 'too less bearings':0, 'divergent bearings':0, 'locations discarded because of divergency':0, 'too big areas':0}
    intersections = {}          # dict( fixIx: [(x1,y1,j1,j2), (x2,y2,j1,j2), ...] )   # j1,j2 - bearing indexes
    centroids = {}              # dict( fixIx: (x1,y1,number_of_bearings,area) )
    stats = {}

    # populate the bearings dict
    for feat in self.layer.getFeatures():
      geom = feat.geometry()
      if self.iface.mapCanvas().hasCrsTransformEnabled():
        geom = QgsGeometry(geom)
        if geom.transform( QgsCoordinateTransform(self.layer.crs(), self.crs) ):
          QMessageBox.warning(self,'I\'m sorry', 'Very strange! Transforming a feature from the layer CRS to project CRS failed.\nPlease try disable OTFR and contact the authors!')
          return
      coor = geom.asPoint()
      attrs = feat.attributes()
      fixId = attrs[self.fieldIndexes["id"]]
      bearing = attrs[self.fieldIndexes["bearing"]]
      datetime = None
      if includeDateTime:
        datetime = parseDateTime(attrs[self.fieldIndexes['datetime']])
      if not bearing or bearing<0 or bearing>360:
        errors['invalid bearings'] += 1
      else:
        dadd(bearings, fixId, [(coor.x(), coor.y(), bearing, datetime)] )
    stats['total subsets'] = len(bearings)
    stats['total bearings'] = self.layer.featureCount()
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
        attrs = [i]
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
          attrs += [dt,mt]
        feat.initAttributes(len(attrs))
        feat.setAttributes(attrs)
        feat.setGeometry( QgsGeometry.fromPoint(QgsPoint(j[0],j[1])) )
        provIntersections.addFeatures([feat])
        if bearings[i][j[2]][3]:
          datetime = bearings[i][j[2]][3].toString('yyyy/MM/dd hh:mm')
        else:
          datetime = ''
        feat = QgsFeature()
        attrs = [i,datetime]
        feat.initAttributes(len(attrs))
        feat.setAttributes(attrs)
        feat.setGeometry( QgsGeometry.fromPolyline( [QgsPoint(bearings[i][j[2]][0],bearings[i][j[2]][1]), QgsPoint(j[0],j[1])] ))
        provBearings.addFeatures([feat])
        if bearings[i][j[3]][3]:
          datetime = bearings[i][j[3]][3].toString('yyyy/MM/dd hh:mm')
        else:
          datetime = ''
        feat = QgsFeature()
        attrs = [i,datetime]
        feat.initAttributes(len(attrs))
        feat.setAttributes(attrs)
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
          attrs = [ i,
                    len(intersections[i]),
                    areas[i] ]
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
            attrs += [dt,mt]
          feat.initAttributes(len(attrs))
          feat.setAttributes(attrs)
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
      attrs = [ i,
                centroids[i][2],
                centroids[i][3] ]
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
        attrs += [dt,mt]
      feat.initAttributes(len(attrs))
      feat.setAttributes(attrs)
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

