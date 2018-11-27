import processing

outPath="C:\\Users\\Sam\\Desktop\\Spatial\\VisualisationData\\p1_mapData\\"
shpPath="C:/Users/Sam/Desktop/spatial/QgisEnvironment/Active/d8_500_simple/NSVStreamSegmentsLength.shp"
csvBasePath="file:///C:/Users/Sam/Desktop/spatial/VisualisationData/p1_mapData/3_27_reunited_NConc_"
csvAppend="?type=csv&geomType=none&subsetIndex=no&watchFile=no"



def loadJoinFunction(outPath,shpPath,csvBasePath,csvAppend,csvPath,csvName,joinedName):
    TempCsv=QgsVectorLayer(csvPath,csvName,"delimitedtext")
    QgsMapLayerRegistry.instance().addMapLayer(TempCsv)
    processing.runalg("qgis:joinattributestable",shpPath,csvName,"AUTO","ID",outPath+joinedName)
    QgsMapLayerRegistry.instance().removeMapLayer(TempCsv.id())
    join_shp=iface.addVectorLayer(outPath+joinedName+".shp",joinedName,"ogr")
    return


#0.1 linx
csvPath=csvBasePath+"0.1_linx.csv"+csvAppend
csvName="linx_csv_01"
joinedName="linx_01"
loadJoinFunction(outPath,shpPath,csvBasePath,csvAppend,csvPath,csvName,joinedName)


#0.1 warm
csvPath=csvBasePath+"0.1_combined_warm.csv"+csvAppend
csvName="warm_csv_01"
joinedName="warm_01"
loadJoinFunction(outPath,shpPath,csvBasePath,csvAppend,csvPath,csvName,joinedName)


#0.1 cool
csvPath=csvBasePath+"0.1_combined_cool.csv"+csvAppend
csvName="cool_csv_01"
joinedName="cool_01"
loadJoinFunction(outPath,shpPath,csvBasePath,csvAppend,csvPath,csvName,joinedName)


#10 linx
csvPath=csvBasePath+"10_linx.csv"+csvAppend
csvName="linx_csv_10"
joinedName="linx_10"
loadJoinFunction(outPath,shpPath,csvBasePath,csvAppend,csvPath,csvName,joinedName)


#10 warm
csvPath=csvBasePath+"10_combined_warm.csv"+csvAppend
csvName="warm_csv_10"
joinedName="warm_10"
loadJoinFunction(outPath,shpPath,csvBasePath,csvAppend,csvPath,csvName,joinedName)


#10 cool
csvPath=csvBasePath+"10_combined_cool.csv"+csvAppend
csvName="cool_csv_10"
joinedName="cool_10"
loadJoinFunction(outPath,shpPath,csvBasePath,csvAppend,csvPath,csvName,joinedName)


#1000 linx
csvPath=csvBasePath+"1000_linx.csv"+csvAppend
csvName="linx_csv_1000"
joinedName="linx_1000"
loadJoinFunction(outPath,shpPath,csvBasePath,csvAppend,csvPath,csvName,joinedName)


#1000 warm
csvPath=csvBasePath+"1000_combined_warm.csv"+csvAppend
csvName="warm_csv_1000"
joinedName="warm_1000"
loadJoinFunction(outPath,shpPath,csvBasePath,csvAppend,csvPath,csvName,joinedName)


#1000 cool
csvPath=csvBasePath+"1000_combined_cool.csv"+csvAppend
csvName="cool_csv_1000"
joinedName="cool_1000"
loadJoinFunction(outPath,shpPath,csvBasePath,csvAppend,csvPath,csvName,joinedName)
