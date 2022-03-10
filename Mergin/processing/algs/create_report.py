# -*- coding: utf-8 -*-

from qgis.PyQt.QtGui import QIcon
from qgis.core import (
    QgsVectorFileWriter,
    QgsProcessing,
    QgsProcessingException,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingParameterFile,
    QgsProcessingParameterNumber,
    QgsProcessingParameterFileDestination
)

from ...utils import (
    icon_path,
    create_mergin_client,
    create_report
)


class CreateReport(QgsProcessingAlgorithm):

    PROJECT_DIR = 'PROJECT_DIR'
    START_VERSION = 'START_VERSION'
    END_VERSION = 'END_VERSION'
    REPORT = 'REPORT'

    def name(self):
        return 'createreport'

    def displayName(self):
        return 'Create report'

    def group(self):
        return 'Tools'

    def groupId(self):
        return 'tools'

    def tags(self):
        return 'mergin,project,report,statistics'.split(',')

    def shortHelpString(self):
        return 'Exports changesets aggregates for Mergin projects in given version range to a CSV file.'

    def icon(self):
        return QIcon(icon_path('icon.png', False))

    def __init__(self):
        super().__init__()

    def createInstance(self):
        return type(self)()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFile(self.PROJECT_DIR, 'Project directory', QgsProcessingParameterFile.Folder))
        self.addParameter(QgsProcessingParameterNumber(self.START_VERSION, 'Start version', QgsProcessingParameterNumber.Integer, 1, False, 1))
        self.addParameter(QgsProcessingParameterNumber(self.END_VERSION, 'End version', QgsProcessingParameterNumber.Integer, 1, False, 1))
        self.addParameter(QgsProcessingParameterFileDestination(self.REPORT, 'Report', 'CSV files (*.csv *.CSV)'))

    def processAlgorithm(self, parameters, context, feedback):
        project_dir = self.parameterAsString(parameters, self.PROJECT_DIR, context)
        start = self.parameterAsInt(parameters, self.START_VERSION, context)
        end = self.parameterAsInt(parameters, self.END_VERSION, context)
        output_file = self.parameterAsFileOutput(parameters, self.REPORT, context)

        mc = create_mergin_client()
        warnings = create_report(mc, project_dir, f"v{start}", f"v{end}", output_file)
        if warnings:
            for w in warnings:
                feedback.pushWarning(w)

        context.addLayerToLoadOnCompletion(output_file, QgsProcessingContext.LayerDetails('Report', context.project()))

        return {self.REPORT: output_file}
