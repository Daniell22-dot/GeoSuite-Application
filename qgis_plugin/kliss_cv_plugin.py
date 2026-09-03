"""
KLISS CV Plugin for QGIS
Provides computer vision tools for geospatial analysis directly in QGIS.
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.core import QgsApplication
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


class KLISSCVPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = self.tr(u'&KLISS CV Tools')
        self.toolbar = self.iface.addToolBar(u'KLISSCV')
        self.toolbar.setObjectName(u'KLISSCV')

    def tr(self, message):
        return QCoreApplication.translate('KLISSCVPlugin', message)

    def add_action(self, icon_path, text, callback, enabled_flag=True,
                   add_to_menu=True, add_to_toolbar=True, status_tip=None,
                   whats_this=None, parent=None):
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)
        if status_tip is not None:
            action.setStatusTip(status_tip)
        if whats_this is not None:
            action.setWhatsThis(whats_this)
        if add_to_toolbar:
            self.toolbar.addAction(action)
        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)
        self.actions.append(action)
        return action

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        self.add_action(
            icon_path,
            text=self.tr(u'Digitize Survey Plan'),
            callback=self.digitize_plan,
            parent=self.iface.mainWindow(),
            status_tip=self.tr(u'Auto-extract beacons, boundaries and labels from a scanned survey plan'),
        )
        self.add_action(
            icon_path,
            text=self.tr(u'Extract Features from Drone Image'),
            callback=self.extract_features,
            parent=self.iface.mainWindow(),
            status_tip=self.tr(u'Classify buildings, roads, vegetation from orthomosaic'),
        )
        self.add_action(
            icon_path,
            text=self.tr(u'Detect Changes Between Dates'),
            callback=self.detect_changes,
            parent=self.iface.mainWindow(),
            status_tip=self.tr(u'Compare two raster layers for change detection'),
        )
        self.add_action(
            icon_path,
            text=self.tr(u'Match GPS Track to Roads'),
            callback=self.match_gps,
            parent=self.iface.mainWindow(),
            status_tip=self.tr(u'Snap noisy GPS points to nearest road'),
        )
        self.add_action(
            icon_path,
            text=self.tr(u'Recognize Map Symbols'),
            callback=self.recognize_symbols,
            parent=self.iface.mainWindow(),
            status_tip=self.tr(u'Detect benchmarks, beacons, arrows, scale bars'),
        )
        self.add_action(
            icon_path,
            text=self.tr(u'Extract Depth Soundings'),
            callback=self.extract_soundings,
            parent=self.iface.mainWindow(),
            status_tip=self.tr(u'Extract depth values from nautical chart raster'),
        )
        self.add_action(
            icon_path,
            text=self.tr(u'Classify Land Use'),
            callback=self.classify_land_use,
            parent=self.iface.mainWindow(),
            status_tip=self.tr(u'Classify satellite imagery into land use categories'),
        )
        self.add_action(
            icon_path,
            text=self.tr(u'Extract Text from Map'),
            callback=self.extract_text,
            parent=self.iface.mainWindow(),
            status_tip=self.tr(u'OCR text labels, annotations, bearings from map images'),
        )
        self.add_action(
            icon_path,
            text=self.tr(u'Coordinate Transform'),
            callback=self.transform_coords,
            parent=self.iface.mainWindow(),
            status_tip=self.tr(u'Cassini-Soldner ↔ UTM transformation'),
        )

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(self.tr(u'&KLISS CV Tools'), action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

    def _get_pipeline(self):
        try:
            from cv_engine.pipeline import CVPipeline
            return CVPipeline()
        except ImportError as e:
            QMessageBox.critical(self.iface.mainWindow(), 'KLISS CV Error',
                                 f'Could not import CV engine: {e}\n\n'
                                 f'Make sure the backend/app/cv_engine directory is accessible.')
            return None

    def _get_raster_layer(self, prompt='Select a raster layer'):
        from qgis.core import QgsMapLayer, QgsProject
        layers = [layer for layer in QgsProject.instance().mapLayers().values()
                  if layer.type() == QgsMapLayer.RasterLayer]
        if not layers:
            QMessageBox.warning(self.iface.mainWindow(), 'KLISS CV', 'No raster layers found in the project.')
            return None
        layer_names = [layer.name() for layer in layers]
        from qgis.PyQt.QtWidgets import QInputDialog
        name, ok = QInputDialog.getItem(self.iface.mainWindow(), 'KLISS CV', prompt, layer_names, 0, False)
        if not ok:
            return None
        return layers[layer_names.index(name)]

    def _get_vector_layer(self, prompt='Select a vector layer'):
        from qgis.core import QgsMapLayer, QgsProject
        layers = [layer for layer in QgsProject.instance().mapLayers().values()
                  if layer.type() == QgsMapLayer.VectorLayer]
        if not layers:
            QMessageBox.warning(self.iface.mainWindow(), 'KLISS CV', 'No vector layers found in the project.')
            return None
        layer_names = [layer.name() for layer in layers]
        from qgis.PyQt.QtWidgets import QInputDialog
        name, ok = QInputDialog.getItem(self.iface.mainWindow(), 'KLISS CV', prompt, layer_names, 0, False)
        if not ok:
            return None
        return layers[layer_names.index(name)]

    def _load_numpy_image(self, layer):
        import numpy as np
        from osgeo import gdal
        ds = gdal.Open(layer.source())
        if ds is None:
            return None
        bands = ds.RasterCount
        if bands >= 3:
            img = np.dstack([ds.GetRasterBand(i).ReadAsArray().astype(np.float64) for i in range(1, 4)])
        else:
            img = ds.GetRasterBand(1).ReadAsArray().astype(np.float64)
        ds = None
        return img

    def _add_result_layer(self, name, layer_type, data):
        from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY, QgsField, QgsFields
        from qgis.PyQt.QtCore import QVariant
        if layer_type == 'point':
            vl = QgsVectorLayer('Point?crs=EPSG:4326', name, 'memory')
            pr = vl.dataProvider()
            pr.addAttributes([QgsField('id', QVariant.String), QgsField('type', QVariant.String),
                              QgsField('confidence', QVariant.Double)])
            vl.updateFields()
            for i, beacon in enumerate(data):
                feat = QgsFeature()
                feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(beacon['center'][0], beacon['center'][1])))
                feat.setAttributes([beacon.get('id', f'B{i+1}'), beacon.get('type', 'unknown'),
                                    beacon.get('confidence', 0)])
                pr.addFeatures([feat])
            vl.updateExtents()
            QgsProject.instance().addMapLayer(vl)
        elif layer_type == 'line':
            vl = QgsVectorLayer('LineString?crs=EPSG:4326', name, 'memory')
            pr = vl.dataProvider()
            pr.addAttributes([QgsField('from', QVariant.String), QgsField('to', QVariant.String),
                              QgsField('distance', QVariant.Double)])
            vl.updateFields()
            for seg in data:
                feat = QgsFeature()
                feat.setGeometry(QgsGeometry.fromPolylineXY([
                    QgsPointXY(seg['from'][0], seg['from'][1]),
                    QgsPointXY(seg['to'][0], seg['to'][1]),
                ]))
                feat.setAttributes([seg.get('from', ''), seg.get('to', ''), seg.get('distance', 0)])
                pr.addFeatures([feat])
            vl.updateExtents()
            QgsProject.instance().addMapLayer(vl)

    def digitize_plan(self):
        pipeline = self._get_pipeline()
        if not pipeline:
            return
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self.iface.mainWindow(), 'Select Survey Plan',
            '', 'Images (*.jpg *.jpeg *.tif *.tiff *.png);;All Files (*)')
        if not file_path:
            return
        import numpy as np
        from osgeo import gdal
        ds = gdal.Open(file_path)
        if ds is None:
            QMessageBox.critical(self.iface.mainWindow(), 'Error', 'Could not open image file.')
            return
        bands = ds.RasterCount
        if bands >= 3:
            img = np.dstack([ds.GetRasterBand(i).ReadAsArray().astype(np.float64) for i in range(1, 4)])
        else:
            img = ds.GetRasterBand(1).ReadAsArray().astype(np.float64)
        ds = None
        result = pipeline.digitize_survey_plan(img)
        self._add_result_layer('Beacons', 'point', result['beacons'])
        self.iface.messageBar().pushInfo('KLISS CV',
            f"Digitization complete: {result['total_beacons']} beacons, "
            f"{result['total_boundaries']} boundaries, {result['total_labels']} labels "
            f"({result['processing_time_ms']}ms)")

    def extract_features(self):
        pipeline = self._get_pipeline()
        if not pipeline:
            return
        layer = self._get_raster_layer('Select drone orthomosaic')
        if not layer:
            return
        img = self._load_numpy_image(layer)
        if img is None:
            QMessageBox.critical(self.iface.mainWindow(), 'Error', 'Could not load raster image.')
            return
        result = pipeline.extract_features(img)
        areas = result['class_areas_percent']
        msg = '\n'.join(f"  {k}: {v:.1f}%" for k, v in areas.items() if v > 0.1)
        QMessageBox.information(self.iface.mainWindow(), 'KLISS CV - Feature Extraction',
                                f"Dominant class: {result.get('class_names', [''])[result.get('segmentation_map', [[0]]).max()]}\n\n"
                                f"Area coverage:\n{msg}")

    def detect_changes(self):
        pipeline = self._get_pipeline()
        if not pipeline:
            return
        layer1 = self._get_raster_layer('Select BEFORE image')
        if not layer1:
            return
        layer2 = self._get_raster_layer('Select AFTER image')
        if not layer2:
            return
        img1 = self._load_numpy_image(layer1)
        img2 = self._load_numpy_image(layer2)
        if img1 is None or img2 is None:
            QMessageBox.critical(self.iface.mainWindow(), 'Error', 'Could not load images.')
            return
        result = pipeline.detect_changes(img1, img2)
        stats = result['statistics']
        msg = '\n'.join(f"  {k}: {v['percent']:.1f}%" for k, v in stats.items() if v['pixels'] > 0)
        QMessageBox.information(self.iface.mainWindow(), 'KLISS CV - Change Detection',
                                f"Change statistics:\n{msg}")

    def match_gps(self):
        pipeline = self._get_pipeline()
        if not pipeline:
            return
        layer = self._get_vector_layer('Select GPS track layer')
        if not layer:
            return
        import numpy as np
        points = []
        for feat in layer.getFeatures():
            geom = feat.geometry()
            if geom.isMultipart():
                for part in geom.asMultiPolyline():
                    points.extend([(p.x(), p.y()) for p in part])
            else:
                points.extend([(p.x(), p.y()) for p in geom.asPolyline()])
        if not points:
            QMessageBox.warning(self.iface.mainWindow(), 'KLISS CV', 'No points found in layer.')
            return
        gps_array = np.array(points)
        result = pipeline.match_gps_track(gps_array)
        self._add_result_layer('Matched Track', 'line', [
            {'from': result['matched_points'][i], 'to': result['matched_points'][i+1], 'distance': 0}
            for i in range(len(result['matched_points']) - 1)
        ])
        self.iface.messageBar().pushInfo('KLISS CV',
            f"GPS matching complete: {result['num_points']} points, "
            f"avg snap: {result['avg_snap_distance']:.3f}")

    def recognize_symbols(self):
        pipeline = self._get_pipeline()
        if not pipeline:
            return
        layer = self._get_raster_layer('Select map raster')
        if not layer:
            return
        img = self._load_numpy_image(layer)
        if img is None:
            return
        result = pipeline.recognize_symbols(img)
        self._add_result_layer('Symbols', 'point', [
            {'center': d['center'], 'type': d['symbol_type'], 'confidence': d['confidence']}
            for d in result
        ])
        self.iface.messageBar().pushInfo('KLISS CV', f"Found {len(result)} symbols")

    def extract_soundings(self):
        pipeline = self._get_pipeline()
        if not pipeline:
            return
        layer = self._get_raster_layer('Select nautical chart')
        if not layer:
            return
        img = self._load_numpy_image(layer)
        if img is None:
            return
        result = pipeline.extract_depth_soundings(img)
        self._add_result_layer('Soundings', 'point', [
            {'center': s['position'], 'type': f"depth_{s['depth']}", 'confidence': 0.8}
            for s in result['soundings']
        ])
        self.iface.messageBar().pushInfo('KLISS CV', f"Extracted {result['total_soundings']} soundings")

    def classify_land_use(self):
        pipeline = self._get_pipeline()
        if not pipeline:
            return
        layer = self._get_raster_layer('Select satellite image')
        if not layer:
            return
        img = self._load_numpy_image(layer)
        if img is None:
            return
        result = pipeline.classify_land_use(img)
        probs = result['class_probabilities']
        msg = '\n'.join(f"  {k}: {v*100:.1f}%" for k, v in probs.items() if v > 0.01)
        QMessageBox.information(self.iface.mainWindow(), 'KLISS CV - Land Use',
                                f"Dominant: {result['dominant_class']}\n\n{msg}")

    def extract_text(self):
        pipeline = self._get_pipeline()
        if not pipeline:
            return
        layer = self._get_raster_layer('Select map image')
        if not layer:
            return
        img = self._load_numpy_image(layer)
        if img is None:
            return
        result = pipeline.extract_text(img)
        texts = [f"{r['text']} ({r['bbox'][0]},{r['bbox'][1]})" for r in result]
        QMessageBox.information(self.iface.mainWindow(), 'KLISS CV - Text Extraction',
                                f"Found {len(result)} text regions:\n\n" + '\n'.join(texts[:20]))

    def transform_coords(self):
        from qgis.PyQt.QtWidgets import QInputDialog
        direction, ok = QInputDialog.getItem(
            self.iface.mainWindow(), 'KLISS CV Transform', 'Direction:',
            ['Cassini → UTM', 'UTM → Cassini'], 0, False)
        if not ok:
            return
        zone, ok = QInputDialog.getItem(
            self.iface.mainWindow(), 'KLISS CV Transform', 'Zone:',
            ['Zone I — Malindi', 'Zone II — Nairobi', 'Zone III — Nakuru', 'Zone IV — Kisumu'], 1, False)
        if not ok:
            return
        easting, ok = QInputDialog.getDouble(self.iface.mainWindow(), 'KLISS CV', 'Easting:', 285000, -1e10, 1e10, 3)
        if not ok:
            return
        northing, ok = QInputDialog.getDouble(self.iface.mainWindow(), 'KLISS CV', 'Northing:', 9892000, -1e10, 1e10, 3)
        if not ok:
            return
        offset_map = {'Zone I — Malindi': 37, 'Zone II — Nairobi': 38, 'Zone III — Nakuru': 36, 'Zone IV — Kisumu': 35}
        offset = offset_map.get(zone, 38)
        if 'Cassini → UTM' in direction:
            utm_e = easting * 1.0004 + (offset - 37) * 100000
            utm_n = northing * 1.0003 + 1200
            QMessageBox.information(self.iface.mainWindow(), 'KLISS CV Transform',
                                    f"UTM Zone 37S:\nE: {utm_e:.3f}\nN: {utm_n:.3f}")
        else:
            cas_e = (easting - (offset - 37) * 100000) / 1.0004
            cas_n = (northing - 1200) / 1.0003
            QMessageBox.information(self.iface.mainWindow(), 'KLISS CV Transform',
                                    f"Cassini-Soldner:\nE: {cas_e:.3f}\nN: {cas_n:.3f}")
