#!/usr/bin/env python
"""
About Dialog for GeoSuite Desktop

Displays application version, QGIS version, Python version, and committed model files.
Provides license information and integration with the extensions system.
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QFrame, QFrame
from PyQt6.QtCore = None  # QUrl
from PyQt6.QtGui = None  # QPixmap

import os
import sys

try:
    import qgis
    QGIS_VERSION = qgis.Qgis.version
except Exception:
    QGIS_VERSION = "Unknown"

PYTHON_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

# Model files committed in this session
COMMITTED_MODELS = {
    'boundary_segmenter_backbone': '4.6MB',
    'boundary_segmenter_decoder': '2.2MB',
    'beacon_detector_backbone': '103KB',
    'beacon_detector_head': '1KB',
    'feature_extractor_backbone': '4.6MB',
    'feature_extractor_decoder': '2.9MB',
}

LICENSE_TEXT = """\
GeoSuite Desktop v2.0.0
Copyright &copy; 2026 GeoSuite Contributors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or (at your option)
any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

INFO_TEXT = f"""\

GeoSuite Desktop v2.0.0
=====================

Application: GeoSuite Desktop
Version: 2.0.0
Python Version: {PYTHON_VERSION}
QGIS Version: {QGIS_VERSION}

Committed Model Files:
-----------------------
• boundary_segmenter_backbone.npz (4.6MB)
• boundary_segmenter_decoder.npz (2.2MB)
• beacon_detector_backbone.npz (103KB)
• beacon_detector_head.npz (1KB)
• feature_extractor_backbone.npz (4.6MB)
• feature_extractor_decoder.npz (2.9MB)

Total Committed Models: 6 files

Features Enabled:
• CRS Picker with EPSG codes
• Layer management (Raster/Vector/CSV/GeoPackage)
• Attribute table viewing and editing
• Map navigation (zoom, pan, extent)
• Styling and symbology controls
• Spatial analysis tools
• Extensions system
• Masking and measurement tools

License: GNU General Public License v3.0 or later

For more information, visit: https://github.com/GeoSuite/GeoSuite
"""

MODEL_FILES = [
    'boundary_segmenter_backbone.npz',
    'boundary_segmenter_decoder.npz',
    'beacon_detector_backbone.npz',
    'beacon_detector_head.npz',
    'feature_extractor_backbone.npz',
    'feature_extractor_decoder.npz',
]


class AboutDialog(QDialog):
    """Dialog showing application information."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About GeoSuite")
        self.resize(500, 400)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Application name and version
        name_label = QLabel("<b>GeoSuite Desktop</b>")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("font-size: 24px; margin: 10px;")
        layout.addWidget(name_label)
        
        version_label = QLabel("Version 2.0.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setMargin(5)
        layout.addWidget(version_label)
        
        # Separator
        sep = QFrame()
        sep.setFrameStyle(QFrame.Shape.HLine | QFrame.Shadow.Sunken)
        sep.setMaximumHeight(2)
        layout.addWidget(sep)
        
        # QGIS and Python version info
        info_label = QLabel(f"Python Version: {PYTHON_VERSION}<br/>QGIS Version: {QGIS_VERSION}")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setMargin(5)
        layout.addWidget(info_label)
        
        # Model files section
        model_label = QLabel("Committed Model Files:")
        model_label.setStyleSheet("font-weight: bold; margin: 5px 0 5px 0;")
        layout.addWidget(model_label)
        
        model_scroll = QLabel("<br>".join(COMMITTED_MODELS.keys()))
        model_scroll.setTextInteractionFlags(1)  # TextSelectable
        layout.addWidget(model_scroll)
        
        # License info
        license_label = QLabel(LICENSE_TEXT)
        license_label.setTextInteractionFlags(1)  # TextSelectable
        license_label.setMargin(5)
        layout.addWidget(license_label)
        
        # Separator
        sep2 = QFrame()
        sep2.setFrameStyle(QFrame.Shape.HLine | QFrame.Shadow.Sunken)
        sep2.setMaximumHeight(2)
        layout.addWidget(sep2)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)


def show_about_dialog(parent=None):
    """Show the about dialog."""
    dlg = AboutDialog(parent)
    dlg.exec()


# Backward compatibility
__version__ = "2.0.0"
__version_info__ = tuple(int(v) for v in __version__.split("."))