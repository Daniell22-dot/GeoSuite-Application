#!/usr/bin/env python
"""
Plugin System for GeoSuite Desktop

Provides a plugin framework for extending GeoSuite Desktop functionality.
Plugins are Python scripts with @pyqtSlot decorated functions
that can add menu entries, tools, or modify UI.

Plugin format:
- Python script with @pyqtSlot decorated functions
- Metadata in header: name, description, version, author
- Loaded from extensions/ directory
- Loaded into the Extensions menubar
- Plugins can add menu entries, tools, or modify UI

Example plugin format:
# Plugin: Add Sample Raster
# description: Loads sample GEBCO bathymetric data
# version: 1.0.0
# author: GeoSuite Team

# @pyqtSlot()
# def load_sample_raster():
#     """Load sample GEBCO bathymetric data."""
#     import os
#     from qgis.core import QgsRasterLayer
#     
#     path = r"D:\Geospatial_suite\RAW DATA\Bathymetric_Data\GEBCO_12_Sep_2025_660ee9b1cc91"
#     layer = QgsRasterLayer(path, "GEBCO Bathymetric")
#     if layer.isValid():
#         QgsProject.instance().addMapLayer(layer)
#         QMessageBox.information(None, "Success", "Sample raster loaded")
#     else:
#         QMessageBox.warning(None, "Error", "Failed to load raster layer")

from PyQt6.QtCore import QSettings, pyqtSignal
from pathlib import Path

# Extensions directory
EXTENSIONS_DIR = Path("extensions")

# Registered plugins
_registered_plugins = {}

# Plugin metadata template
PLUGIN_METADATA_TEMPLATE = """
# Plugin Metadata
# name: Plugin Name
# description: Short description
# version: 1.0.0
# author: Author Name

# PyQt6 pyqtSlot functions will be automatically loaded
"""

# Load all plugins
def load_plugins(extensions_dir=None):
    """Load all plugins from the extensions directory."""
    import importlib
    import os
    
    ext_dir = extensions_dir or EXTENSIONS_DIR
    if not os.path.exists(ext_dir):
        return
    
    for file in os.listdir(ext_dir):
        if not file.endswith('.py'):
            continue
        
        if file.startswith('__'):
            continue
        
        try:
            # Import the module
            module_name = file[:-3]  # Remove .py extension
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
            
            _registered_plugins[file[:-3]] = {
                'module': module,
                'metadata': metadata,
                'functions': plugin_functions,
                'file': file,
            }
            
        except Exception as e:
            print(f"Failed to load plugin {file}: {e}")
    
    return _registered_plugins


def get_plugin(plugin_name):
    """Get a registered plugin by name."""
    return _registered_plugins.get(plugin_name)


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


# Example plugins (would be in extensions/ directory)
# -------------------------------------------------------
# # Plugin: Add Sample Raster
# # description: Loads sample GEBCO bathymetric data
# # version: 1.0.0
# # author: GeoSuite Team
# 
# # @pyqtSlot()
# # def load_sample_raster():
# #     """Load sample GEBCO bathymetric data."""
# #     import os
# #     from qgis.core import QgsRasterLayer
# #     
# #     path = r"D:\Geospatial_suite\RAW DATA\Bathymetric_Data\GEBCO_12_Sep_2025_660ee9b1cc91"
# #     layer = QgsRasterLayer(path, "GEBCO Bathymetric")
# #     if layer.isValid():
# #         QgsProject.instance().addMapLayer(layer)
# #         QMessageBox.information(None, "Success", "Sample raster loaded")
# #     else:
# #         QMessageBox.warning(None, "Error", "Failed to load raster layer")
# 
# # Plugin: Add Sample Vector
# # description: Loads sample point/line/polygon data
# # version: 1.0.0
# # author: GeoSuite Team
# 
# # @pyqtSlot()
# # def load_sample_vector():
# #     """Load sample vector data."""
# #     from qgis.core import QgsVectorLayer, QgsProject
# #     layer = QgsVectorLayer("Point?crs=EPSG:4326", "Sample Points", "memory")
# #     QgsProject.instance().addMapLayer(layer)
# -------------------------------------------------------

# Example usage
if __name__ == "__main__":
    # Load all plugins
    plugins = load_plugins()
    print(f"Loaded {len(plugins)} plugins:")
    for name, info in _registered_plugins.items():
        print(f"  - {name}: {info['metadata'].get('version', '?')} by {info['metadata'].get('author', '?')}")
        for func in info['functions']:
            print(f"    - {func}")
"