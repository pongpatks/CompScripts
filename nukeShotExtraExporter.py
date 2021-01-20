# Example of a custom transcoder

import sys
import os
import tempfile
import re

import hiero.core
import hiero.core.nuke as nuke

from hiero.exporters import FnScriptLayout, FnNukeShotExporter, FnNukeShotExporterUI

import _nuke # import _nuke so it does not conflict with hiero.core.nuke

from hiero.exporters.FnExportUtil import (trackItemTimeCodeNodeStartFrame,
                            TrackItemExportScriptWriter,
                            createViewerNode
                            )

from hiero.ui.nuke_bridge import FnNsFrameServer as postProcessor

import glob
import shutil


class NukeShotExtraExporter(FnNukeShotExporter.NukeShotExporter):
  def __init__(self, initDict):
    """Initialize"""
    FnNukeShotExporter.NukeShotExporter.__init__( self, initDict )

  def updateItem(self, originalItem, localtime):
    # XXX
    FnNukeShotExporter.NukeShotExporter.updateItem(self, originalItem, localtime)

  def taskStep(self):
    # XXX
    try:
      return self._extraTaskStep()
    except:
      hiero.core.log.exception("NukeShotExporter.taskStep")

  def _extraTaskStep(self):
    # KUN IS THIS POSSIBLE???
    FnNukeShotExporter.FnShotExporter.ShotTask.taskStep(self)

    if self._nothingToDo:
      return False
    
    script = nuke.ScriptWriter()
    
    start, end = self.outputRange(ignoreRetimes=True, clampToSource=False)
    unclampedStart = start
    hiero.core.log.debug( "rootNode range is %s %s %s", start, end, self._startFrame )
    
    firstFrame = start
    if self._startFrame is not None:
      firstFrame = self._startFrame

    # if startFrame is negative we can only assume this is intentional
    if start < 0 and (self._startFrame is None or self._startFrame >= 0):
      # We dont want to export an image sequence with negative frame numbers
      self.setWarning("%i Frames of handles will result in a negative frame index.\nFirst frame clamped to 0." % self._cutHandles)
      start = 0
      firstFrame = 0

    # Clip framerate may be invalid, then use parent sequence framerate
    framerate = self._sequence.framerate()
    dropFrames = self._sequence.dropFrame()
    if self._clip and self._clip.framerate().isValid():
      framerate = self._clip.framerate()
      dropFrames = self._clip.dropFrame()
    fps = framerate.toFloat()
    showAnnotations = self._preset.properties()["showAnnotations"]

    # Create the root node, this specifies the global frame range and frame rate
    rootNode = nuke.RootNode(start, end, fps, showAnnotations)
    rootNode.addProjectSettings(self._projectSettings)
    #rootNode.setKnob("project_directory", os.path.split(self.resolvedExportPath())[0])
    script.addNode(rootNode)

    if isinstance(self._item, hiero.core.TrackItem):
      rootNode.addInputTextKnob("shot_guid", value=hiero.core.FnNukeHelpers._guidFromCopyTag(self._item),
                                tooltip="This is used to identify the master track item within the script",
                                visible=False)
      inHandle, outHandle = self.outputHandles(self._retime != True)
      rootNode.addInputTextKnob("in_handle", value=int(inHandle), visible=False)
      rootNode.addInputTextKnob("out_handle", value=int(outHandle), visible=False)

    # Set the format knob of the root node
    rootNode.setKnob("format", self.rootFormat())

    # BUG 40367 - proxy_type should be set to 'scale' by default to reflect
    # the custom default set in Nuke. Sadly this value can't be queried,
    # as it's set by nuke.knobDefault, hence the hard coding.
    rootNode.setKnob("proxy_type","scale")

    # Kun
    # Add Unconnected additional nodes
    if self._preset.properties()["additionalNodesEnabled"]:
      script.addNode(FnNukeShotExporter.FnExternalRender.createAdditionalNodes(FnNukeShotExporter.FnExternalRender.kUnconnected, self._preset.properties()["additionalNodesData"], self._item))

    writeNodes = self._createWriteNodes(firstFrame, start, end, framerate, rootNode)

    # MPLEC TODO should enforce in UI that you can't pick things that won't work.
    if not writeNodes:
      # Blank preset is valid, if preset has been set and doesn't exist, report as error
      self.setWarning(str("NukeShotExporter: No write node destination selected"))

    if self.writingSequence():
      self.writeSequence(script)

    # Write out the single track item
    else:
      self.writeTrackItem(script, firstFrame)

#     script.pushLayoutContext("clip", self._item.name())
#     colorspace1 = """
# Colorspace {
#  colorspace_out SLog3
#  name Colorspace1
#  selected true
# }
# """
#  # xpos 80
#  # ypos 512
#     tmpX = nuke.UserDefinedNode(colorspace1)
#     script.addNode(tmpX)
#     script.popLayoutContext()

    script.pushLayoutContext("write", "%s_Render" % self._item.name())

#     colorspace2 = """Colorspace {
#  colorspace_in SLog3
#  name Colorspace2
#  selected true
# }
# """
#     script.addNode(nuke.UserDefinedNode(colorspace2))

    metadataNode = nuke.MetadataNode(metadatavalues=[("hiero/project", self._projectName), ("hiero/project_guid", self._project.guid())] )
    
    # Add sequence Tags to metadata
    metadataNode.addMetadataFromTags( self._sequence.tags() )
    
    # Apply timeline offset to nuke output
    if isinstance(self._item, hiero.core.TrackItem):
      if self._cutHandles is None:
        # Whole clip, so timecode start frame is first frame of clip
        timeCodeNodeStartFrame = unclampedStart
      else:
        startHandle, endHandle = self.outputHandles()
        timeCodeNodeStartFrame = trackItemTimeCodeNodeStartFrame(unclampedStart, self._item, startHandle, endHandle)
      timecodeStart = self._clip.timecodeStart()
    else:
      # Exporting whole sequence/clip
      timeCodeNodeStartFrame = unclampedStart
      timecodeStart = self._item.timecodeStart()

    script.addNode(nuke.AddTimeCodeNode(timecodeStart=timecodeStart, fps=framerate, dropFrames=dropFrames, frame=timeCodeNodeStartFrame))
    # The AddTimeCode field will insert an integer framerate into the metadata, if the framerate is floating point, we need to correct this
    metadataNode.addMetadata([("input/frame_rate",framerate.toFloat())])

    script.addNode(metadataNode)

    # Generate Write nodes for nuke renders.

    for node in writeNodes:
      script.addNode(node)

    # Create pre-comp nodes for external annotation scripts
    # annotationsNodes = self._createAnnotationsPreComps()
    # if annotationsNodes:
    #   script.addNode(annotationsNodes)

    script.popLayoutContext()

    # KUN

    script.pushLayoutContext("track", "%s_LUTView" % self._item.name())

    vectorField = """Vectorfield {
 vfield_file "O:/LUTs/Sony/Sony Lut_2.cube"
 version 3
 file_type cube
 colorspaceIn sRGB
 colorspaceOut sRGB
 name Vectorfield1
 selected true
}
"""
 # xpos 394
 # ypos 660
    tmpVectorField = nuke.UserDefinedNode(vectorField)
    script.addNode(tmpVectorField)
    # print(tmpVectorField.inputNodes())
    # tmpVectorField.setInputNode(0, tmpX)
    # print(tmpVectorField.inputNodes())

    # add a viewer
    viewerNode = createViewerNode(self._projectSettings)
    viewerNode.setInputNode(0, tmpVectorField)
    script.addNode( viewerNode )

    script.popLayoutContext()




    scriptFilename = self.resolvedExportPath()
    hiero.core.log.debug( "Writing Script to: %s", scriptFilename )

    # Call callback before writing script to disk (see _beforeNukeScriptWrite definition below)
    self._beforeNukeScriptWrite(script)

    # script.popLayoutContext()

    # Layout the script
    FnScriptLayout.scriptLayout(script)

    script.writeToDisk(scriptFilename)
    #if postProcessScript has been set to false, don't post process
    #it will be done on a background thread by create comp
    #needs to be done as part of export task so that information
    #is added in hiero workflow
    if self._preset.properties().get("postProcessScript", True):
      error = postProcessor.postProcessScript(scriptFilename)
      if error:
        hiero.core.log.error( "Script Post Processor: An error has occurred while preparing script:\n%s", scriptFilename )
    # Nothing left to do, return False.
    return False

  def _beforeNukeScriptWrite(self, script):
    # adfs
    seqPathSplit = self.resolvedExportPath().split("/")[:6]
    seqPathSplit.append("_AuxDraft")
    auxDraftPath = "\\".join(seqPathSplit)
    if not os.path.exists(auxDraftPath):
      os.mkdir(auxDraftPath)

    slatePath = "\\".join(["M:", "JOBS", seqPathSplit[2], "_Edit", "RAW", "SLATE", "*.jpg"])
    slateList = glob.glob(slatePath)

    shutil.copy2(slateList[0], auxDraftPath)

    lutSearchPath = "\\".join(["M:", "JOBS", seqPathSplit[2], "_Edit", "RAW", "COLOR_PIPE", "SHOW_LUT", "*.cube"])
    lutList = glob.glob(lutSearchPath)

    shutil.copy2(lutList[0], auxDraftPath)

class NukeShotExtraPreset(FnNukeShotExporter.NukeShotPreset):
  """ Preset for 'Process as Shots' script export. """
  def __init__(self, name, properties, task=NukeShotExtraExporter):
    super(NukeShotExtraPreset, self).__init__(name, properties, task)

    
# Register this CustomTask and its associated Preset
hiero.core.taskRegistry.registerTask(NukeShotExtraPreset, NukeShotExtraExporter)


