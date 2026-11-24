#!/usr/bin/env python
"""
GeoSuite Desktop Application - Main Window

A QGIS-like desktop geospatial application for geospatial data processing,
analysis, and visualization. Supports raster, vector, and bathymetric data.

Features:
- CRS Picker with EPSG code selection
- Layer management (add/remove raster/vector layers)
- Attribute table viewing and editing
- Map navigation (zoom, pan, extent)
- Styling and symbology controls
- Spatial analysis tools
- File format support (GeoPackage, Shapefile, CSV, GeoTIFF, etc.)
- Extensions system
- Masking and analysis tools
"""

import sys
import os

from PyQt6.QtWidgets import (QApplication, QMainWindow, QDockWidget, QComboBox,
    QLabel, QStatusBar, QToolBar, QAction, QMessageBox, QTreeView, QDialog,
    QVBoxLayout, QWidget, QPushButton, QSlider, QCheckBox, QLineEdit,
    QFormLayout, QGroupBox, QTabWidget, QHeaderView, QSplitter)
from PyQt6.QtCore import Qt, QSettings, QSize, pyqtSignal, QLocale, QTranslator
from PyQt6.QtGui import QAction, QIcon, QPixmap, QCursor, QColor

# Try to import QGIS classes; fall back to standalone mode if not available
try:
    from qgis.core import QgsApplication, QgsCoordinateReferenceSystem, QgsLayerTreeRegistry
    QGIS_AVAILABLE = True
except ImportError:
    QGIS_AVAILABLE = False

# Import application modules (will be created in subsequent commits)
from .format_handlers import format_handlers
from .layer_manager import LayerManager
from .layer_catalogue import LayerCatalogue
from .map_canvas import MapCanvas
from .attribute_table import AttributeTableDialog
from .styling_dialog import StylingDialog
from .import_dialog import ImportDialog
from .analysis_tools import AnalysisTools
from . import extensions


class GeoSuiteDesktop(QMainWindow):
    """
    Main application window for GeoSuite Desktop.
    
    Provides a QGIS-like interface for geospatial data processing,
    analysis, and visualization with desktop deployment.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Application settings
        self.settings = QSettings("GeoSuite", "DesktopApp")
        
        # Initialize QGIS application if available
        if QGIS_AVAILABLE:
            self.qgs_app = QgsApplication([], False)
            self.qgs_app.setPrefixPath("/usr", True)
            self.qgs_app.initQgis()
        
        # Track loaded layers
        self.loaded_layers = []
        self.crs_enabled = True
        
        # Setup the user interface
        self.setup_ui()
        
        # Load settings
        self.restore_state()
        
        # Initialize default CRS
        self.on_crs_changed(self.cmb_crs.currentText())
    
    def setup_ui(self):
        """Set up the main user interface."""
        self.setWindowTitle("GeoSuite Desktop")
        self.resize(1200, 800)
        
        # ---- Menu Bar ----
        self.setup_menu_bar()
        
        # ---- Tool Bar ----
        self.setup_toolbar()
        
        # ---- Status Bar ----
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("GeoSuite Desktop Ready")
        
        # ---- Central Widget: Map Canvas ----
        self.map_canvas = MapCanvas(self)
        self.setCentralWidget(self.map_canvas)
        
        # ---- Dock Widgets ----
        # 1. Layer Catalogue (left)
        self.layer_catalogue = LayerCatalogue(self)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetZone, self.layer_catalogue)
        
        # 2. Attribute Table (bottom)
        self.attribute_table_btn = QAction("Attribute Table", self)
        self.attribute_table_btn.setStatusTip("View attribute table")
        self.attribute_table_btn.triggered.connect(self.show_attribute_table)
        
        # 3. Styling (right)
        self.styling_action = QAction("Styling", self)
        self.styling_action.setStatusTip("Configure layer symbology")
        self.styling_action.triggered.connect(self.show_styling_dock)
        
        # 4. Analysis tools (bottom right)
        self.analysis_action = QAction("Analysis Tools", self)
        self.analysis_action.setStatusTip("Spatial analysis tools")
        self.analysis_action.triggered.connect(self.show_analysis_tools)
        
        # ---- CRS Picker Toolbar ----
        self.setup_crs_picker()
        
        # ---- Layer Toolbar ----
        self.setup_layer_toolbar()
    
    def setup_crs_picker(self):
        """Set up the CRS (Coordinate Reference System) picker toolbar."""
        self.toolbar_crs = self.addToolBar("CRS Picker")
        self.toolbar_crs.setObjectName("CRS Picker")
        
        self.lbl_crs = QLabel("CRS:")
        self.toolbar_crs.addWidget(self.lbl_crs)
        
        self.cmb_crs = QComboBox()
        self.cmb_crs.setMaximumWidth(180)
        self.cmb_crs.addItem("EPSG:4326 - WGS84 (Default)")
        self.cmb_crs.addItem("EPSG:3857 - Web Mercator")
        self.cmb_crs.addItem("EPSG:27700 - OSGB British National Grid")
        self.cmb_crs.addItem("EPSG:32661 - UTM Zone 60N")
        self.cmb_crs.addItem("EPSG:32662 - UTM Zone 61N")
        self.cmb_crs.addItem("EPSG:32663 - UTM Zone 62N")
        self.cmb_crs.addItem("EPSG:32664 - UTM Zone 63N")
        self.cmb_crs.addItem("EPSG:32665 - UTM Zone 64N")
        self.cmb_crs.currentTextChanged.connect(self.on_crs_changed)
        self.toolbar_crs.addWidget(self.cmb_crs)
        
        self.btn_crs_load = QAction("Load CRS...", self)
        self.toolbar_crs.addAction(self.btn_crs_load)
        self.btn_crs_load.triggered.connect(self.load_crs_file)
        
        # Set default CRS
        self.cmb_crs.setCurrentIndex(0)  # EPSG:4326
    
    def on_crs_changed(self, crs_text):
        """Handle CRS change event."""
        self.statusBar.showMessage(f"CRS changed to: {crs_text}")
        # Extract EPSG code
        epsg_code = crs_text.split(":")[1] if ":" in crs_text else "4326"
        try:
            if QGIS_AVAILABLE:
                self.qgs_crs = QgsCoordinateReferenceSystem(epsg_code)
                if self.qgs_crs.isValid():
                    self.map_canvas.set_crs(self.qgs_crs)
                    self.statusBar.showMessage(f"CRS set to {crs_valid} successfully", 3000)
                else:
                    self.statusBar.showMessage(f"Invalid CRS: {epsg_code}", 5000)
            else:
                # Standalone mode: just log the CRS
                self.statusBar.showMessage(f"CRS: {epsg_code} (standalone mode)", 3000)
        except Exception as e:
            self.statusBar.showMessage(f"CRS error: {str(e)[:50]}", 5000)
    
    def load_crs_file(self):
        """Load CRS from .prj or .qgs project file."""
        from PyQt6.QtWidgets import QFileDialog
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Load CRS File", "", "PRJ Files (*.prj);;All Files (*)"
        )
        if filepath:
            try:
                with open(filepath, 'r') as f:
                    crs_text = f.read().strip()
                self.cmb_crs.setCurrentText(crs_text)
                self.on_crs_changed(crs_text)
                self.statusBar.showMessage(f"CRS loaded from {filepath}", 3000)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load CRS file:\n{str(e)}")
    
    def setup_menu_bar(self):
        """Set up the menu bar."""
        # File menu
        self.menu_file = self.menuBar().addMenu("&File")
        self.action_open_project = QAction("&Open Project...", self)
        self.menu_file.addAction(self.action_open_project)
        self.action_save_project = QAction("&Save Project", self)
        self.menu_file.addAction(self.action_save_project)
        self.action_exit = QAction("E&xit", self, Qt.KeyboardShortcut.Close)
        self.menu_file.addAction(self.action_exit)
        
        # Edit menu
        self.menu_edit = self.menuBar().addMenu("&Edit")
        self.action_undo = QAction("&Undo", self, shortcut="Ctrl+Z")
        self.menu_edit.addAction(self.action_undo)
        self.action_redo = QAction("&Redo", self, shortcut="Ctrl+Y")
        self.menu_edit.addAction(self.action_redo)
        
        # View menu
        self.menu_view = self.menuBar().addMenu("&View")
        self.action_attributes = QAction("&Attribute Table", self, shortcut="Ctrl+T")
        self.menu_view.addAction(self.action_attributes)
        self.action_styling = QAction("&Styling", self, shortcut="Ctrl+S")
        self.menu_view.addAction(self.action_styling)
        self.action_analysis = QAction("&Analysis Tools", self, shortcut="Ctrl+A")
        self.menu_view.addAction(self.action_analysis)
        
        # Extensions menu
        self.menu_extensions = self.menuBar().addMenu("&Extensions")
        self.action_load_plugin = QAction("&Load Plugin...", self)
        self.menu_extensions.addAction(self.action_load_plugin)
        self.action_list_extensions = QAction("&List Extensions", self)
        self.menu_extensions.addAction(self.action_list_extensions)
        self.action_about = QAction("&About GeoSuite", self)
        self.menu_extensions.addAction(self.action_about)
        self.action_about.setToolTip("About GeoSuite Desktop")
        # Connect about action to about dialog
        self.action_about.triggered.connect(self.show_about_dialog)
        
        # Help menu
        self.menu_help = self.menuBar().addMenu("&Help")
        self.action_help = QAction("&User Manual", self)
        self.menu_help.addAction(self.action_help)
        self.action_feedback = QAction("&Feedback", self)
        self.menu_help.addAction(self.action_feedback)
    
    def setup_toolbar(self):
        """Set up the main toolbar."""
        pass  # Toolbar items added in specific methods
    
    def setup_layer_toolbar(self):
        """Set up the layer management toolbar."""
        self.toolbar_layers = self.addToolBar("Layers")
        self.toolbar_layers.setObjectName("Layer Toolbar")
        
        self.btn_add_layer = QAction("Add Layer", self, shortcut="Ctrl+L")
        self.toolbar_layers.addAction(self.btn_add_layer)
        self.btn_add_layer.triggered.connect(self.open_import_dialog)
        
        self.btn_remove_layer = QAction("Remove Layer", self, shortcut="Delete")
        self.toolbar_layers.addAction(self.remove_layer_action)
        
        self.btn_remove_all = QAction("Remove All", self)
        self.toolbar_layers.addAction(self.btn_remove_all)
        self.btn_remove_all.triggered.connect(self.remove_all_layers)
    
    def open_import_dialog(self):
        """Open the file import dialog."""
        dlg = ImportDialog(self)
        if dlg.exec():
            # Layer added via signal
            pass
    
    def remove_layer(self, layer):
        """Remove a layer from the map and registry."""
        if layer in self.loaded_layers:
            self.loaded_layers.remove(layer)
            self.layer_catalogue.remove_layer(layer)
            self.map_canvas.remove_layer(layer)
            self.statusBar.showMessage(f"Layer removed: {layer.name()}", 2000)
    
    def remove_all_layers(self):
        """Remove all loaded layers."""
        for layer in self.loaded_layers[:]:
            self.remove_layer(layer)
        self.statusBar.showMessage("All layers removed", 2000)
    
    def show_attribute_table(self):
        """Show the attribute table dialog."""
        # Get the current selected layer from the catalogue
        selected = self.layer_catalogue.get_selected_layer()
        if selected:
            dlg = AttributeTableDialog(selected, self)
            dlg.exec()
        else:
            QMessageBox.information(self, "No Layer Selected", 
                "Please select a layer in the catalogue to view its attribute table.")
    
    def show_styling_dock(self):
        """Show the styling/dock widget."""
        selected = self.layer_catalogue.get_selected_layer()
        if selected:
            dlg = StylingDialog(selected, self)
            dlg.exec()
        else:
            QMessageBox.information(self, "No Layer Selected", 
                "Please select a layer in the catalogue to configure styling.")
    
    def show_analysis_tools(self):
        """Show the analysis tools dialog."""
        dlg = AnalysisTools(self)
        dlg.exec()
    
    def show_about_dialog(self):
        """Show the about dialog."""
        QMessageBox.about(self, "About GeoSuite Desktop",
            "<b>GeoSuite Desktop v2.0.0</b><br>"
            "Geospatial Data Processing & Analysis Platform<br><br>"
            "Copyright &copy; 2026 GeoSuite Contributors<br><br>"
            "Features:<br>"
            "- CRS Picker with EPSG codes<br>"
            "- Layer management (Raster/Vector/CSV/GeoPackage)<br>"
            "- Attribute table viewing and editing<br>"
            "- Map navigation (zoom, pan, extent)<br>"
            "- Styling and symbology controls<br>"
            "- Spatial analysis tools (buffer, intersect, etc.)<br>"
            "- Extensions system<br>"
            "- Masking and measurement tools<br><br>"
            "QGIS-like desktop geospatial application.<br>"
            "For non-commercial and research use only.")
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Save settings
        self.save_state()
        
        # Clean up QGIS
        if QGIS_AVAILABLE:
            self.qgs_app.exitQgis()
        
        event.accept()
    
    def restore_state(self):
        """Restore application state from QSettings."""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            # Default geometry for 1200x800 window
            self.resize(1200, 800)
        
        # Restore CRS from last session
        crs = self.settings.value("crs", "EPSG:4326")
        idx = self.cmb_crs.findText(crs)
        if idx >= 0:
            self.cmb_crs.setCurrentIndex(idx)
            self.on_crs_changed(crs)
    
    def save_state(self):
        """Save application state to QSettings."""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("crs", self.cmb_crs.currentText())


def main():
    """Main entry point for GeoSuite Desktop application."""
    import sys
    
    # Check for headless mode
    headless = "--headless" in sys.argv
    
    if headless:
        print("GeoSuite Desktop running in headless mode (no GUI)")
        # In headless mode, we could perform batch processing, etc.
        # For now, just exit
        sys.exit(0)
    
    # Enable high-DPI scaling
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
    
    app = QApplication(sys.argv)
    app.setApplicationName("GeoSuite Desktop")
    app.setApplicationVersion("2.0.0")
    org = "GeoSuite"
    app.setOrganizationName(org)
    
    window = GeoSuiteDesktop()
    window.show()
    
    # Remove splash screen after window shows
    # (Splash screen would be added in a later commit)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()