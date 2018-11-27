from qgis.core import *
import qgis.utils
from PyQt4.QtCore import *
import processing
import os
import csv
from numpy import *
import datetime

print "start time: " + str(datetime.datetime.now().time())

## user inputs ---------
BasePath = "C:/Users/Sam/Desktop/spatial/QgisEnvironment/Active/mfd/"
inputDemName = "grdn41w106_13/w001001.adf"
inputEPSG="4326"
environmentEPSG="32613"
WatershedOutPointsCsvName="WshedDefinitions.csv"
StreamDrainageThreshold=25000
## end user inputs ---------

def loadRaster(basePath, rasterName):
    fileName = basePath + rasterName
    fileInfo = QFileInfo(fileName)
    baseName=fileInfo.baseName()
    newRaster = QgsRasterLayer(fileName, baseName)
    if not newRaster.isValid():
        print rasterName + " raster failed to load"
    else:
        return newRaster
    


def getExtCords(rasterName):
    fullExt = rasterName.extent() 
    return str(fullExt.xMinimum()) +","+ str(fullExt.xMaximum()) + "," + str(fullExt.yMinimum()) + "," + str(fullExt.yMaximum())

#convert to wgs 84 projected
bigDemName = "BigDemWGS84.tif"

if os.access(BasePath+bigDemName,os.F_OK):
    os.remove(BasePath+bigDemName)

print "Reprojecting dem from ESPG:"+inputEPSG+"to EPSG:"+ environmentEPSG+"..."
processing.runalg("gdalogr:warpreproject",BasePath+inputDemName,"EPSG:"+inputEPSG,"EPSG:"+environmentEPSG,"-9999",0,1,5,0,75,6,1,False,0,False,"",BasePath+bigDemName)
#load big dem raster into qpython to determine extent
bigDemLayer = loadRaster(BasePath,bigDemName)


print "Calculating watershed parameters for StreamDrainageThreshold = " + str(StreamDrainageThreshold) + ".  This may take a while..."
processing.runalg("grass:r.watershed",BasePath + bigDemName,None,None,None,None,StreamDrainageThreshold,0,9,300,False,False,False,False,getExtCords(bigDemLayer),0,BasePath + "uaa",BasePath +"flowdir",BasePath +"watersheds",BasePath +"streams",BasePath +"half_watersheds",BasePath +"visualDisplay",BasePath +"slopeLengthSteepness",BasePath +"SlopeSteepness")

OutPoints=QgsVectorLayer(BasePath + "OutPoints.shp", "OutPoints","ogr")

iter=OutPoints.getFeatures()
for feature in iter:
    geom=feature.geometry()
    xy=geom.asPoint()
    name=str(feature.attributes()[0])
    print "Extracting raster data to " + name + " watershed"
    processing.runalg("grass:r.water.outlet",BasePath+"flowdir.tif",xy[0],xy[1],getExtCords(bigDemLayer),0,BasePath+name+"XL.tif")
    processing.runalg("saga:croptodata",BasePath+name+"XL.tif",BasePath+name+".tif")
    wshedDefRaster = loadRaster(BasePath,name+".tif")
    processing.runalg("grass:r.mapcalculator",BasePath+"uaa.tif",wshedDefRaster,None,None,None,None,"A*B",getExtCords(wshedDefRaster),0,BasePath + name + "_uaa.tif")
    processing.runalg("grass:r.mapcalculator",BasePath+"flowdir.tif",wshedDefRaster,None,None,None,None,"A*B",getExtCords(wshedDefRaster),0,BasePath + name + "_flowdir.tif")
    processing.runalg("grass:r.mapcalculator",BasePath+"streams.tif",wshedDefRaster,None,None,None,None,"A*B",getExtCords(wshedDefRaster),0,BasePath + name + "_streams.tif")
    processing.runalg("grass:r.mapcalculator",BasePath+"half_watersheds.tif",wshedDefRaster,None,None,None,None,"A*B",getExtCords(wshedDefRaster),0,BasePath + name + "_half_watersheds.tif")
    processing.runalg("grass:r.mapcalculator",BasePath+"SlopeSteepness.tif",wshedDefRaster,None,None,None,None,"A*B",getExtCords(wshedDefRaster),0,BasePath + name + "_SlopeSteepness.tif")
    processing.runalg("grass:r.mapcalculator",BasePath+"BigDemWGS84.tif",wshedDefRaster,None,None,None,None,"A*B",getExtCords(wshedDefRaster),0,BasePath + name + "_Dem.tif")

print "end time: " +str(datetime.datetime.now().time())