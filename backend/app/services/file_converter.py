"""
Universal file converter for geospatial formats.
Handles conversions between GPX, KML, GeoJSON, Shapefile, etc.
"""
import os
import tempfile
import json
from typing import Dict, List, Optional, BinaryIO
from pathlib import Path

# GDAL for format conversions
from osgeo import gdal, ogr, osr

# For KML/GPX parsing
import gpxpy
import fastkml

class FileConverterService:
    """
    Service for converting between different geospatial file formats.
    Supports: GPX, KML, GeoJSON, Shapefile, CSV, GML, DWG, DXF
    """
    
    # Supported format conversions
    SUPPORTED_FORMATS = {
        'gpx': ['kml', 'geojson', 'csv', 'shp'],
        'kml': ['gpx', 'geojson', 'csv', 'shp'],
        'geojson': ['gpx', 'kml', 'csv', 'shp', 'gml'],
        'shp': ['gpx', 'kml', 'geojson', 'csv'],
        'csv': ['gpx', 'kml', 'geojson', 'shp'],
        'dwg': ['dxf', 'shp', 'geojson'],
        'dxf': ['dwg', 'shp', 'geojson']
    }
    
    def __init__(self):
        # GDAL configuration
        gdal.SetConfigOption('GDAL_DATA', '/usr/share/gdal')
        gdal.SetConfigOption('OGR_GPX_ELEV_AS_25D', 'YES')
    
    def convert_file(self, input_file: str, output_format: str, 
                    options: Optional[Dict] = None) -> Dict:
        """
        Convert a file from one format to another.
        
        Args:
            input_file: Path to input file
            output_format: Desired output format
            options: Conversion options (crs, precision, etc.)
        
        Returns:
            Dictionary with conversion results and output file path
        """
        # Validate input
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        # Get file extension
        input_ext = Path(input_file).suffix.lower()[1:]  # Remove dot
        
        # Check if conversion is supported
        if input_ext not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported input format: {input_ext}")
        
        if output_format.lower() not in self.SUPPORTED_FORMATS[input_ext]:
            raise ValueError(
                f"Cannot convert from {input_ext} to {output_format}. "
                f"Supported: {self.SUPPORTED_FORMATS[input_ext]}"
            )
        
        # Create temp directory for output
        temp_dir = tempfile.mkdtemp()
        output_file = os.path.join(
            temp_dir, 
            f"converted_{Path(input_file).stem}.{output_format}"
        )
        
        try:
            # Handle special conversions
            if input_ext == 'dwg' or input_ext == 'dxf':
                result = self._convert_cad_file(input_file, output_file, output_format)
            elif input_ext == 'gpx' and output_format == 'kml':
                result = self._convert_gpx_to_kml(input_file, output_file)
            elif input_ext == 'kml' and output_format == 'gpx':
                result = self._convert_kml_to_gpx(input_file, output_file)
            else:
                # Use GDAL/OGR for general conversions
                result = self._convert_with_gdal(input_file, output_file, output_format, options)
            
            # Read output file content
            with open(output_file, 'rb') as f:
                file_content = f.read()
            
            return {
                'success': True,
                'output_file': output_file,
                'output_format': output_format,
                'file_size': os.path.getsize(output_file),
                'file_content': file_content,
                'temporary': True
            }
            
        except Exception as e:
            # Cleanup on error
            if os.path.exists(output_file):
                os.remove(output_file)
            raise Exception(f"Conversion failed: {str(e)}")
    
    def _convert_with_gdal(self, input_file: str, output_file: str, 
                          output_format: str, options: Optional[Dict]) -> Dict:
        """
        Convert using GDAL/OGR driver.
        """
        # Set conversion options
        driver_name = self._get_gdal_driver_name(output_format)
        
        # Open input datasource
        input_ds = ogr.Open(input_file)
        if input_ds is None:
            raise ValueError(f"Could not open file: {input_file}")
        
        try:
            # Get the driver for output format
            driver = ogr.GetDriverByName(driver_name)
            if driver is None:
                raise ValueError(f"Unsupported output format: {output_format}")
            
            # Create output datasource
            output_ds = driver.CreateDataSource(output_file)
            if output_ds is None:
                raise ValueError(f"Could not create output file: {output_file}")
            
            # Copy layers
            for i in range(input_ds.GetLayerCount()):
                in_layer = input_ds.GetLayerByIndex(i)
                
                # Create output layer
                out_layer = output_ds.CreateLayer(
                    in_layer.GetName(),
                    in_layer.GetSpatialRef(),
                    in_layer.GetGeomType()
                )
                
                # Copy field definitions
                in_layer_defn = in_layer.GetLayerDefn()
                for j in range(in_layer_defn.GetFieldCount()):
                    field_defn = in_layer_defn.GetFieldDefn(j)
                    out_layer.CreateField(field_defn)
                
                # Copy features
                in_layer.ResetReading()
                for feature in in_layer:
                    out_feature = ogr.Feature(out_layer.GetLayerDefn())
                    out_feature.SetGeometry(feature.GetGeometryRef().Clone())
                    
                    # Copy fields
                    for j in range(in_layer_defn.GetFieldCount()):
                        field_name = in_layer_defn.GetFieldDefn(j).GetName()
                        out_feature.SetField(field_name, feature.GetField(j))
                    
                    out_layer.CreateFeature(out_feature)
                    out_feature = None
            
            # Cleanup
            output_ds = None
            input_ds = None
            
            return {'success': True}
            
        finally:
            # Ensure cleanup
            if 'input_ds' in locals():
                input_ds = None
            if 'output_ds' in locals():
                output_ds = None
    
    def _convert_gpx_to_kml(self, input_file: str, output_file: str) -> Dict:
        """
        Convert GPX to KML with elevation support.
        """
        import xml.etree.ElementTree as ET
        
        # Parse GPX
        with open(input_file, 'r') as f:
            gpx_content = f.read()
        
        # Create KML structure
        kml_root = ET.Element('kml', xmlns="http://www.opengis.net/kml/2.2")
        document = ET.SubElement(kml_root, 'Document')
        
        # Parse GPX and convert to KML
        try:
            gpx = gpxpy.parse(gpx_content)
            
            # Convert tracks
            for track in gpx.tracks:
                folder = ET.SubElement(document, 'Folder')
                name = ET.SubElement(folder, 'name')
                name.text = track.name or 'Unnamed Track'
                
                for segment in track.segments:
                    for point in segment.points:
                        placemark = ET.SubElement(folder, 'Placemark')
                        
                        # Create point
                        point_elem = ET.SubElement(placemark, 'Point')
                        coordinates = ET.SubElement(point_elem, 'coordinates')
                        coordinates.text = f"{point.longitude},{point.latitude},{point.elevation or 0}"
            
            # Write KML file
            tree = ET.ElementTree(kml_root)
            tree.write(output_file, encoding='utf-8', xml_declaration=True)
            
            return {'success': True}
            
        except Exception as e:
            raise Exception(f"GPX to KML conversion failed: {str(e)}")
    
    def _convert_kml_to_gpx(self, input_file: str, output_file: str) -> Dict:
        """
        Convert KML to GPX format.
        """
        from fastkml import kml
        
        # Parse KML
        with open(input_file, 'r') as f:
            kml_content = f.read()
        
        # Create GPX
        gpx = gpxpy.gpx.GPX()
        
        try:
            # Parse KML (simplified - would need full KML parsing)
            # This is a basic implementation
            import xml.etree.ElementTree as ET
            root = ET.fromstring(kml_content)
            
            # Find coordinates in KML
            for coordinates in root.findall('.//{http://www.opengis.net/kml/2.2}coordinates'):
                coords_text = coordinates.text.strip()
                points = []
                
                for coord in coords_text.split():
                    parts = coord.split(',')
                    if len(parts) >= 2:
                        lon, lat = float(parts[0]), float(parts[1])
                        elev = float(parts[2]) if len(parts) > 2 else 0
                        points.append((lat, lon, elev))
                
                if points:
                    # Create track
                    track = gpxpy.gpx.GPXTrack()
                    segment = gpxpy.gpx.GPXTrackSegment()
                    
                    for lat, lon, elev in points:
                        point = gpxpy.gpx.GPXTrackPoint(lat, lon, elev)
                        segment.points.append(point)
                    
                    track.segments.append(segment)
                    gpx.tracks.append(track)
            
            # Write GPX file
            with open(output_file, 'w') as f:
                f.write(gpx.to_xml())
            
            return {'success': True}
            
        except Exception as e:
            raise Exception(f"KML to GPX conversion failed: {str(e)}")
    
    def _convert_cad_file(self, input_file: str, output_file: str, 
                         output_format: str) -> Dict:
        """
        Convert CAD files (DWG/DXF) to GIS formats.
        Note: Requires ODA converter or similar.
        """
        # This is a simplified implementation
        # In production, you would use ODA File Converter or ezdxf
        
        if output_format == 'dxf':
            # DWG to DXF conversion
            # Using ezdxf for demonstration
            import ezdxf
            
            try:
                doc = ezdxf.readfile(input_file)
                doc.saveas(output_file)
                return {'success': True}
            except Exception as e:
                raise Exception(f"DWG to DXF conversion failed: {str(e)}")
        
        elif output_format in ['shp', 'geojson']:
            # CAD to Shapefile/GeoJSON
            # This requires proper CAD to GIS conversion
            raise NotImplementedError(
                "CAD to GIS conversion requires additional libraries. "
                "Consider using OGR with CAD driver or specialized tools."
            )
        
        else:
            raise ValueError(f"Unsupported CAD output format: {output_format}")
    
    def _get_gdal_driver_name(self, format: str) -> str:
        """
        Get GDAL driver name for format.
        """
        driver_map = {
            'shp': 'ESRI Shapefile',
            'geojson': 'GeoJSON',
            'kml': 'KML',
            'gpx': 'GPX',
            'csv': 'CSV',
            'gml': 'GML',
            'dxf': 'DXF'
        }
        
        return driver_map.get(format.lower(), format.upper())
    
    def batch_convert(self, input_files: List[str], output_format: str,
                     output_dir: Optional[str] = None) -> Dict:
        """
        Convert multiple files at once.
        
        Args:
            input_files: List of input file paths
            output_format: Desired output format
            output_dir: Directory for output files (optional)
        
        Returns:
            Dictionary with results for each conversion
        """
        results = []
        
        for input_file in input_files:
            try:
                result = self.convert_file(input_file, output_format)
                results.append({
                    'input_file': input_file,
                    'success': True,
                    'output_file': result['output_file'],
                    'file_size': result['file_size']
                })
            except Exception as e:
                results.append({
                    'input_file': input_file,
                    'success': False,
                    'error': str(e)
                })
        
        return {
            'total_files': len(input_files),
            'successful': len([r for r in results if r['success']]),
            'failed': len([r for r in results if not r['success']]),
            'results': results
        }
    
    def get_supported_conversions(self) -> Dict:
        """
        Get all supported format conversions.
        """
        return self.SUPPORTED_FORMATS