###################################################################################################################################
#
# This python script add an additional action command menu when right click on Clip-related object, mainly for Timeline slate.
# The action will scan for latest versions of the selected objects. Then update to the latest version.
# The problem the comp team has, is that conventionally they need to click two commands to update to latest version. First, torturously wait for scan command to complete then manually click version up command.
# 
# - Most of the code is inheritance from the original ScanForVersionsAction class. The core part is in doit(). 
# - Set shortcut on right click command doesn't work somehow on Hiero.
#
# **Update** Found out later. Existing maxversion command already did what the comp team want.. Guess they just don't know about it... So if you just teach them about maxversion command. We can scrap this plugin.
#
###################################################################################################################################

import hiero.core
from hiero.ui import ScanForVersions, findMenuAction
import Qt.QtGui
import Qt.QtWidgets

class ScanAndMaxVersionsAction(ScanForVersions.ScanForVersionsAction):
	"""QAction class inherited from working ScanForVersionsAction class. Will scan for latest version then max version on selected item"""
	def __init__(self):
		Qt.QtWidgets.QAction.__init__(self, "Scan and max version", None)
		
		# doesnt work somehow
		self.setShortcut(Qt.QtGui.QKeySequence('Alt+Shift+Up'))
		
		self.triggered.connect(self.doit)
		
		hiero.core.events.registerInterest((hiero.core.events.EventType.kShowContextMenu, hiero.core.events.EventType.kBin), self.eventHandler)
		hiero.core.events.registerInterest((hiero.core.events.EventType.kShowContextMenu, hiero.core.events.EventType.kTimeline), self.eventHandler)

	def doit(self):

		# get the currently selected versions from UI
		versions = self.selectedVersions()

		if len(versions) == 0:
			hiero.core.log.info( "No valid versions found in selection" )
			return
		
		#ScanForVersions.ScanAndMaxVersionTrackItems(versions)
		#ScanForVersions._DoScanForVersions(versions, None, True)
		# Find maxversion command then call it.
		maxVersionAction = findMenuAction('foundry.project.maxversion')
		maxVersionAction.trigger()


# Instantiate the action to get it to register itself.
action = ScanAndMaxVersionsAction()

