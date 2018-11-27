#load .csv files, join to NSV network shapefile
from qgis.core import *
import qgis.utils
from PyQt4.QtCore import *
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
import processing
import os, sys, shutil
import csv
import numpy
import datetime



NetworkPath="C:/Users/Sam/Desktop/spatial/QgisEnvironment/Active/d8_500_simple/NSVStreamSegmentsLength.shp"
CsvPath="file:///C:/Users/Sam/Desktop/spatial/VisualisationData/p1_mapData/"
CsvSpecs="?type=csv&geomType=none&subsetIndex=no&watchFile=no"
OutPath=CsvPath
CsvPreface="7_27_NConc_"

networkLayer=QgsVectorLayer(NetworkPath,"NSVStreamSegmentsLength",'ogt')
QgsMapLayerRegistry.instance().addMapLayer(networkLayer)

Name="0.01_combined_cold"
csvLayer=QgsVectorLayer(CsvPath+CsvPreface+Name+".csv",Name,'ogr')
QgsMapLayerRegistry.instance().addMapLayer(csvLayer)
processing.runalg("qgis:joinattributestable","C:/Users/Sam/Desktop/spatial/QgisEnvironment/Active/d8_500_simple/NSVStreamSegmentsLength.shp","file:///C:/Users/Sam/Desktop/spatial/VisualisationData/p1_mapData/7_27_NConc_"+Name+".csv?type=csv&geomType=none&subsetIndex=no&watchFile=no","AUTO","ID","C:/Users/Sam/Desktop/spatial/VisualisationData/p1_mapData/display_"+Name+".shp")

Name="0.01_concOnly_cold"
csvLayer=QgsVectorLayer(CsvPath+CsvPreface+Name+".csv",Name,'ogr')
QgsMapLayerRegistry.instance().addMapLayer(csvLayer)
processing.runalg("qgis:joinattributestable","C:/Users/Sam/Desktop/spatial/QgisEnvironment/Active/d8_500_simple/NSVStreamSegmentsLength.shp","file:///C:/Users/Sam/Desktop/spatial/VisualisationData/p1_mapData/7_27_NConc_"+Name+".csv?type=csv&geomType=none&subsetIndex=no&watchFile=no","AUTO","ID","C:/Users/Sam/Desktop/spatial/VisualisationData/p1_mapData/test3_"+Name+".shp")