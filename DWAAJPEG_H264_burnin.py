import sys
import os
import datetime

import Draft
from DraftParamParser import *

#----------------------------------------------------------------------------------------------------------------------------------------------------------------
# Extract params
expectedTypes = dict()
expectedTypes['frameList'] = '<string>'
expectedTypes['inFile'] = '<string>'
expectedTypes['outFile'] = '<string>'
expectedTypes['outFolder'] = '<string>'
expectedTypes['username'] = '<string>'
expectedTypes['version'] = '<string>'
expectedTypes['FPS'] = '<float>'

params = ParseCommandLine( expectedTypes, sys.argv )

frames = FrameRangeToFrames( params['frameList'] )
inFilePattern = params['inFile']
outFile = params['outFile'].rsplit(".", 1)[0] + ".mp4"
outFolder = params['outFolder']
userName = params['username']
#version = params['version']
FPS = params['FPS']

#----------------------------------------------------------------------------------------------------------------------------------------------------------------
# Extract information from file hierachy
inFileSplit = inFilePattern.split('\\')

jobName = inFileSplit[2].replace('_', ' ')
seqName = inFileSplit[4].replace('_', ' ')
shotName = inFileSplit[5]
version = inFileSplit[8][1:]

# define output file pattern with hashtag as frame number
outFileNamePattern = inFileSplit[9].rsplit('.', 1)[0] + '.jpg'
outFilePathPattern = os.path.join( outFolder, outFileNamePattern )

#----------------------------------------------------------------------------------------------------------------------------------------------------------------
# initialize draft properties
outWidth = 1920
outHeight = 1080

videoCodec = "H264"
quality = 100
KBitRate = 8000

encoder = Draft.VideoEncoder( outFile, fps = FPS, quality=quality, width=outWidth, height=outHeight, codec=videoCodec )

#----------------------------------------------------------------------------------------------------------------------------------------------------------------
# Create annotation info
annotationInfo = Draft.AnnotationInfo()
annotationInfo.PointSize = int( outHeight * 0.020 )
#annotationInfo.Color = Draft.ColorRGBA( 0.97, .98, .99, 1.0 )
annotationInfo.Color = Draft.ColorRGBA( 1.0, 1.0, 1.0, 1.0 )
annotationInfo.BackgroundColor = Draft.ColorRGBA( 0.0, 0.0, 0.0, 0.5 )

# Create draft annotation
draftDateAnnotation = Draft.Image.CreateAnnotation(userName + "   |   " + datetime.datetime.now().strftime("%d/%m/%Y"), annotationInfo )
entityAnnotation = Draft.Image.CreateAnnotation(params['inFile'], annotationInfo )

# Create video annotation
vidDateAnnotation = Draft.Image.CreateAnnotation('COMP :  ' + datetime.datetime.now().strftime("%d %b %Y"), annotationInfo )
jobAnnotation = Draft.Image.CreateAnnotation('PROJECT :  ' + jobName, annotationInfo )
sequenceAnnotation = Draft.Image.CreateAnnotation('SEQUENCE :  ' + seqName, annotationInfo )
shotAnnotation = Draft.Image.CreateAnnotation('SHOT :  ' + shotName.strip("SH") + '    ' + 'VERSION :  ' + version, annotationInfo )

#----------------------------------------------------------------------------------------------------------------------------------------------------------------
#Main loop
progressCounter = 0;
totalFrames = len( frames )

for frameNumber in frames:
	print( "Processing Frame: %d..." % frameNumber )
	inFrame = ReplaceFilenameHashesWithNumber( inFilePattern, frameNumber )
	
	# Create frame for draft
	draftImage = Draft.Image.ReadFromFile( inFrame ) 
	draftImage.Resize( outWidth, outHeight, type='fit' ) # none,width,height,fill,fit,distort# original fit
	draftImage.SetChannel( 'A', 1.0 )

	# Create frame as video frame
	vidFrame = Draft.Image.ReadFromFile( inFrame )
	vidFrame.Resize( outWidth, outHeight, type='fit' ) 
	vidFrame.SetChannel( 'A', 1.0 )

	lut = Draft.LUT.CreateSRGB()
	lut.Apply( draftImage )
	lut.Apply( vidFrame )

	framesAnnotation = Draft.Image.CreateAnnotation( str( frameNumber ), annotationInfo )

	# Composite annotation on draft
	draftImage.CompositeWithAnchor( draftDateAnnotation, Draft.Anchor.NorthEast, Draft.CompositeOperator.OverCompositeOp )
	draftImage.CompositeWithAnchor( entityAnnotation, Draft.Anchor.NorthWest, Draft.CompositeOperator.OverCompositeOp )
	draftImage.CompositeWithAnchor( framesAnnotation, Draft.Anchor.South, Draft.CompositeOperator.OverCompositeOp )

	# Composite annotation on video frame
	vidFrame.CompositeWithAnchor( shotAnnotation, Draft.Anchor.NorthEast, Draft.CompositeOperator.OverCompositeOp )
	vidFrame.CompositeWithAnchor( sequenceAnnotation, Draft.Anchor.North, Draft.CompositeOperator.OverCompositeOp )
	vidFrame.CompositeWithAnchor( framesAnnotation, Draft.Anchor.South, Draft.CompositeOperator.OverCompositeOp )
	vidFrame.CompositeWithAnchor( jobAnnotation, Draft.Anchor.NorthWest, Draft.CompositeOperator.OverCompositeOp )
	vidFrame.CompositeWithAnchor( vidDateAnnotation, Draft.Anchor.SouthWest, Draft.CompositeOperator.OverCompositeOp )

	# Write draft
	outFrame = ReplaceFilenameHashesWithNumber( outFilePathPattern, frameNumber )
	draftImage.WriteToFile( outFrame )

	# Write video frame
	encoder.EncodeNextFrame( vidFrame )

	progressCounter = progressCounter + 1
	progress = progressCounter * 100 / totalFrames
	print( "Progress: %i%%" % progress )

#Finalize the encoding process
encoder.FinalizeEncoding()

#----------------------------------------------------------------------------------------------------------------------------------------------------------------
print(inFileSplit[2])
FILESERV = os.getenv('FILE_SERVER')
if not FILESERV:
	FILESERV = "\\\\serverraid02"

sys.path.append(FILESERV+"\\CherryTechnic$\\SHOTGUN\\python-api-3.0.32")

import shotgun_api3

sgShotInfo = None

# if inFileSplit[2] == "CM_ERICA":
# 	sg = shotgun_api3.Shotgun("https://flavourworks.shotgunstudio.com", script_name="CM Script", 
# 		api_key="ysaeef*c2akscetotDapitayb")
	
# 	project = "ERICA"
# 	entityType = "CustomEntity03"

# 	filters = [["project.Project.name", "is", project], ["code", "is", "I-031"]]

# 	fields = ["id", "description"]

# 	sgShotInfo = sg.find_one(entityType, filters, fields)


if inFileSplit[2] == "FORTITUDE_S3_EP2":
	sg = shotgun_api3.Shotgun("https://myliaison.shotgunstudio.com", script_name="Nuke Uploader2",
		api_key="4fd8f1a96b6e6e68aeb5f30d5af32d74a36a2c1c8be6114e053a306201f73614")
	
	project = inFileSplit[2]
	entityType = "Shot"

	filters = [["project.Project.name", "is", project], ["code", "is", shotName], ["sg_sequence.Sequence.code", "is", inFileSplit[4]] ]

	fields = ["id", "description", "project.Project.id"]

	sgShotInfo = sg.find_one(entityType, filters, fields)


if sgShotInfo:
	data = {"project": {"type": "Project", "id": sgShotInfo["project.Project.id"]},#86
			"entity": {"type": entityType, "id": sgShotInfo["id"]},
			"code": version,
			"frame_count": totalFrames,
			"frame_range": "{0}-{1}".format(frames[0], frames[-1]) ,
			"sg_first_frame": frames[0],
			"sg_last_frame": frames[-1],
			"sg_path_to_frames": inFilePattern,
			"sg_path_to_movie": outFile,
			}

	sgResult = sg.create("Version", data)

	sg.upload("Version", sgResult["id"], outFile, field_name="sg_uploaded_movie")
