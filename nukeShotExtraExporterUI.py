import hiero.ui

from hiero.exporters import FnNukeShotExporter, FnNukeShotExporterUI

import nukeShotExtraExporter

class NukeShotExtraExporterUI(FnNukeShotExporterUI.NukeShotExporterUI):
	def __init__(self, preset):
		FnNukeShotExporterUI.NukeShotExporterUI.__init__(self, preset)
		self._displayName = "Netflix Project File"

hiero.ui.taskUIRegistry.registerTaskUI(nukeShotExtraExporter.NukeShotExtraPreset, NukeShotExtraExporterUI)
#hiero.ui.taskUIRegistry.registerTaskUI(FnNukeShotExporter.NukeSequencePreset, NukeShotExtraExporterUI)