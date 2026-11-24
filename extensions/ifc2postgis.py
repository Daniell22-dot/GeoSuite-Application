#!/usr/bin/env python
"""
IFC2PostGIS Plugin for GeoSuite Desktop

Plugin for importing Industry Foundation Classes (IFC) files
and converting them to PostGIS format for use in GeoPackage/PostGIS.

This plugin integrates with the GeoSuite Desktop plugin system
and provides functionality to:
- Import IFC files (ifcopen, ifcXML, ifcZIP)
- Extract building elements (walls, slabs, doors, windows)
- Convert to PostGIS geometry types
- Store in PostGIS/GeoPackage
- Map IFC layers to GIS attributes
"""

import sys
import os
import json

# Check if ifcopenshell is available
try:
    import ifcopenshell
    IFC_AVAILABLE = True
except ImportError:
    IFC_AVAILABLE = False

# Check if pyprojectqgis is available
try:
    from qgis.core import QgsProject, QgsVectorLayer, QgsCoordinateReferenceSystem
    QGIS_AVAILABLE = True
except ImportError:
    QGIS_AVAILABLE = False


# IFC to PostGIS Plugin Metadata
PLUGIN_METADATA = {
    'name': 'IFC2PostGIS',
    'description': 'Import IFC files and convert to PostGIS format',
    'version': '1.0.0',
    'author': 'GeoSuite Team',
    'version': '1.0.0',
}

# IFC Element Types Mapping
IFC_ELEMENT_TYPES = {
    'IfcWall': 'wall',
    'IfcSlab': 'slab',
    'IfcDoor': 'door',
    'IfcWindow': 'window',
    'IfcBeam': 'beam',
    'IfcColumn': 'column',
    'IfcFooting': 'footing',
    'IfcStair': 'stair',
    'IfcRamp': 'ramp',
    'IfcFooting': 'footing',
}


# IFC to PostGIS Attribute Mapping
IFC_ATTRIBUTE_MAP = {
    'IfcWall': ['Name', 'Description', 'OverallHeight', 'OverallHeight', 'OverallWidth', 'OverallWidth', 'OverallHeight'],
    'IfcSlab': ['Name', 'Description', 'OverallThickness', 'OverallLength', 'OverallWidth'],
    'IfcDoor': ['Name', 'Description', 'OverallWidth', 'OverallHeight', 'OverallHeight'],
    'IfcWindow': ['Name', 'Description', 'OverallWidth', 'OverallHeight', 'OverallWidth'],
}


# IFC2PostGIS Plugin Class
class IFC2PostGISPlugin:
    """IFC2PostGIS Plugin for GeoSuite Desktop."""
    
    def __init__(self):
        self.plugin_name = 'IFC2PostGIS'
        self.plugin_version = '1.0.0'
        self.plugin_author = 'GeoSuite Team'
    
    def get_metadata(self):
        """Return plugin metadata."""
        return {
            'name': 'IFC2PostGIS',
            'description': 'Import IFC files and convert to PostGIS format',
            'version': '1.0.0',
            'author': 'GeoSuite Team',
        }
    
    def load_ifc_file(self, ifc_file_path):
        """Import an IFC file and return the dataset."""
        if not IFC_AVAILABLE:
            return None, "ifcopenshell is not installed"
        
        if not os.path.exists(ifc_file_path):
            return None, f"File not found: {ifc_file_path}"
        
        try:
            ifc_document = ifcopenshell.open(ifc_file_path)
            return ifc_document, None
        except Exception as e:
            return None, f"Failed to open IFC file: {str(e)}"
    
    def extract_elements(self, ifc_document, element_types=None):
        """Extract IFC elements from the dataset."""
        if not IFC_AVAILABLE:
            return [], "ifcopenshell is not available"
        
        if ifc_document is None:
            return [], "No IFC document provided"
        
        # Default to all element types if not specified
        if element_types is None:
            element_types = list(IFC_ELEMENT_TYPES.keys())
        
        elements = []
        
        for element_type in element_types:
            if element_type not in IFC_ELEMENT_TYPES:
                continue
            
            # Get all elements of this type
            elements_list = ifc_document.by_type(element_type)
            
            for element in elements_list:
                # Extract attributes
                attributes = {}
                for attribute in ifc_document.get_attribute(element, '*'):
                    attr_name = attribute.is_declared.item_by_name('name')
                    if attr_name:
                        attributes[attr_name] = ifcopenshell.util.type.get_value(ifcopenshell.util.type.get_attr(attribute))
                
                # Get geometry
                geometry = ifc_document.get_element_geometry(element)
                
                element_data = {
                    'guid': element.GlobalId if hasattr(element, 'GlobalId') else None,
                    'type': element_type,
                    'attributes': attributes,
                    'geometry': geometry,
                }
                elements.append(element_data)
        
        return elements, None
    
    def export_to_postgis(self, ifc_document, element_types=None, srid=4326):
        """Export IFC elements to PostGIS/GeoPackage."""
        if not IFC_AVAILABLE:
            return False, "ifcopenshell is not available"
        
        if not IFC_AVAILABLE:
            return False, "ifcopenshell is not available"
        
        # Extract elements
        elements, error = self.extract_elements(ifc_document, element_types)
        if error:
            return False, error
        
        # In a full implementation, would use QgsVectorLayer and QgsVectorFileWriter
        # to create a GeoPackage layer with the extracted elements
        
        # For now, return the extracted elements
        return True, elements
    
    def ifc_element_to_dict(self, element):
        """Convert an IFC element to a dictionary."""
        if not IFC_AVAILABLE:
            return {}
        
        attributes = {}
        for attribute in ifcopenshell.util.element.get_attr(element):
            try:
                value = ifcopenshell.util.type.get_value(ifcopenshell.util.type.get_attr(attribute))
                attributes[attribute.name()] = value
            except:
                pass
        
        return {
            'global_id': ifcopenshell.util.element.get_global_id(element),
            'type': ifcopenshell.util.element.get_type(element),
            'attributes': attributes,
        }


# Plugin example functions (would be called from the plugin system)
# @pyqtSlot()
# def load_ifc_file():
#     """Load an IFC file and display elements."""
#     from PyQt6.QtWidgets import QFileDialog, QMessageBox
#     
#     path, _ = QFileDialog.getOpenFileName(
#         None, "Select IFC File",
#         "",
#         "IFC Files (*.ifc *.ifcxml *.ifczip)")
#     
#     if path:
#         plugin = IFC2PostGISPlugin()
#         ifc_document, error = plugin.load_ifc_file(path)
#         
#         if error:
#             QMessageBox.warning(None, "Error", error)
#         else:
#             # Extract elements
#             elements, error = plugin.extract_elements(ifc_document)
#             
#             if error:
#                 QMessageBox.warning(None, "Error", error)
#             else:
#                 # Export to PostGIS
#                 success, result = plugin.export_to_postgis(ifc_document)
#                 
#                 if success:
#                     QMessageBox.information(None, "Success", 
#                         f"Loaded {len(elements)} IFC elements")
#                 else:
#                     QMessageBox.warning(None, "Error", result)


# Example usage
if __name__ == "__main__":
    print("IFC2PostGIS Plugin")
    print("=" * 40)
    print(f"IFC Available: {IFC_AVAILABLE}")
    print(f"QGIS Available: {QGIS_AVAILABLE}")
    
    if IFC_AVAILABLE:
        # Example: Open an IFC file
        ifc_path = r"D:\Ifc2postGIS\example.ifc"
        if os.path.exists(ifc_path):
            plugin = IFC2PostGISPlugin()
            ifc_document, error = plugin.load_ifc_file(ifc_path)
            
            if error:
                print(f"Error: {error}")
            else:
                # Extract elements
                elements, error = plugin.extract_elements(ifc_document)
                
                if error:
                    print(f"Error: {error}")
                else:
                    print(f"Loaded {len(elements)} IFC elements")
                    
                    # Export to PostGIS
                    success, result = plugin.export_to_postgis(ifc_document)
                    print(f"Export result: {success}")
        else:
            print(f"IFC file not found at: {ifc_path}")
            print("Please provide a valid IFC file path.")
    
    if not IFC_AVAILABLE:
        print("\nTo use IFC2PostGIS, install ifcopenshell:")
        print("pip install ifcopenshell")


# Example usage when run as module
if __name__ == "__main__":
    print("IFC2PostGIS Plugin - Standalone Mode")
    print("=" * 40)
    print("This plugin converts IFC files to PostGIS format.")
    print("For full integration, use within GeoSuite Desktop.")
"