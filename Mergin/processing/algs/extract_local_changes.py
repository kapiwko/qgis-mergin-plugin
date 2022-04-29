# -*- coding: utf-8 -*-

import os
import sqlite3

from qgis.PyQt.QtGui import QIcon
from qgis.core import (
    QgsFeatureSink,
    QgsProcessing,
    QgsProcessingException,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingParameterFile,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterFeatureSink
)

from ...mergin.merginproject import MerginProject

from ...diff import (
    get_local_changes,
    parse_db_schema,
    parse_diff,
    get_table_name,
    create_field_list,
    diff_table_to_features
)

from ...utils import (
    icon_path,
    check_mergin_subdirs,
)


class ExtractLocalChanges(QgsProcessingAlgorithm):

    PROJECT_DIR = 'PROJECT_DIR'
    LAYER = 'LAYER'
    OUTPUT = 'OUTPUT'

    def name(self):
        return 'extractlocalchanges'

    def displayName(self):
        return 'Extract local changes'

    def group(self):
        return 'Tools'

    def groupId(self):
        return 'tools'

    def tags(self):
        return 'mergin,added,dropped,new,deleted,features,geometries,difference,delta,revised,original,version,compare'.split(',')

    def shortHelpString(self):
        return 'Extracts local changes made in the specific layer of the Mergin project to make it easier to revise changes.'

    def icon(self):
        return QIcon(icon_path('icon.png', False))

    def __init__(self):
        super().__init__()

    def createInstance(self):
        return type(self)()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFile(self.PROJECT_DIR, 'Project directory', QgsProcessingParameterFile.Folder))
        self.addParameter(QgsProcessingParameterVectorLayer(self.LAYER, 'Input layer'))
        self.addParameter(QgsProcessingParameterFeatureSink(self.OUTPUT, 'Local changes layer'))

    def processAlgorithm(self, parameters, context, feedback):
        project_dir = self.parameterAsString(parameters, self.PROJECT_DIR, context)
        layer = self.parameterAsVectorLayer(parameters, self.LAYER, context)

        if not check_mergin_subdirs(project_dir):
            raise QgsProcessingException("Selected directory does not contain a valid Mergin project.")

        if not os.path.normpath(layer.source()).lower().startswith(os.path.normpath(project_dir)):
            raise QgsProcessingException("Selected layer does not belong to the selected Mergin project.")

        if layer.dataProvider().storageType() != "GPKG":
            raise QgsProcessingException("Selected layers has unsupported format. Only GPKG layers are supported.")

        mp = MerginProject(project_dir)

        layer_path = layer.source().split("|")[0]
        diff_path = get_local_changes(layer_path, mp)
        feedback.setProgress(5)

        if diff_path is None:
            raise QgsProcessingException("Failed to retrieve changes, as there is no base file for input layer.")

        table_name = get_table_name(layer)

        db_schema = parse_db_schema(layer_path)
        feedback.setProgress(10)

        fields, fields_mapping = create_field_list(db_schema[table_name])
        (sink, dest_id) = self.parameterAsSink(parameters, self.OUTPUT, context, fields, layer.wkbType(), layer.sourceCrs())

        diff = parse_diff(diff_path)
        feedback.setProgress(15)

        if diff and table_name in diff.keys():
            db_conn = None  # no ref. db
            db_conn = sqlite3.connect(layer_path)
            features = diff_table_to_features(diff[table_name], db_schema[table_name], fields, fields_mapping, db_conn)
            feedback.setProgress(20)

            current = 20
            step = 80.0 / len(features) if features else 0
            for i, f in enumerate(features):
                if feedback.isCanceled():
                    break
                sink.addFeature(f, QgsFeatureSink.FastInsert)
                feedback.setProgress(int(i * step))

        return {self.OUTPUT: dest_id}
