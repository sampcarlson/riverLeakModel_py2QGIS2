segmentDetail=function(nodeIDs){
  conn=odbcConnect("neo_tables_from_q_ANSI",uid = "root", pwd = "password")
  
  #nodeIDs = 65:68
  
  wherePart = paste0(paste0("FromCell = 'channel_",nodeIDs,"'", " OR ToCell = 'channel_", nodeIDs, "'"), collapse = " OR ")
  matrixEdge = sqlQuery(conn, paste("SELECT * FROM matrix_edge WHERE", wherePart), stringsAsFactors = F)
  
  wherePart = paste0(paste0("ID = 'channel_",nodeIDs,"'"), collapse = " OR ")
  matrixCell = sqlQuery(conn, paste("SELECT * FROM matrix_cell WHERE", wherePart), stringsAsFactors = F)
  output = sqlQuery(conn, "SELECT * FROM RiverLeak_Output WHERE modelTick = 300", stringsAsFactors = F)
  
  #head(output)
  #tail(output)
  #head(matrixCell)
  #head(matrixEdge)
  
  preAndPost = strsplit(output$holonName, "-") 
  pre = sapply(preAndPost, "[", 1)
  post = sapply(preAndPost, "[", 2)
  is.cell = is.na(post)
  
  output$ID = pre
  output$FromCell = NA
  output$FromCell[is.cell] = pre[is.cell]
  output$ToCell = NA
  output$ToCell[is.cell] = pre[is.cell]
  output$face = NA
  output$face[!is.cell] = post[!is.cell]
  
  matrixCell$FromCell = matrixCell$ID
  matrixCell$ToCell = matrixCell$ID
  
  fromOutput = join(matrixEdge, output, by = "FromCell", type="inner")[,c("ID", "EdgeType", "modelTick", "modelTime", "stateVal", "svValue", "face", "FromCell")]
  fromOutput = cast(fromOutput, ID  ~ stateVal, value = "svValue")
  names(fromOutput)[2:length(fromOutput)] = paste0("from.", names(fromOutput)[2:length(fromOutput)])
  toOutput = join(matrixEdge, output, by = "ToCell", type="inner")[,c("ID", "EdgeType", "modelTick", "modelTime", "stateVal", "svValue", "face", "ToCell")]
  toOutput = cast(toOutput, ID  ~ stateVal, value = "svValue")
  names(toOutput)[2:length(toOutput)] = paste0("to.", names(toOutput)[2:length(toOutput)])
  edgeOutput = join(matrixEdge, output, by = "ID", type = "inner")[,c("ID", "EdgeType", "modelTick", "modelTime", "stateVal", "svValue", "face", "ID")]
  edgeOutput = edgeOutput[edgeOutput$face != "from",]
  edgeOutput = cast(edgeOutput, ID +  EdgeType ~ stateVal, value = "svValue")
  
  #head(fromOutput)
  #head(toOutput)
  #head(edgeOutput)
  
  debug = join(edgeOutput, toOutput, by = "ID")
  debug = join(debug, fromOutput, by = "ID")
  return(debug)
}