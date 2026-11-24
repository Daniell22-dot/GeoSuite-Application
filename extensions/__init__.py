#!/usr/bin/env python
"""
Extensions Registry for GeoSuite Desktop

Manages plugin loading from the extensions/ directory.
Plugins are Python scripts with @pyqtSlot decorated functions
that extend the application's functionality.

Plugin format:
- Python script with @pyqtSlot decorated functions
- Metadata in header: name, description, version, author
- Loaded into the Extensions menubar
- Plugins can add menu entries, tools, or modify UI
"""

import importlib
import os
import sys
from pathlib import Path

from PyQt6.QtCore import QSettings, pyqtSlot
from PyQt6.QtWidgets = None  # QMenu, QAction

# Extensions directory
EXTENSIONS_DIR = Path(__file__).parent / "extensions" if "__file__" in dir() else Path("extensions")

# Plugin metadata template
PLUGIN_METADATA_TEMPLATE = """
# Plugin Metadata
# name: Plugin Name
# description: Short description
# version: 1.0.0
# author: Author Name

# PyQt6 pyqtSlot functions will be automatically loaded
"""

# Registered plugins
_registered_plugins = {}
PLUGIN_VERSION = "2.0.0"


def discover_plugins(extensions_dir=None):
    """Discover and load all plugins from the extensions directory."""
    global _registered_plugins
    
    ext_dir = extensions_dir or EXTENSIONS_DIR
    if not ext_dir.exists():
        return
    
    for py_file in ext_dir.glob("*.py"):
        if py_file.name.startswith("__"):
            continue
        
        try:
            # Import the module
            module_name = py_file.stem
            module = importlib.import_module(f"extensions.{module_name}")
            
            # Extract metadata from module docstring or attributes
            metadata = {}
            if hasattr(module, '__doc__') and module.__doc__:
                # Parse metadata from docstring
                for line in module.__doc__.split('\n'):
                    line = line.strip()
                    if line.startswith('#'):
                        key_val = line[1:].strip()
                        if ':' in key_val:
                            key, val = key_val.split(':', 1)
                            key = key.strip().lower()
                            val = val.strip()
                            metadata[key] = val
            
            # Find pyqtSlot functions
            plugin_functions = []
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if callable(attr):
                    # Check if it's a pyqtSlot (has Slot annotation or is a Qt method)
                    # In PyQt6, we check if it has the pyqtSlot decorator pattern
                    # For now, assume any function starting with 'plugin_' or decorated
                    # is a plugin function
                    if attr_name.startswith('plugin_') or hasattr(attr, '__pyqt_slot__'):
                        plugin_functions.append(attr_name)
            
            _registered_plugins[module_name] = {
                'module': module,
                'metadata': metadata,
                'functions': plugin_functions,
                'file': str(py_file),
            }
            
        except Exception as e:
            print(f"Failed to load plugin {py_file.name}: {e}")


def load_plugins(extensions_dir=None):
    """Load all discovered plugins and register their actions."""
    discover_plugins(extensions_dir)
    return _registered_plugins


def get_plugin(name):
    """Get a registered plugin by name."""
    return _registered_plugins.get(name)


def list_plugins():
    """List all registered plugins."""
    return list(_registered_plugins.keys())


def call_plugin_function(plugin_name, function_name, *args, **kwargs):
    """Call a function from a registered plugin."""
    plugin = get_plugin(plugin_name)
    if plugin and function_name in plugin['functions']:
        module = plugin['module']
        func = getattr(module, function_name, None)
        if func:
            return func(*args, **kwargs)
    return None


# Example plugin structure (would be in extensions/ directory)
# -------------------------------------------------------
# # Plugin: Add Sample Raster
# # description: Loads sample GEBCO bathymetric data
# # version: 1.0.0
# # author: GeoSuite Team
# 
# from PyQt6.QtWidgets import QAction, QMessageBox
# 
# @pyqtSlot()
# def load_sample_raster():
#     """Load sample GEBCO bathymetric data."""
#     import os
#     import numpy as np
#     from qgis.core import QgsRasterLayer
#     
#     path = r"D:\Geospatial_suite\RAW DATA\Bathymetric_Data\GEBCO_12_Sep_2025_660ee9b1cc91"
#     layer = QgsRasterLayer(path, "GEBCO Bathymetric")
#     if layer.isValid():
#         QgsProject.instance().addMapLayer(layer)
#         QMessageBox.information(None, "Success", "Sample raster loaded")
#     else:
#         QMessageBox.warning(None, "Error", "Failed to load raster layer")


# # Plugin: Add Sample Vector
# # description: Loads sample point/line/polygon data
# # version: 1.0.0
# # author: GeoSuite Team
# 
# @pyqtSlot()
# def load_sample_vector():
#     """Load sample vector data."""
#     from qgis.core import QgsVectorLayer, QgsProject
#     layer = QgsVectorLayer("Point?crs=EPSG:4326", "Sample Points", "memory")
#     QgsProject.instance().addMapLayer(layer)
</ext\ extensions\n\n


def check_plugin_compatibility(plugin_name, layer_crs):
    """Check if a plugin is compatible with the layer's CRS.
    
    Args:
        plugin_name: Name of the plugin
        layer_crs: CRS string of the layer
        
    Returns:
        bool: True if compatible, False otherwise
    """
    plugin = get_plugin(plugin_name)
    if not plugin:
        return False
    
    metadata = plugin['metadata']
    # In a full implementation, would check plugin CRS requirements
    # against the layer CRS
    return True  # Placeholder - assume compatible


# Example usage
if __name__ == "__main__":
    # Load all plugins
    plugins = load_plugins()
    print(f"Loaded {len(plugins)} plugins:")
    for name, info in plugins.items():
        print(f"  - {name}: {metadata.get('version', '?')} by {metadata.get('author', '?')}")
        for func in info['functions']:
            print(f"    - {func}")