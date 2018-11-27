# NEO db builder tool 5/5/2016

#temp date format: date="2014-09-08"
CreateDB=function(flowDate,tempDate,nConc,rebuild){
  #flowDate=tempDate="2014-09-08"
  #DefaultNConc=1
  require(waterData)
  require(RODBC)
  
  BasePath = "C:/Users/Sam/Desktop/spatial/QgisEnvironment/Active/d8_500_simple/"
  WshedName = "NSV"
  
  DefaultNConc=nConc   #ug/l
  endDate=as.Date(1,origin=flowDate)
  refQ_ls=(importDVs("402114105350101",sdate=flowDate,edate=endDate)$val[1]/(3.28084^3))*1000
  
  # flow function as of 5/2016 - return l/sec
  WaterYieldFunction = function(area,refQ){
    areas=(sum(area))
    ls=2.005e-08*areas*refQ_ls
    return(ls)
  }
  
  #this is not longer relevant - width is now calculated as f(q) in water.cell.channel.width
  WidthFunction = function(uaa){
    return ((uaa/1e6)*10)
  }
  StreamTempCoeffs=tempFit(tempDate)
  StreamTempFunction = function(coeffs,ptElev,ALF,lakeElev){
  return(max(0,(ALF*(coeffs[["li"]]+coeffs[["lc"]]*lakeElev)+(1-ALF)*(coeffs[["ei"]]+coeffs[["ec"]]*ptElev))))
    
  }
  
  RespRateFunction = function(coeffs,ptElev,ALF,lakeElev){
    streamTemp=StreamTempFunction(coeffs,ptElev,ALF,lakeElev)
    respRate=3.8*2.5^((streamTemp-8)/10)
    return(respRate)
  }
  
  
  #tables:
  #    neo table name            name used here
  #init_nitrate_face_loading = initNLoad
  #init_nitrate_face_removal = nitRemove
  #init_water_Cell_channel   = channelCharacteristics
  #init_water_face_loading   = waterLoad
  #matrix_cell               = segments
  #matrix_edge               = junctions (get rid of row.names?)
  
  
  topoTable <- read.csv(paste0(BasePath,WshedName,"topoTable.csv"), stringsAsFactors=FALSE)
  segmentsTable <- read.csv(paste0(BasePath,WshedName,"strSegs.csv"), stringsAsFactors=FALSE)
  contribAreasTable <- read.csv(paste0(BasePath,WshedName,"finalContribAreasStats.csv"), stringsAsFactors=FALSE)
  endpointsElevTable <- read.csv(paste0(BasePath,WshedName,"endpointsElevation.csv"), stringsAsFactors=FALSE)
  
  #this one for stream temp
  #strTempInfoTable = read.csv("C:/Users/Sam/Desktop/spatial/sites/nsvSegmentTempInfo.csv")
  #names(strTempInfoTable)=c("ID","ALF","MLE")
  #segmentsMerge = merge(segmentsTable,strTempInfoTable,by.x="AUTO",by.y="ID",all.x=T)
  
  ###-------------matrix_edge-------------###########
  
  #junctions table mirrors neo matrix_edge table
  segUaa = c(0,0)
  #Create approx 'SegUaa' field as max of endpoint uaas.  Indexed as segID
  for (s in unique(c(topoTable$SegIDX, topoTable$segidx_2))){
    segUaa[s]=max(c(topoTable$rast_val[topoTable$SegIDX==s],topoTable$rast_val_2[topoTable$segidx_2==s]))
  } 
  
  # identify junction groups for each intermediate point: reduandant, and does not include begin and end face points
#   junctions = read.csv(text="ID,EdgeType,FromCell,ToCell,EdgeIDX
#                      NaN,NaN,NaN,NaN,NaN")
#   faceSegs = NULL
#   jctID = 1
#   allPoints = unique(c(topoTable$PointIDX,topoTable$pointidx_2))
#   
  # Make a dataframe of pointIDX and pointUAA by segment.
  pointsBySeg = ddply(topoTable, c("SegIDX"), summarize, pt1 = min(PointIDX), pt2 = max(PointIDX))
  pointsBySeg = unique(merge(pointsBySeg, topoTable[,c("PointIDX", "rast_val")], by.x = "pt1", by.y = "PointIDX"))
  names(pointsBySeg)[names(pointsBySeg) == "rast_val"] = "pt1UAA"
  pointsBySeg = unique(merge(pointsBySeg, topoTable[,c("PointIDX", "rast_val")], by.x = "pt2", by.y = "PointIDX"))
  names(pointsBySeg)[names(pointsBySeg) == "rast_val"] = "pt2UAA"
  
  # if UAA is equal, there is a stream segment of length zero. Get rid of it.
  keepIt = pointsBySeg$pt1UAA != pointsBySeg$pt2UAA
  pointsBySeg = pointsBySeg[keepIt,]
  
  
  choose2 = pointsBySeg$pt1UAA < pointsBySeg$pt2UAA
  pointsBySeg$endPoint = pointsBySeg$pt1
  pointsBySeg$endPoint[choose2] = pointsBySeg$pt2[choose2]
  pointsBySeg$startPoint = pointsBySeg$pt1
  pointsBySeg$startPoint[!choose2] = pointsBySeg$pt2[!choose2]
  pointsBySeg$minUAA = apply(pointsBySeg[,c("pt1UAA", "pt2UAA")], 1, min)
  proximalPoints = merge(data.frame(endPoint = pointsBySeg[,"endPoint"]), topoTable[,c("PointIDX", "pointidx_2")], by.x = "endPoint", by.y = "PointIDX")
  
  keep = proximalPoints$pointidx_2 %in% pointsBySeg$startPoint
  proximalPoints = proximalPoints[keep,]
  proximalPoints = merge(proximalPoints, pointsBySeg[,c("startPoint", "minUAA")], by.x = "pointidx_2", by.y = "startPoint")
  targetUAAs = ddply(proximalPoints, "endPoint", summarize, lowestSegUAA = max(minUAA))
  edgePoints = merge(proximalPoints, targetUAAs, by.x = c("endPoint", "minUAA"), by.y = c("endPoint", "lowestSegUAA"))
  names(edgePoints)[names(edgePoints) == "pointidx_2"] = "startPoint"
  
  edges = merge(edgePoints, pointsBySeg[,c("endPoint", "SegIDX")], by = "endPoint")
  names(edges)[names(edges) == "SegIDX"] = "fromSegIDX"
  edges = merge(edges, pointsBySeg[,c("startPoint", "SegIDX")], by = "startPoint")
  names(edges)[names(edges) == "SegIDX"] = "toSegIDX"
  
  outPoint = pointsBySeg$endPoint[!(pointsBySeg$endPoint %in% proximalPoints$endPoint)]
  outSeg = pointsBySeg$SegIDX[pointsBySeg$endPoint == outPoint]
  
  junctions = data.frame(
    ID = paste0(edges$fromSegIDX, "_to_", edges$toSegIDX),
    EdgeType = 'advect',
    FromCell = paste0("channel_", edges$fromSegIDX),
    ToCell = paste0("channel_", edges$toSegIDX),
    stringsAsFactors = FALSE
  )
  
  addToJunctions = data.frame(
    ID = paste0("load_to_", pointsBySeg$SegIDX),
    EdgeType = "load",
    FromCell = "",
    ToCell = paste0("channel_", pointsBySeg$SegIDX)
  )
  
  junctions = rbind(junctions, addToJunctions)
  
  addToJunctions = data.frame(
    ID = paste0("remove_to_", pointsBySeg$SegIDX),
    EdgeType = "remove",
    FromCell = "",
    ToCell = paste0("channel_", pointsBySeg$SegIDX)
  )
  
  junctions = rbind(junctions, addToJunctions)
  junctions = rbind(junctions,c(paste0("outflow_to_",outSeg),'outflow',"",paste0("channel_",outSeg)))
  junctions$EdgeIDX = 1:nrow(junctions)
  
#   for (p in pointsBySeg$endPoint){
#     jctGroup = topoTable[topoTable$PointIDX==p | topoTable$pointidx_2==p,]
#     #print(jctGroup)
#     jctSegs = unique(c(jctGroup$SegIDx,jctGroup$segidx_2))
#     if (length(jctSegs)==1){
#       faceSegs = rbind(faceSegs,jctSegs)
#     } else {
#        
#       downSeg = jctSegs[which.max(segUaa[jctSegs])]
#       
#       
#       upSegs = jctSegs[jctSegs!=downSeg]
#       for (s in upSegs){
#         if (jctID == 1){
#           junctions$ID[1]=paste0(s,"_to_",downSeg)
#           junctions$EdgeType[1]='advect'
#           junctions$FromCell[1]=paste0("channel_",s)
#           junctions$ToCell[1]=paste0("channel_",downSeg)
#           junctions$EdgeIDX[1]=1
#         } else {
#           junctions = rbind(junctions,c(paste0(s,"_to_",downSeg),'advect',paste0("channel_",s),paste0("channel_",downSeg),jctID))
#         }
#         
#         jctID = jctID + 1
#       }
#     }
#   }
#   
  #define upstream and downstream faces
#   faceSegUaa=segUaa[faceSegs]
#   outSeg = faceSegs[which.max(faceSegUaa)]

#   jctID = jctID + 1
#   
#   
#   for (s in unique(c(topoTable$SegIDX, topoTable$segidx_2))){
#     #   junctions = rbind(junctions,c(paste0("r_load_to_",s),'load',"",paste0("channel_",s),jctID))
#     #   jctID = jctID + 1
#     #   junctions = rbind(junctions,c(paste0("l_load_to_",s),'load',"",paste0("channel_",s),jctID))
#     #   jctID = jctID + 1
#     junctions = rbind(junctions,c(paste0("load_to_",s),'load',"",paste0("channel_",s)))
#     jctID = jctID + 1
#     junctions = rbind(junctions,c(paste0("remove_to_",s),'remove',"",paste0("channel_",s)))
#     jctID = jctID + 1
#   }
#   
#   junctions = junctions[!duplicated(junctions[,c(1,2,3,4)]),]
  
  
  
  #####-----------matrix_cell------#######
  first=T
  segments = read.csv(text="ID,CellType,CellIDX
                    NaN,NaN,NaN")
  for (s in unique(c(topoTable$SegIDX, topoTable$segidx_2))){
    if (first==T){
      segments$ID[1]=paste0("channel_",s)
      segments$CellType[1]="channel"
      segments$CellIDX[1]=s
      first=F
    } else {
      segments = rbind(segments,c(paste0("channel_",s),"channel",s))
    }
    
  }
  
  
  #######---------init_water_cell_channel--------#############
  
  channelCharacteristics = segments
  names(channelCharacteristics)=c("ID","Length","Width")
  for (s in unique(c(topoTable$SegIDX, topoTable$segidx_2))){
    channelCharacteristics$Length[segments$CellIDX==s]=segmentsTable$length[segmentsTable$AUTO==s]
    channelCharacteristics$Width[segments$CellIDX==s]=WidthFunction(segUaa[s])
    
  }
  
  
  ###------------init_nitrate_face_loading--------#####
  
  # very simple right now - this will have to change
  initNLoad = read.csv(text="ID,NConc
                     NaN,NaN")
  loadIDs = junctions$ID[junctions$EdgeType=="load"]
  first = TRUE
  for (l in loadIDs){
    if (first == TRUE){
      initNLoad$ID[1]=l
      initNLoad$NConc[1]=DefaultNConc
      first = FALSE
    } else {
      initNLoad = rbind(initNLoad,c(l,DefaultNConc))
    }
  }
  
  
  ####----------init_nitrate_face_removal----------##########
  # temp based on elevation based on mean of endpoints
  nitRemove_ID=NaN
  nitRemove_Resp=NaN
  segTemp=NaN
  segID=NaN
  removeEdges=junctions[junctions$EdgeType=="remove",]
  for(i in 1:nrow(removeEdges)){
    endpointElevs=endpointsElevTable$rast_val[endpointsElevTable$pnt_val==strsplit(removeEdges$ToCell[i],"_")[[1]][2]]
    #  ALF=segmentsMerge$ALF[segmentsMerge$AUTO==strsplit(removeEdges$ToCell[i],"_")[[1]][2]]
    #  MLE=segmentsMerge$MLE[segmentsMerge$AUTO==strsplit(removeEdges$ToCell[i],"_")[[1]][2]]
    nitRemove_ID[i]=removeEdges$ID[i]
    nitRemove_Resp[i]=RespRateFunction(StreamTempCoeffs,mean(endpointElevs),0,0)
    segID[i]=strsplit(removeEdges$ToCell[i],"_")[[1]][2]
    segTemp[i]=StreamTempFunction(StreamTempCoeffs,mean(endpointElevs),0,0)

  }
  nitRemove=data.frame(ID=nitRemove_ID,RespRate=nitRemove_Resp)
  SegmentData=data.frame(ID=segID,Temp=segTemp,Resp=nitRemove_Resp)
  print(paste0("Mean Temperature: ",mean(segTemp)," Min: ",min(segTemp)," Max: ",max(segTemp)))
  
  ####-------------init_water_face_loading---------#########
  totalArea=0.0
  loadEdgeTable=junctions[junctions$EdgeType=="load",]
  waterLoad_ID=NaN
  waterLoad_ID_Numeric=NaN
  waterLoad_HydroGain=NaN
  areaRecordTest=NaN
  for (i in 1:nrow(loadEdgeTable)){ #for each load face
    waterLoad_ID_Numeric[i]=as.numeric(strsplit(loadEdgeTable$ID[i],"_")[[1]][3])
    waterLoad_ID[i]=loadEdgeTable$ID[i]
    Str_segID=strsplit(loadEdgeTable$ToCell[i],"_")[[1]][2]
    contribArea_Area=sum(contribAreasTable$area[contribAreasTable$value==Str_segID])
    totalArea=totalArea+contribArea_Area
    waterLoad_HydroGain[i]=WaterYieldFunction(contribArea_Area,refQ)
    areaRecordTest[i]=contribArea_Area
  }
  waterLoad=data.frame(ID_neo=waterLoad_ID,ID=waterLoad_ID_Numeric,HydrologicGain=waterLoad_HydroGain,Area=areaRecordTest)
  #print(head(waterLoad))
  SegmentData=merge(SegmentData,waterLoad,by="ID")
  names(SegmentData)[names(SegmentData=="Area")]="LateralArea"
  ######------------write tables to mysql-------##########
  
  #tables:
  #    neo table name            name used here
  #init_nitrate_face_loading = initNLoad
  #init_nitrate_face_removal = nitRemove
  #init_water_cell_channel   = channelCharacteristics
  #init_water_face_loading   = waterLoad
  #matrix_cell               = segments
  #matrix_edge               = junctions

  NeoDB=odbcConnect("neo_tables_from_q_ANSI",uid = "root", pwd = "password")
  sqlQuery(NeoDB, "DROP TABLE IF EXISTS init_nitrate_face_loading")
  sqlQuery(NeoDB,"CREATE TABLE init_nitrate_face_loading(
         ID varchar(255),
         NConc double,
         PRIMARY KEY (ID))")
  for (i in 1:nrow(initNLoad)){
    sqlQuery(NeoDB,paste("INSERT INTO init_nitrate_face_loading (ID, NConc) VALUES ('",
                        initNLoad$ID[i],"', '",
                        initNLoad$NConc[i],"');",sep=""))
  }
  
  
  #rebuild whole database - only do this the first run of each concentration-variable set
  if (rebuild==TRUE){
    
    
    sqlQuery(NeoDB, "DROP TABLE IF EXISTS init_nitrate_face_removal")
    sqlQuery(NeoDB,"CREATE TABLE init_nitrate_face_removal(
         ID varchar(255),
         RespRate double,
         PRIMARY KEY (ID))")
    for (i in 1:nrow(nitRemove)){
      sqlQuery(NeoDB,paste("INSERT INTO init_nitrate_face_removal (ID, RespRate) VALUES ('",
                          nitRemove$ID[i],"', '",
                          nitRemove$RespRate[i],"');",sep=""))
    }
    
    
    sqlQuery(NeoDB, "DROP TABLE IF EXISTS init_water_cell_channel")
    sqlQuery(NeoDB,"CREATE TABLE init_water_cell_channel(
         ID varchar(255),
         Length double,
         PRIMARY KEY (ID))")
    for (i in 1:nrow(channelCharacteristics)){
      sqlQuery(NeoDB,paste("INSERT INTO init_water_cell_channel (ID, Length) VALUES ('",
                          channelCharacteristics$ID[i],"', '",
                          channelCharacteristics$Length[i],"');",sep=""))
    }
    
    
    #init_water_face_loading   = waterLoad
    sqlQuery(NeoDB, "DROP TABLE IF EXISTS init_water_face_loading")
    sqlQuery(NeoDB,"CREATE TABLE init_water_face_loading(
         ID varchar(255),
         HydrologicGain double,
         PRIMARY KEY (ID))")
    for (i in 1:nrow(waterLoad)){
      sqlQuery(NeoDB,paste("INSERT INTO init_water_face_loading (ID, HydrologicGain) VALUES ('",
                          waterLoad$ID_neo[i],"', '",
                          waterLoad$HydrologicGain[i],"');",sep=""))
    }
    
    #matrix_cell   = segments
    sqlQuery(NeoDB, "DROP TABLE IF EXISTS matrix_cell")
    sqlQuery(NeoDB,"CREATE TABLE matrix_cell(
         ID varchar(255),
         CellType varchar(255),
         CellIDX int(11),
         PRIMARY KEY (CellIDX))")
    for (i in 1:nrow(segments)){
      sqlQuery(NeoDB,paste("INSERT INTO matrix_cell (ID, CellType, CellIDX) VALUES ('",
                          segments$ID[i],"', '",
                          segments$CellType[i],"', '",
                          segments$CellIDX[i],"');",sep=""))
    }
    
    #matrix_edge     = junctions
    sqlQuery(NeoDB, "DROP TABLE IF EXISTS matrix_edge")
    sqlQuery(NeoDB,"CREATE TABLE matrix_edge(
         ID varchar(255),
         EdgeType varchar(255),
         FromCell varchar(255),
         ToCell varchar(255),
         EdgeIDX int NOT NULL,
         PRIMARY KEY (EdgeIDX))")
    for (i in 1:nrow(junctions)){
      sqlQuery(NeoDB,paste("INSERT INTO matrix_edge (ID, EdgeType,FromCell,ToCell, EdgeIDX) VALUES ('",
                          junctions$ID[i],"', '",
                          junctions$EdgeType[i],"', '",
                          junctions$FromCell[i],"', '",
                          junctions$ToCell[i],"', '",
                          junctions$EdgeIDX[i],"');",sep=""))
    }
  }
  odbcCloseAll()
  #return this for visualization uses
  return(SegmentData)
}