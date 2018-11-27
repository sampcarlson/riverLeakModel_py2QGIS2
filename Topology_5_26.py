from qgis.core import *
import qgis.utils
from PyQt4.QtCore import *
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
import processing
import os, sys, shutil
import csv
import numpy
import datetime

print "start time: " + str(datetime.datetime.now().time())

#execfile(u'C:/Users/Sam/Desktop/spatial/QgisEnvironment/Inputs_and_scripts/ClipClop.py'.encode('mbcs'))

## user inputs ---------
BasePath = "C:/Users/Sam/Desktop/spatial/QgisEnvironment/Active/d8_100/"
StreamDrainageThreshold=25000
ReachLength=10000
## end user inputs ---------

#def deleteRasters(BasePath,rasterList):
#    for raster in rasterList:
#        if os.access(BasePath+raster+".tif",os.F_OK):
#            os.remove(BasePath+raster+".tif")
#        if os.access(BasePath+raster+".tif.mgrd",os.F_OK):
#            os.remove(BasePath+raster+".tif.mgrd")
#        if os.access(BasePath+raster+".tif.prj",os.F_OK):
#            os.remove(BasePath+raster+".tif.prj")
#        if os.access(BasePath+raster+".tif.sdat",os.F_OK):
#            os.remove(BasePath+raster+".tif.sdat")
#        if os.access(BasePath+raster+".tif.sgrd",os.F_OK):
#            os.remove(BasePath+raster+".tif.sgrd")

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

##Stream raster to vector, Remove unrealistic stream segments

QSettings().setValue("/Projections/defaultBehaviour","useProject")
OutPoints=QgsVectorLayer(BasePath + "OutPoints.shp", "OutPoints","ogr")
iter=OutPoints.getFeatures()
for feature in iter:
    name=str(feature.attributes()[0])
    print name
    wshedDefRaster = loadRaster(BasePath, name+".tif")
    #not exact - cells are not quite square
    cellSize = (wshedDefRaster.rasterUnitsPerPixelY()+wshedDefRaster.rasterUnitsPerPixelY())/2
    processing.runalg("grass:r.to.vect",BasePath+name+"_streams.tif",1,False,getExtCords(wshedDefRaster),0,BasePath + name+ "Points")
    #find singular values
    StreamPoints = QgsVectorLayer(BasePath + name + "Points.shp", "StreamPoints","ogr")
    StreamPtsIter = StreamPoints.getFeatures()
    allPts = []
    dupPts=[]
    tooShort=[]
    for pt in StreamPtsIter:
        if pt['value'] not in allPts:
            allPts.append(pt['value'])
        else:
            dupPts.append(pt['value'])

    for pid in allPts:
        if pid not in dupPts:
            tooShort.append(pid) 
    
    halfWshedsRaster=loadRaster(BasePath,name+"_half_watersheds.tif")
    calcEntries = []
    ras1=QgsRasterCalculatorEntry()
    ras1.ref='wshedConst'
    ras1.raster=wshedDefRaster
    ras1.bandNumber=1
    calcEntries.append(ras1)
    
    ras2=QgsRasterCalculatorEntry()
    ras2.ref='halfContribAreas'
    ras2.raster=halfWshedsRaster
    ras2.bandNumber=1
    calcEntries.append(ras2)
    selectSmallString = ''
    for i in range(0,len(tooShort)):
        if i == 0:
            selectSmallString = '"halfContribAreas" = '
            selectSmallString = selectSmallString + str(tooShort[i])
            selectSmallString = selectSmallString + ' OR "halfContribAreas" = '
            selectSmallString = selectSmallString + str(tooShort[i]-1)
        else:
            selectSmallString = selectSmallString + ' OR "halfContribAreas" = '
            selectSmallString = selectSmallString + str(tooShort[i])
            selectSmallString = selectSmallString + ' OR "halfContribAreas" = '
            selectSmallString = selectSmallString + str(tooShort[i]-1)
    if len(selectSmallString)>0:
        calc = QgsRasterCalculator(' "wshedConst" - 0.9 * ( '+selectSmallString+' )',BasePath+name+'adjustedFlow.tif','GTiff',wshedDefRaster.extent(),wshedDefRaster.width(),wshedDefRaster.height(),calcEntries)
        print ' "wshedConst" - 0.9 * ( '+selectSmallString+' )'
        calc.processCalculation()
        #run watershed tool with adjustedFlow
        processing.runalg("grass:r.watershed",BasePath + name+"_Dem.tif",None,BasePath+name+"adjustedFlow.tif",None,None,StreamDrainageThreshold,0,9,300,False,False,False,False,getExtCords(wshedDefRaster),0,BasePath + name+"_uaa_adj",BasePath+name+"_flowdir_adj",BasePath +name+"_watersheds_adj",BasePath +name+"_streams_adj",BasePath +name+"_half_watersheds_adj",BasePath +name+"_visualDisplay_adj",BasePath +name+"_slopeLengthSteepness_adj",BasePath +name+"_SlopeSteepness_adj")
        #run r.to.vect points from watershed tool streamoutputraster
        processing.runalg("grass:r.to.vect",BasePath+name+"_streams_adj.tif",1,False,getExtCords(wshedDefRaster),0,BasePath + name+ "Points_adj")
        #if stream network is modified, create lines here:
        processing.runalg("grass:v.sample",BasePath + name + "Points_adj.shp","value",BasePath+name+"_uaa.tif",1,False,False,getExtCords(wshedDefRaster),-1,0.0001,0,BasePath+name+"PointsUaa")
        processing.runalg("saga:convertpointstolines",BasePath+name+"PointsUaa.shp","rast_val","pnt_val",BasePath+name+"StreamLine")
    else:
        #otherwise, create streamlines here:pointsIDs
        processing.runalg("grass:v.sample",BasePath + name + "Points.shp","value",BasePath+name+"_uaa.tif",1,False,False,getExtCords(wshedDefRaster),-1,0.0001,0,BasePath+name+"PointsUaa")
        processing.runalg("saga:convertpointstolines",BasePath+name+"PointsUaa.shp","rast_val","pnt_val",BasePath+name+"StreamLine")

    #smooth streams to undo diagonal length bias (important with 4 direction flow), less so with 8 direction flow
    processing.runalg("qgis:simplifygeometries",BasePath+name+"StreamLine.shp",2,BasePath+name+"StreamLineSmooth")
    
    processing.runalg("grass:v.split.length",BasePath+name+"StreamLineSmooth.shp",ReachLength,getExtCords(wshedDefRaster),-1,0.0001,0,BasePath+name+"StreamSegments")
    processing.runalg("qgis:addautoincrementalfield",BasePath+name+"StreamSegments.shp",BasePath+name+"StreamSegmentsIDX")
    processing.runalg("grass:v.to.points",BasePath+name+"StreamSegmentsIDX.shp",ReachLength,False,False,False,getExtCords(wshedDefRaster),-1,0.0001,0,BasePath+name+"StreamSegmentEndpoints")
    processing.runalg("qgis:fieldcalculator",BasePath+name+"StreamSegmentEndpoints.shp","SegIDX",1,10,3,True,' "AUTO" ',BasePath+name+"StreamSegmentEndpointsSegIDX.shp")
    processing.runalg("qgis:deletecolumn",BasePath+name+"StreamSegmentEndpointsSegIDX.shp","AUTO",BasePath+name+"EndpointsSegIDX.shp")
    processing.runalg("qgis:addautoincrementalfield",BasePath+name+"EndpointsSegIDX.shp",BasePath+name+"EndpointsSegIDXAutoIDX.shp")
    processing.runalg("qgis:exportaddgeometrycolumns",BasePath+name+"EndpointsSegIDXAutoIDX.shp",0,BasePath+name+"EndpointsSegIDXAutoIDXXY.shp")
    processing.runalg("grass:v.sample",BasePath+name+"EndpointsSegIDXAutoIDXXY.shp","AUTO",BasePath+name+"_uaa.tif",1,False,False,getExtCords(wshedDefRaster),-1,0.0001,0,BasePath+name+"EndpointsUaa")
    processing.runalg("qgis:fieldcalculator",BasePath+name+"EndpointsUaa.shp","PointIDX",1,10,3,True,' "pnt_val" ',BasePath+name+"UaaIntIndex.shp")
    processing.runalg("qgis:joinattributestable",BasePath+name+"EndpointsSegIDXAutoIDXXY.shp",BasePath+name+"UaaIntIndex.shp","AUTO","PointIDX",BasePath+name+"EndpointsFinal_extra")
    processing.runalg("qgis:deletecolumn",BasePath+name+"EndpointsFinal_extra.shp","AUTO",BasePath+name+"EndpointsFinal_Extra1.shp")
    processing.runalg("qgis:deletecolumn",BasePath+name+"EndpointsFinal_extra1.shp","diff",BasePath+name+"EndpointsFinal_Extra2.shp")
    processing.runalg("qgis:deletecolumn",BasePath+name+"EndpointsFinal_extra2.shp","pnt_val_2",BasePath+name+"EndpointsFinal.shp")
    
    endpointsVector= QgsVectorLayer(BasePath + name + "EndpointsFinal.shp", "EndpointsFinal","ogr")
    endpointsArray=[]
    del endpointsArray
    first='T'
    pts=endpointsVector.getFeatures()
    for point in pts:
        if first=='T':
            endpointsArray=numpy.array([point.attributes()])
            first='F'
        else:  #first=='F':
            endpointsArray = numpy.append(endpointsArray,numpy.array([point.attributes()]),axis=0)

    endpointsStruct = numpy.core.records.fromarrays(endpointsArray.transpose(),names='halfWshedID, reachID, segID,x, y, uaa, pointID', formats='i8,i8,i8,f8,f8,i8,i8') 
    endpointsStructSort=numpy.sort(endpointsStruct,0,order=['segID','uaa'])
    endpointsLower=endpointsStructSort[1:endpointsStructSort.shape[0]:2]
    endpointsLowerSort=numpy.sort(endpointsLower,0,order=['uaa'])

 #   make nodata raster 'basins.tif'
    #deleteRasters(BasePath,['basins','temp','merged'])
#    if os.path.exists(BasePath+name+"Temp"):
#        shutil.rmtree(BasePath+name+"Temp")
#    os.mkdir(BasePath+name+"Temp")
    processing.runalg("saga:reclassifygridvalues",BasePath+name+".tif",0,1,0,0,0,1,2,0,"0,0,0,0,0,0,0,0,0",0,True,0,True,0,BasePath+name+"basins0.tif")

    for j in range(0,endpointsLowerSort.shape[0]):
        print "processing " + name + " segment " + str(j+1)+ " of " + str(endpointsLowerSort.shape[0])
#        extract watershed to temp.tif
        processing.runalg("grass:r.water.outlet",BasePath+name+"_flowdir.tif",endpointsLowerSort[j][3],endpointsLowerSort[j][4],getExtCords(wshedDefRaster),0,BasePath+name+"temp"+str(j)+".tif")
#        reclass to segidx / zero        
        #processing.runalg("saga:reclassifygridvalues",BasePath+name+"Temp/temp_"+str(j)+".tif",0,1,2,0,0,1,2,0,"0,0,0,0,0,0,0,0,0",0,True,0,True,0,BasePath+name+"Temp/tempSegID"+str(j)+".tif")
        inStr = BasePath+name+"temp"+str(j) + ".tif"
        val=int(endpointsLowerSort[j][2])
        outStr = BasePath+name+"tempSegID"+str(j)+".tif"
       # print inStr + ", " +str(val) + ", " + outStr
        processing.runalg("saga:reclassifygridvalues",inStr,0,1,val,0,0,1,2,0,"0,0,0,0,0,0,0,0,0",0,True,0,True,0,outStr)
#        merge with basins.tif to form merged.tif
        processing.runalg("grass:r.patch",BasePath+name+"basins"+str(j)+".tif"+";"+BasePath+name+"tempSegID"+str(j)+".tif",True,getExtCords(wshedDefRaster),0,BasePath+name+"basins"+str(j+1)+".tif")
#        delete basins.tif
        #deleteRasters(BasePath,['basins','temp','tempSegID'])
#        rename merged.tif to basins.tif
        #os.rename(BasePath+'merged.tif',BasePath+'basins.tif')
        #deleteRasters(BasePath,'merged')

    os.rename(BasePath+name+"basins"+str(j+1)+".tif",BasePath+name+"Basins.tif")
    processing.runalg("grass:r.to.vect",BasePath+name+"Basins.tif",2,False,getExtCords(wshedDefRaster),0,BasePath+name+"BasinsShape")
    #processing.runalg("qgis:zonalstatistics",BasePath+name+"_Dem.tif",1,BasePath+name+"BasinsShape.shp","_",True,BasePath+name+"AreaElevationStats.shp")
    
    
    #combine half_watersheds raster with AreaElevationStats shp into HalfContibAreas shp
    if os.path.exists(BasePath +name+"_half_watersheds_adj.tif"):
        processing.runalg("grass:r.to.vect",BasePath +name+"_half_watersheds_adj.tif",2,False,getExtCords(wshedDefRaster),0,BasePath+name+"HalfWshedsVector")
    else:
        processing.runalg("grass:r.to.vect",BasePath +name+"_half_watersheds.tif",2,False,getExtCords(wshedDefRaster),0,BasePath+name+"HalfWshedsVector")
    
    processing.runalg("grass:v.overlay",BasePath+name+"BasinsShape.shp",0,BasePath+name+"HalfWshedsVector.shp",0,False,getExtCords(wshedDefRaster),0.0001,0.0001,0,BasePath+name+"FinalAreas")
    processing.runalg("qgis:addautoincrementalfield",BasePath+name+"FinalAreas.shp",BasePath+name+"FinalAreasIDX")
    processing.runalg("qgis:exportaddgeometrycolumns",BasePath+name+"FinalAreasIDX.shp",0,BasePath+name+"FinalAreasArea")
    processing.runalg("qgis:zonalstatistics",BasePath+name+"_Dem.tif",1,BasePath+name+"FinalAreasArea.shp","_",True,BasePath+name+"FinalFinalAreas.shp")
    #save ^ this ^ as .csv
    finalContribAreasStats=QgsVectorLayer(BasePath + name+ "FinalFinalAreas.shp", "FinalFinalAreas","ogr")
    QgsVectorFileWriter.writeAsVectorFormat(finalContribAreasStats,BasePath+name+"finalContribAreasStats.csv","utf-8",None,"CSV")

    del finalContribAreasStats
    #record topology 
   
    processing.runalg("qgis:fixeddistancebuffer",BasePath+name+"EndpointsFinal.shp",cellSize*1.5,5,False,BasePath+name+"PointBuffer")
    processing.runalg("qgis:intersection",BasePath+name+"PointBuffer.shp",BasePath+name+"PointBuffer.shp",BasePath+name+"RedundantJunctions.shp")
    topoTableLayer=QgsVectorLayer(BasePath + name+ "RedundantJunctions.shp", "RedundantJunctions","ogr")
    QgsVectorFileWriter.writeAsVectorFormat(topoTableLayer,BasePath+name+"topoTable.csv","utf-8",None,"CSV")
    
    del topoTableLayer
    
    # branch of endpoints vector for elev stats
    processing.runalg("grass:v.sample",BasePath+name+"StreamSegmentEndpointsSegIDX.shp","SegIDX",BasePath+name+"_Dem.tif",1,False,False,getExtCords(wshedDefRaster),-1,0.0001,0,BasePath+name+"EndpointsElev.shp")
    endpointsElev=QgsVectorLayer(BasePath+name+"EndpointsElev.shp","EndpoiontsElev","ogr")
    QgsVectorFileWriter.writeAsVectorFormat(endpointsElev,BasePath+name+"endpointsElevation.csv","utf-8",None,"CSV")
    del endpointsElev
    # add lengths to stream segments table
    processing.runalg("qgis:exportaddgeometrycolumns",BasePath+name+"StreamSegmentsIDX.shp",0,BasePath+name+"StreamSegmentsLength")
    strSegs = QgsVectorLayer(BasePath+name+"StreamSegmentsLength.shp","StreamSegmentsLength","ogr")
    QgsVectorFileWriter.writeAsVectorFormat(strSegs,BasePath+name+"strSegs.csv","utf-8",None,"CSV")
    del strSegs
#for j in range(1,endpointsLowerSort.shape[0]):
#    print "processing " + name + " segment " + str(j)+ " of " + str(endpointsLowerSort.shape[0])
##        extract watershed to temp.tif
#    processing.runalg("grass:r.water.outlet",BasePath+name+"_flowdir.tif",endpointsLowerSort[j][3],endpointsLowerSort[i][4],getExtCords(wshedDefRaster),0,BasePath+"temp.tif")
##        reclass to segidx / zero        
#    processing.runalg("saga:reclassifygridvalues",BasePath+"temp.tif",0,1,endpointsLowerSort[j][2],0,0,1,2,0,"0,0,0,0,0,0,0,0,0",0,True,0,True,0,BasePath+"tempSegID.tif")
##        merge with basins.tif to form merged.tif
#    processing.runalg("grass:r.patch",BasePath+"basins.tif"";"+BasePath+"tempSegID.tif",True,getExtCords(wshedDefRaster),0,BasePath+"merged.tif")
##        delete basins.tif
#    deleteRasters(BasePath,['basins','temp','tempSegID'])
##        rename merged.tif to basins.tif
#    os.rename(BasePath+'merged.tif',BasePath+'basins.tif')
#    deleteRasters(BasePath,'merged')
#
#
#    
#    
#    if os.path.exists(BasePath+"TempContribAreas"+name):
#        shutil.rmtree(BasePath+"TempContribAreas"+name)
#    os.mkdir(BasePath+"TempContribAreas"+name)
#    #iterate throug points, define contrib areas
#    strSegPts=QgsVectorLayer(BasePath + name+"StreamSegmentPointsXY.shp", "StreamSegs","ogr")
#    allPts=processing.features(strSegPts)
#    for i in range(1,((strSegPts.featureCount()+2)/2)):
#        processing.runalg("qgis:extractbyattribute",strSegPts,"AUTO",0,i,BasePath+"TempSelectPoints")
#        strSegPtsSelect=QgsVectorLayer(BasePath+"TempSelectPoints.shp", "StreamPtsSelect","ogr")
#        if strSegPtsSelect.featureCount()==2:
#            print "processing " + name + "segment " + str(i)
#            pointID="upper"
#            for point in strSegPtsSelect.getFeatures():
#                processing.runalg("grass:r.water.outlet",BasePath+name+"_flowdir.tif",point.geometry().asPoint()[0],point.geometry().asPoint()[1],getExtCords(wshedDefRaster),0,BasePath+"WshedArea_"+pointID)
#                pointID="lower"
#            #reclass as 0; AUTO (id), subtract upper contrib area raster from lower
#            processing.runalg("saga:reclassifygridvalues",BasePath+"WshedArea_upper.tif",0,1,i,0,0,1,2,0,"0,0,0,0,0,0,0,0,0",0,True,0,True,0,BasePath+"WshedArea_reclass_upper")
#            processing.runalg("saga:reclassifygridvalues",BasePath+"WshedArea_lower.tif",0,1,i,0,0,1,2,0,"0,0,0,0,0,0,0,0,0",0,True,0,True,0,BasePath+"WshedArea_reclass_lower")
#            processing.runalg("grass:r.mapcalculator",BasePath+"WshedArea_reclass_lower.tif",BasePath+"WshedArea_reclass_upper.tif",None,None,None,None,"A-B",getExtCords(wshedDefRaster),0,BasePath+"/TempContribAreas"+name+"/"+str(i))
#            #processing.runalg("grass:r.to.vect",BasePath+"TempContribArea.tif",2,False,getExtCords(wshedDefRaster),0,BasePath+"/TempContribAreas"+name+"/"+str(i))
#            #Delete upper and lower area rasters
#            deleteRasters(BasePath,["WshedArea_upper.tif","WshedArea_lower.tif","WshedArea_reclass_upper.tif","WshedArea_reclass_lower.tif"])
#        else: 
#            print "Oops: Select Feature Count != 2 "
#        del strSegPtsSelect
#        QgsMapLayerRegistry.instance().removeMapLayer(strSegPtsSelect.id())
#        
    
    
    
    
    
    #allSegs=StreamSegs.getFeatures()
 #   for point in allPts:
  #      processing.runalg("grass:v.to.points",seg,ReachLength,False,False,False,getExtCords(wshedDefRaster),-1,0.0001,0,BasePath+"OneSegPoints")
   #     processing.runalg("qgis:exportaddgeometrycolumns",BasePath+"temp/OneSegPoints",0,BasePath+"temp/OneSegPointsXY")
    #    segPoints=QgsVectorLayer(BasePath + "temp/OneSegPointsXY.shp", "segPoints","ogr")
    #    segPointsFeatures=segPoints.getFeatures()
   #     for point in segPointsFeatures:
   #         xy=point.geometry().asPoint()
   #         print(xy)
    
    #processing.runalg("grass:v.to.points",BasePath+name+"StreamSegmentsIDX.shp",ReachLength,False,False,False,getExtCords(wshedDefRaster),-1,0.0001,0,BasePath+name+"StreamSegmentPointsDuplicates")
    #processing.runalg("qgis:deleteduplicategeometries",BasePath+name+"StreamSegmentPointsDuplicates.shp",BasePath+name+"StreamSegmentPointsUnique")
    #processing.runalg("qgis:exportaddgeometrycolumns",BasePath+name+"StreamSegmentPointsUnique.shp",0,BasePath+name+"StreamSegmentPointsXY")
    #iterate throug points, define contrib areas
print "end time: " + str(datetime.datetime.now().time())

