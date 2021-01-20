import sys
import os
import datetime

#import xml.etree.ElementTree as ET

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
# Custom param
expectedTypes['FPS'] = '<float>'
expectedTypes['cdlFile'] = '<string>'
expectedTypes['lutFile'] = '<string>'
print sys.argv
params = ParseCommandLine( expectedTypes, sys.argv )

inFilePattern = params['inFile']
outFile = params['outFile'].rsplit(".", 1)[0] + ".mov"
outFolder = params['outFolder']
userName = params['username']
version = params['version']
FPS = params['FPS']

slateFile = params['slateFile']
cdlFile = params['cdlFile']
lutFile = params['lutFile']

#----------------------------------------------------------------------------------------------------------------------------------------------------------------
# Read cdl and lut properties from files

# Read CDL file
#tree = ET.parse(cdlFile)
#root = tree.getroot()

#----------------------------------------------------------------------------------------------------------------------------------------------------------------
# Final quicktime properties
outWidth = 1920
outHeight = 1080

videoCodec = "H264"
quality = 100
# KBitRate = 8000

#----------------------------------------------------------------------------------------------------------------------------------------------------------------
# initialize variables

# Get list of all frame number
frames = FrameRangeToFrames( params['frameList'] )
totalFrames = len( frames )

# Extra frame as slate
# firstFrameNum = frames[0] + 8
firstFrameNum = frames[0]
slateFrameNum = frames[0] - 1
# frames = [slateFrameNum] + frames

# Extract information from file hierachy
inFileSplit = inFilePattern.split('\\')

jobName = inFileSplit[2].replace('_', ' ')
seqName = inFileSplit[4].replace('_', ' ')
shotName = inFileSplit[5]
# inFileSplit[-2] = "CustomDraftAnno"

# define output file pattern with hashtag as frame number
outFileNamePattern = inFileSplit[9].rsplit('.', 1)[0] + '.jpg'
outFilePathPattern = os.path.join( outFolder, outFileNamePattern )

#----------------------------------------------------------------------------------------------------------------------------------------------------------------
# Create Slate frame
# templateSlate = "M:\\JOBS\\NETFLIX_TEST\\_Edit\\RAW\\4K Test Materials\\CadmusCompTest\\CadmusCompTest\\CadmusSlate01.jpg"

# Netflix required slate as frame 1000 on every submitted shot
slateFramePath = ReplaceFilenameHashesWithNumber( inFilePattern, slateFrameNum )
firstFramePath = ReplaceFilenameHashesWithNumber( inFilePattern, firstFrameNum )

# Create Slate image 1980x1080
slateFrame = Draft.Image.ReadFromFile( slateFile )

# Create first frame as thumbnail on top of slate
firstFrame = Draft.Image.ReadFromFile( firstFramePath )

exrWidth = firstFrame.width
exrHeight = firstFrame.height

# Slate annotation info
slateAnnoInfo = Draft.AnnotationInfo()
slateAnnoInfo.PointSize = int( 1080 * 0.042 )
slateAnnoInfo.Color = Draft.ColorRGBA( 1.0, 1.0, 1.0, 1.0 )
slateAnnoInfo.BackgroundColor = Draft.ColorRGBA( 0.0, 0.0, 0.0, 0.0 )

titleAnnoInfo = Draft.AnnotationInfo()
titleAnnoInfo.PointSize = int( 1080 * 0.11 )
# titleAnnoInfo.FontType = "Cambria"
titleAnnoInfo.Color = Draft.ColorRGBA( 1.0, 1.0, 1.0, 1.0 )
titleAnnoInfo.BackgroundColor = Draft.ColorRGBA( 0.0, 0.0, 0.0, 0.0 )

# Create and comp draft text to the slate
titleSlateAnnotation = Draft.Image.CreateAnnotation( "LOVE 101 EP.01", titleAnnoInfo)

shotSlateAnnotation = Draft.Image.CreateAnnotation( shotName, slateAnnoInfo )
dateSlateAnnotation = Draft.Image.CreateAnnotation( datetime.datetime.now().strftime("%m/%d/%Y"), slateAnnoInfo )
versionSlateAnnotation = Draft.Image.CreateAnnotation( version, slateAnnoInfo )
totalFrameSlateAnnotation = Draft.Image.CreateAnnotation( str(totalFrames), slateAnnoInfo )

slateFrame.CompositeWithPositionAndAnchor(titleSlateAnnotation, 0.5, 0.92, Draft.Anchor.North, Draft.CompositeOperator.OverCompositeOp)

slateFrame.CompositeWithPositionAndAnchor(shotSlateAnnotation, 0.125, 0.612, Draft.Anchor.West, Draft.CompositeOperator.OverCompositeOp)
slateFrame.CompositeWithPositionAndAnchor(dateSlateAnnotation, 0.125, 0.56, Draft.Anchor.West, Draft.CompositeOperator.OverCompositeOp)
slateFrame.CompositeWithPositionAndAnchor(versionSlateAnnotation, 0.125, 0.508, Draft.Anchor.West, Draft.CompositeOperator.OverCompositeOp)
slateFrame.CompositeWithPositionAndAnchor(totalFrameSlateAnnotation, 0.125, 0.456, Draft.Anchor.West, Draft.CompositeOperator.OverCompositeOp)
#slateFrame.CompositeWithPositionAndAnchor(noteSlateAnnotation, 0.125, 0.404, Draft.Anchor.West, Draft.CompositeOperator.OverCompositeOp)

# Create duplicate of slate
draftSlateFrame = Draft.Image.CreateImage( outWidth, outHeight, ['R', 'G', 'B'])
draftSlateFrame.Copy(slateFrame)
draftSlateFrame.SetChannel( 'A', 1.0 )

firstFrame.Resize(640, 360)
firstFrame.SetChannel( 'A', 1.0 )

draftFirstFrame = Draft.Image.CreateImage( 640, 360)
draftFirstFrame.Copy(firstFrame)

# Linear EXR >> RGB
linearToRGBInvLUT = Draft.LUT.CreateSRGB().Inverse()
linearToRGBLUT = Draft.LUT.CreateSRGB()#.Inverse()
linearToRGBInvLUT.Apply( slateFrame )
linearToRGBLUT.Apply( draftFirstFrame )
draftFirstFrame.SetChannel( 'A', 1.0 )

lut = Draft.LUT.CreateOCIOProcessorFromFile(lutFile)
lut.Apply(draftFirstFrame)

slateFrame.Composite(firstFrame, 0.577, 0.445, Draft.CompositeOperator.CopyCompositeOp)
slateFrame.Resize(3840, 2160)

draftSlateFrame.Composite(draftFirstFrame, 0.577, 0.445, Draft.CompositeOperator.CopyCompositeOp)
draftSlateFrame.Resize(3840, 2160)

# If we comp slate with 4K resolution. If they want plate size delivery, just resize the slate boarder to match
if slateFrame.height != exrHeight or slateFrame.width != exrWidth:
	slateFrame.Resize(exrWidth, exrHeight, 'fit')

# Write the extra slate frame as -1 of first frame.
slateFrame.WriteToFile( slateFramePath )

#----------------------------------------------------------------------------------------------------------------------------------------------------------------
# Make black box bar mask for draft

bbbm = Draft.Image.CreateImage( 1920, 1080 )
bbbm.SetToColor( Draft.ColorRGBA( 0.0, 0.0, 0.0, 1.0 ) )

alpha = Draft.Image.CreateImage( 1920, 960 )
alpha.SetToColor( Draft.ColorRGBA( 0.0, 0.0, 0.0, 0.0 ) )

bbbm.CompositeWithAnchor( alpha, Draft.Anchor.Center, Draft.CompositeOperator.CopyOpacityCompositeOp )

#----------------------------------------------------------------------------------------------------------------------------------------------------------------
# Make Draft

# Create annotation info
draftAnnoInfo = Draft.AnnotationInfo()
draftAnnoInfo.PointSize = int( outHeight * 0.030 )
#draftAnnoInfo.Color = Draft.ColorRGBA( 0.97, .98, .99, 1.0 )
draftAnnoInfo.Color = Draft.ColorRGBA( 1.0, 1.0, 1.0, 1.0 )
draftAnnoInfo.BackgroundColor = Draft.ColorRGBA( 0.0, 0.0, 0.0, 0.0 )

# Create video annotation
vendorAnnotation = Draft.Image.CreateAnnotation('MYLIAISONVFX', draftAnnoInfo)
dateAnnotation = Draft.Image.CreateAnnotation(datetime.datetime.now().strftime("%m/%d/%Y"), draftAnnoInfo )
versionAnnotation = Draft.Image.CreateAnnotation(version, draftAnnoInfo )
notesAnnotation = Draft.Image.CreateAnnotation('NOTE', draftAnnoInfo )

progressCounter = 0;
encoder = Draft.VideoEncoder( outFile, fps = FPS, quality=quality, width=outWidth, height=outHeight, codec=videoCodec )

# NETFlix want us to apply their editorial color pipeline to our quicktime draft when hand in the shot.

# Write slate frame as jpg and first frame of .mov
draftSlateFrame.Resize( outWidth, outHeight, type='fit' )
draftSlateFrame.SetChannel( 'A', 1.0 )

outFrame = ReplaceFilenameHashesWithNumber( outFilePathPattern, slateFrameNum )
draftSlateFrame.WriteToFile( outFrame )

encoder.EncodeNextFrame( slateFrame )

# Apply burn in and write frames
for frameNumber in frames:
	print( "Processing Frame: %d..." % frameNumber )
	inFrame = ReplaceFilenameHashesWithNumber( inFilePattern, frameNumber )

	# Create frame as video frame
	vidFrame = Draft.Image.ReadFromFile( inFrame )
	
	# Linear EXR >> RGB
	linearToRGBLUT = Draft.LUT.CreateSRGB()#.Inverse()
	linearToRGBLUT.Apply( vidFrame )

	# cdlLUT = Draft.LUT.CreateOCIOProcessorFromFile(cdlFile)
	# cdlLUT.Apply(vidFrame)

	lut = Draft.LUT.CreateOCIOProcessorFromFile(lutFile)
	lut.Apply(vidFrame)

	vidFrame.Resize( outWidth, outHeight, type='fit' ) 
	vidFrame.SetChannel( 'A', 1.0 )

	framesAnnotation = Draft.Image.CreateAnnotation( str( frameNumber ), draftAnnoInfo )

	# Compasite black box bar mask on video frame
	vidFrame.CompositeWithAnchor( bbbm, Draft.Anchor.Center, Draft.CompositeOperator.OverCompositeOp )

	# # Composite annotation on video frame
	vidFrame.CompositeWithAnchor( vendorAnnotation, Draft.Anchor.NorthWest, Draft.CompositeOperator.OverCompositeOp )
	vidFrame.CompositeWithAnchor( dateAnnotation, Draft.Anchor.NorthEast, Draft.CompositeOperator.OverCompositeOp )
	vidFrame.CompositeWithAnchor( versionAnnotation, Draft.Anchor.SouthWest, Draft.CompositeOperator.OverCompositeOp )
	# vidFrame.CompositeWithAnchor( notesAnnotation, Draft.Anchor.South, Draft.CompositeOperator.OverCompositeOp )
	vidFrame.CompositeWithAnchor( framesAnnotation, Draft.Anchor.SouthEast, Draft.CompositeOperator.OverCompositeOp )

	# Write draft
	outFrame = ReplaceFilenameHashesWithNumber( outFilePathPattern, frameNumber )
	vidFrame.WriteToFile( outFrame )

	# Write video frame
	encoder.EncodeNextFrame( vidFrame )

	progressCounter = progressCounter + 1
	progress = progressCounter * 100 / totalFrames
	print( "Progress: %i%%" % progress )

#Finalize the encoding process
encoder.FinalizeEncoding()
