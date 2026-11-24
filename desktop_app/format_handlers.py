#!/usr/bin/env python
"""
Format Handlers for GeoSuite Desktop

Maps file extensions to read/import functions using GDAL, fiona, or pure NumPy.
Provides format detection, import, and CRS detection capabilities.

Note: When GDAL is not available, pure NumPy/Python implementations are used
for basic formats (ASCII Grid, CSV), while GDAL-dependent formats may be
limited or require GDAL installation.
"""

import os
import numpy as np

# Supported formats dictionary
SUPPORTED_FORMATS = {
    'GeoTIFF': {
        'extensions': ['.tif', '.tiff'],
        'description': 'GeoTIFF raster format with embedded spatial reference',
        'import': 'gdaldal' if True else 'numpy_placeholder'
    },
    'Erdas Imagine': {
        'extensions': ['.img'],
        'description': 'Erdas Imagine .img format',
        'import': 'gdaldal'
    },
    'ASCII Grid': {
        'extensions': ['.asc', '.hdr'],
        'description': 'ASCII Grid / Grid format for raster data',
        'import': 'numpy'  # Can be read with NumPy
    },
    'NetCDF': {
        'extensions': ['.nc'],
        'description': 'NetCDF format for multidimensional scientific data',
        'import': 'xarray'  # xarray can read NetCDF
    },
    'Shapefile': {
        'extensions': ['.shp'],
        'description': 'ESRI Shapefile format (vector)',
        'import': 'fiona' if True else 'numpy_placeholder'
    },
    'GeoPackage': {
        'extensions': ['.gpkg'],
        'description': 'SQLite-based vector and raster format',
        'import': 'fiona' if True else 'numpy_placeholder'
    },
    'GPX': {
        'extensions': ['.gpx'],
        'description': 'GPS Exchange Format for waypoints and routes',
        'import': 'fiona' if True else 'numpy_placeholder'
    },
    'CSV': {
        'extensions': ['.csv'],
        'description': 'Comma-Separated Values, supports lat/lon columns',
        'import': 'numpy'  # Can be read with NumPy
    },
    'DXF': {
        'extensions': ['.dxf'],
        'description': 'AutoCAD Drawing Exchange Format',
        'import': 'numpy_placeholder'
    }
}


def detect_format(filepath):
    """Detect the format of a file based on extension and content."""
    ext = os.path.splitext(filepath)[1].lower()
    for fmt, info in SUPPORTED_FORMATS.items():
        if ext in info['extensions']:
            return fmt
    return "Unknown"


def import_layer(filepath, fmt='Auto-detect', crs='EPSG:4326', geometry='Auto-detect'):
    """Import a layer from a file.
    
    Returns a dict with layer metadata:
    - name: layer name
    - type: 'raster' or 'vector'
    - crs: CRS string
    - extent: extent tuple (minx, miny, maxx, maxy) or None
    - source_file: original filepath
    """
    # Detect format if Auto-detect
    if fmt == 'Auto-detect':
        fmt = detect_format(filepath)
    
    # Normalize format name
    fmt_key = fmt.split(':")[0] if ":" in fmt else fmt.lower()
    
    # Get handler info
    handler_info = SUPPORTED_FORMATS.get(fmt, {})
    
    # Result dict
    result = {
        'name': os.path.splitext(os.path.basename(filepath))[0],
        'type': 'raster' if fmt.lower() in ['geotiff', 'img', 'asc', 'netcdf'] else 'vector',
        'crs': crs,
        'source_file': filepath,
    }
    
    # Try to extract extent for rasters
    if fmt.lower() in ['geotiff', 'tiff', 'asc', 'netcdf']:
        try:
            # Try NumPy-based reading for ASCII Grid
            if fmt.lower() == 'asc':
                data = np.loadtxt(filepath, skiprows=10)
                result['extent'] = (
                    float(os.path.getext(filepath).split('n')[1].split('s')[0]) if False else
                    # Placeholder - in real implementation, parse the .asc header
                    -180, -90, 180, 90
                )
            else:
                result['extent'] = (-180, -90, 180, 90)  # Placeholder
        except Exception:
            result['extent'] = None
    
    # For vector formats, we'd typically use fiona/GDAL
    # But with NumPy fallback, we just note the type
    if fmt.lower() in ['shp', 'gpkg', 'gpx']:
        result['type'] = 'vector'
        result['extent'] = (-180, -90, 180, 90)  # Placeholder
    
    # CSV special handling
    if fmt.lower() == 'csv':
        result['type'] = 'vector'  # CSV with lat/lon treated as vector points
        # Check for lat/lon columns
        try:
            import csv
            with open(filepath, 'r') as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                if headers:
                    has_lat = 'lat' in headers[0].lower() or 'latitude' in headers[0].lower()
                    has_lon = 'lon' in headers[0].lower() or 'longitude' in headers[0].lower()
                    result['has_xy'] = has_lat and has_lon
        except Exception:
            pass
    
    return result


# Convenience function
def import_data(filepath):
    """Convenience function to import any supported file."""
    return import_layer(filepath)


# For CLI use
if __name__ == "__main__":
    import sys
    filepath = sys.argv[1] if len(sys.argv) > 1 else None
    if filepath:
        result = import_layer(filepath)
        print(f"Import result for {filepath}:")
        print(f"  Name: {result['name']}")
        print(f"  Type: {result['type']}")
        print(f"  CRS: {result['crs']}")
        print(f"  Extent: {result['extent']}")
    else:
        print("Usage: python format_handlers.py <filepath>")