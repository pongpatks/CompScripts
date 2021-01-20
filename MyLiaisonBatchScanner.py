###################################################################################################################################
#
# This python script define an action class that will scan all file in the project for latest version then max version them.
#
# It is a mash up code from version_everywhere.py-an official example and hiero.ui.ScanForVersion.py code.
#
# The reason I have to copy and change so much original code becoz I want it to have meaningful popup feedback in detail. Original one sucks at this.
#
###################################################################################################################################

import hiero.core
import hiero.ui
from hiero.ui import ScanForVersions
import foundry.ui

import Qt.QtGui
import Qt.QtWidgets


class ScanVersionsTaskDetail(object):
	"""Modified class of original ScanForVersionTask.
	change normal popup to infobox. newVersionFiles[] array has been moved from private variable to class variable for easier access.
	"""
	def __init__(self):
		self._task = foundry.ui.ProgressTask("Finding Versions...")
		self.newVersionFiles = []

	def scanForVersions(self, versions, postScanFunc, shouldDisplayResults):
		""" Scan a list of versions for new versions.  If postScanFunc is provided,
		this will be called after the scan.
		Returns True if scanning was completed, or False if the user cancelled or
		an error occurred.
		"""
		try:
			self.scanForVersionsInternal(versions, postScanFunc, shouldDisplayResults)
			return True
		except StopIteration: # This is raised if the user cancelled
			return False
		except: # For other exceptions, log them and return False
			hiero.core.log.exception("Scan for Versions failed")
			return False


	def scanForVersionsInternal(self, versions, postScanFunc, shouldDisplayResults):
		scanner = hiero.core.VersionScanner.VersionScanner()

		for version in versions:
			self.rescanClipRanges(version)
			self.processEventsAndCheckCancelled()

		# Find all the files to be added as versions
		numNewFiles = 0
		self.newVersionFiles = []

		# For each version find the additional files
		verIndex = 0
		numVer = len(versions)
		self._task.setMessage("Scanning file system for new versions...")

		for version in versions:
			newFiles = scanner.findVersionFiles(version)
			self.newVersionFiles.append ( [ version, newFiles ] )
			numNewFiles += len(newFiles)
			self.processEventsAndCheckCancelled()

			verIndex += 1
			self._task.setProgress(int(100.0*(float(verIndex)/float(numVer))))

		# Now create the clips for the additional files
		fileIndex = 0
		numNewVer = len(self.newVersionFiles)
		self._task.setMessage("Creating new Clips...")
		for versionFile in self.newVersionFiles:
			newClips = []

			version, newFiles = versionFile

			for newFile in newFiles:
				self.processEventsAndCheckCancelled()

				fileIndex += 1
				self._task.setProgress(int(100.0*(float(fileIndex)/float(numNewVer))))
				newClip = scanner.createClip(newFile)

				# Filter out any invalid clips
				if newClip is not None:
					newClips.append(newClip)

			versionFile.append ( newClips )

		# Now create the additional versions from the clips and add them to the version list
		regIndex = 0
		self._task.setMessage("Registering Clips as new versions...")
		for versionFile in self.newVersionFiles:
			version  = versionFile[0]
			newClips = versionFile[2]
			binitem = version.parent()

			# Now add the clips as new versions
			newVersions = scanner.insertClips(binitem, newClips)
			versionFile.append ( newVersions )

			hiero.core.log.info("InsertClips - Versions found for %s: %s", version, newVersions)
			self.processEventsAndCheckCancelled()

			regIndex += 1
			self._task.setProgress(int(100.0*(float(regIndex)/float(numNewVer))))


		# If we have a post scan function then run it (version up/down, min/max)
		if (postScanFunc is not None):
			oldClip = version.item()
			postScanFunc()
			newClip = binitem.activeVersion().item()

			# Then update any viewers looking at the old clip to the new clip
			hiero.ui.updateViewer(oldClip, newClip)

		# If we're supposed to display results then do so
		if (shouldDisplayResults):
			self.displayResults()


	def processEventsAndCheckCancelled(self):
		""" Call QCoreApplication.processEvents() and check if the user has cancelled
		the progress task.  If cancelled, StopIteration will be raised.
		"""
		Qt.QtCore.QCoreApplication.processEvents()
		if self._task.isCancelled():
			raise StopIteration()


	def displayResults(self):
		""" Display results """
		infoBox = Qt.QtWidgets.QMessageBox(hiero.ui.mainWindow())
		infoBox.setIcon(Qt.QtWidgets.QMessageBox.Information)

		# Now present an info dialog, explaining where shots were updated
		updatedCount = 0
		updateReportString = "The following Versions were updated:\n"
		for each in self.newVersionFiles:
			if len(each[3])!=0:
				updateReportString+="%s > %s\n" % (each[0].name(), each[3][-1].name())
				updatedCount += 1

		if len(self.newVersionFiles)<=0:
			infoBox.setText("No Shot Versions were updated")
			infoBox.setInformativeText("Clip could not be found in any Shots in this Project")
		else:
			infoBox.setText("Found %i versions. Please show Details for more info." % (updatedCount))
			infoBox.setDetailedText(updateReportString)
			
			infoBox.exec_()


	def rescanClipRanges(self, activeVersion):
		""" From an active version, iterates through all the siblings inside the BinItem """
		binItem = activeVersion.parent()
		if binItem:
			for version in binItem.items():
				clip = version.item()
				if clip:
					clip.rescan()

def ScanAndMaxVersionTrackItemWithPrompt(trackItems):
	'''Scan then move to next version on the track items'''
	versionsToScan = set()
	for item in trackItems:
		if item.isMediaPresent():
			versionsToScan.add(item.currentVersion())

	# Do the scan
	scanner = ScanVersionsTaskDetail()
	ok = scanner.scanForVersions(versionsToScan, None, True)

	scanner._task.setMessage("Switching to the max versions...")

	# If the scan was successful, do the callback on each item
	if ok:
		for item in trackItems:
			hiero.core.TrackItem.maxVersion(item)
	return ok

# Action to scan for new versions
class ScanTimelineVersionsAction(Qt.QtWidgets.QAction):

	_scanner = hiero.core.VersionScanner.VersionScanner()

	def __init__(self):
		Qt.QtWidgets.QAction.__init__(self, "Scan timeline for versions", None)
	  
		self.setShortcut(Qt.QtGui.QKeySequence('Alt+V'))
		self.triggered.connect(self.doit)


	def doit(self):
		#proj = hiero.core.projects()[0]
		#searches = hiero.core.findItemsInProject(proj, 'TrackItems')

		if isinstance(hiero.ui.activeView(), hiero.ui.TimelineEditor):
			# 
			trackItemList = []

			for track in hiero.ui.activeView().sequence().items():
				if track.name() in ["VFX", "Review", "EXPORT"]:
					for item in track.items():
						trackItemList.append(item)

			if len(trackItemList) == 0:
				hiero.core.log.info( "No valid versions found in selection" )
				return

			# Main operation
			ScanAndMaxVersionTrackItemWithPrompt(trackItemList)

		else:
			msgBox = Qt.QtWidgets.QMessageBox()
			msgBox.setText("Please make target timeline tab active.")
			msgBox.setStandardButtons(Qt.QtWidgets.QMessageBox.Ok)
			msgBox.setDefaultButton(Qt.QtWidgets.QMessageBox.Ok)
			msgBox.exec_()

		
		# Main operation
		#ScanAndMaxVersionTrackItemWithPrompt(trackItemList)


# action = ScanAllVersionsAction()

# menubar = hiero.ui.menuBar()
# tbmenu = menubar.addMenu("&MyLiaison")
# tbmenu.addAction(action)
