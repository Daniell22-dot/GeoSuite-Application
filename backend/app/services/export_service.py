"""
Export service for converting and downloading files in various formats.
"""
import os
import zipfile
import tempfile
import json
from typing import Dict, List, Optional, BinaryIO
from pathlib import Path
from datetime import datetime
import shutil

from app.services.file_converter import FileConverterService
from app.services.gps_service import GPSService
from app.services.watershed_service import WatershedService
from app.services.marine_service import MarineChartService
from app.services.hecras_service import HECRASService

try:
    import geospatial_cpp
    geospatial_cpp_available = True
except ImportError:
    geospatial_cpp_available = False

class ExportService:
    """
    Service for exporting data in various formats.
    Supports: GPX, KML, GeoJSON, Shapefile, CSV, PDF, PNG, GeoTIFF
    """
    
    def __init__(self):
        self.file_converter = FileConverterService()
        self.gps_service = GPSService()
        self.watershed_service = WatershedService()
        self.marine_service = MarineChartService()
        self.hecras_service = HECRASService()
    
    def export_gps_data(self, gps_data: Dict, format: str, 
                       include_metadata: bool = True) -> Dict:
        """
        Export GPS data to various formats.
        
        Args:
            gps_data: GPS data dictionary
            format: Output format (gpx, kml, geojson, csv, shp)
            include_metadata: Whether to include metadata
        
        Returns:
            Dictionary with export results
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create base filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_filename = f"gps_export_{timestamp}"
            
            if format.lower() == 'gpx':
                output = self._export_to_gpx(gps_data, temp_dir, base_filename)
            elif format.lower() == 'kml':
                output = self._export_to_kml(gps_data, temp_dir, base_filename)
            elif format.lower() == 'geojson':
                output = self._export_to_geojson(gps_data, temp_dir, base_filename)
            elif format.lower() == 'csv':
                output = self._export_to_csv(gps_data, temp_dir, base_filename)
            elif format.lower() == 'shp':
                output = self._export_to_shapefile(gps_data, temp_dir, base_filename)
            else:
                raise ValueError(f"Unsupported GPS export format: {format}")
            
            # Add metadata if requested
            if include_metadata:
                self._add_metadata_file(gps_data, output['file_path'])
            
            # Read file content
            with open(output['file_path'], 'rb') as f:
                file_content = f.read()
            
            return {
                'success': True,
                'filename': output['filename'],
                'format': format,
                'file_size': len(file_content),
                'file_content': file_content,
                'mime_type': self._get_mime_type(format)
            }
    
    def export_watershed_data(self, watershed_data: Dict, format: str) -> Dict:
        """
        Export watershed analysis results.
        
        Args:
            watershed_data: Watershed analysis results
            format: Output format (geojson, shp, pdf, png)
        
        Returns:
            Dictionary with export results
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_filename = f"watershed_export_{timestamp}"
            
            if format.lower() == 'geojson':
                output = self._export_watershed_geojson(watershed_data, temp_dir, base_filename)
            elif format.lower() == 'shp':
                output = self._export_watershed_shapefile(watershed_data, temp_dir, base_filename)
            elif format.lower() == 'pdf':
                output = self._export_watershed_pdf(watershed_data, temp_dir, base_filename)
            elif format.lower() == 'png':
                output = self._export_watershed_png(watershed_data, temp_dir, base_filename)
            else:
                raise ValueError(f"Unsupported watershed export format: {format}")
            
            with open(output['file_path'], 'rb') as f:
                file_content = f.read()
            
            return {
                'success': True,
                'filename': output['filename'],
                'format': format,
                'file_size': len(file_content),
                'file_content': file_content,
                'mime_type': self._get_mime_type(format)
            }
    
    def export_marine_data(self, marine_data: Dict, format: str) -> Dict:
        """
        Export marine chart data.
        
        Args:
            marine_data: Marine chart data
            format: Output format (geotiff, png, jpg, pdf)
        
        Returns:
            Dictionary with export results
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_filename = f"marine_export_{timestamp}"
            
            if format.lower() in ['geotiff', 'tiff', 'tif']:
                output = self._export_marine_geotiff(marine_data, temp_dir, base_filename)
            elif format.lower() in ['png', 'jpg', 'jpeg']:
                output = self._export_marine_image(marine_data, temp_dir, base_filename, format)
            elif format.lower() == 'pdf':
                output = self._export_marine_pdf(marine_data, temp_dir, base_filename)
            else:
                raise ValueError(f"Unsupported marine export format: {format}")
            
            with open(output['file_path'], 'rb') as f:
                file_content = f.read()
            
            return {
                'success': True,
                'filename': output['filename'],
                'format': format,
                'file_size': len(file_content),
                'file_content': file_content,
                'mime_type': self._get_mime_type(format)
            }
    
    def export_hecras_results(self, results: Dict, format: str) -> Dict:
        """
        Export HEC-RAS analysis results.
        
        Args:
            results: HEC-RAS results
            format: Output format (geojson, csv, pdf, xlsx)
        
        Returns:
            Dictionary with export results
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_filename = f"hecras_export_{timestamp}"
            
            if format.lower() == 'geojson':
                output = self._export_hecras_geojson(results, temp_dir, base_filename)
            elif format.lower() == 'csv':
                output = self._export_hecras_csv(results, temp_dir, base_filename)
            elif format.lower() == 'pdf':
                output = self._export_hecras_pdf(results, temp_dir, base_filename)
            elif format.lower() == 'xlsx':
                output = self._export_hecras_excel(results, temp_dir, base_filename)
            else:
                raise ValueError(f"Unsupported HEC-RAS export format: {format}")
            
            with open(output['file_path'], 'rb') as f:
                file_content = f.read()
            
            return {
                'success': True,
                'filename': output['filename'],
                'format': format,
                'file_size': len(file_content),
                'file_content': file_content,
                'mime_type': self._get_mime_type(format)
            }
    
    def create_export_package(self, exports: List[Dict], package_name: str = None) -> Dict:
        """
        Create a ZIP package of multiple exports.
        
        Args:
            exports: List of export dictionaries
            package_name: Name for the package
        
        Returns:
            Dictionary with ZIP package
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            if not package_name:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                package_name = f"geosuite_export_{timestamp}"
            
            zip_path = os.path.join(temp_dir, f"{package_name}.zip")
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add export files
                for export in exports:
                    if export.get('success'):
                        filename = export['filename']
                        file_content = export.get('file_content')
                        
                        if file_content:
                            # Write to temp file
                            temp_file = os.path.join(temp_dir, filename)
                            with open(temp_file, 'wb') as f:
                                f.write(file_content)
                            
                            # Add to ZIP
                            zipf.write(temp_file, filename)
                
                # Add manifest
                manifest = {
                    'export_date': datetime.now().isoformat(),
                    'total_files': len(exports),
                    'files': [
                        {
                            'filename': e['filename'],
                            'format': e['format'],
                            'file_size': e['file_size']
                        }
                        for e in exports if e.get('success')
                    ]
                }
                
                manifest_path = os.path.join(temp_dir, 'manifest.json')
                with open(manifest_path, 'w') as f:
                    json.dump(manifest, f, indent=2)
                
                zipf.write(manifest_path, 'manifest.json')
            
            # Read ZIP content
            with open(zip_path, 'rb') as f:
                zip_content = f.read()
            
            return {
                'success': True,
                'filename': f"{package_name}.zip",
                'format': 'zip',
                'file_size': len(zip_content),
                'file_content': zip_content,
                'mime_type': 'application/zip',
                'contains': len(exports)
            }
    
    def _export_to_gpx(self, gps_data: Dict, temp_dir: str, base_filename: str) -> Dict:
        """Export GPS data to GPX format."""
        from gpxpy.gpx import GPX, GPXTrack, GPXTrackSegment, GPXTrackPoint
        import gpxpy
        
        gpx = GPX()
        
        # Create track
        gpx_track = GPXTrack()
        gpx_track.name = gps_data.get('metadata', {}).get('name', 'Exported Track')
        gpx_track.description = gps_data.get('metadata', {}).get('description', '')
        
        # Add segments
        for track in gps_data.get('tracks', []):
            for segment in track.get('segments', []):
                gpx_segment = GPXTrackSegment()
                
                for point in segment.get('points', []):
                    gpx_point = GPXTrackPoint(
                        latitude=point.get('latitude'),
                        longitude=point.get('longitude'),
                        elevation=point.get('elevation_corrected') or point.get('elevation')
                    )
                    
                    if point.get('time'):
                        from datetime import datetime
                        try:
                            gpx_point.time = datetime.fromisoformat(point['time'].replace('Z', '+00:00'))
                        except:
                            pass
                    
                    gpx_segment.points.append(gpx_point)
                
                gpx_track.segments.append(gpx_segment)
        
        gpx.tracks.append(gpx_track)
        
        # Write to file
        filename = f"{base_filename}.gpx"
        file_path = os.path.join(temp_dir, filename)
        
        with open(file_path, 'w') as f:
            f.write(gpx.to_xml())
        
        return {'filename': filename, 'file_path': file_path}
    
    def _export_to_kml(self, gps_data: Dict, temp_dir: str, base_filename: str) -> Dict:
        """Export GPS data to KML format."""
        import simplekml
        
        kml = simplekml.Kml()
        
        # Create folder for tracks
        track_folder = kml.newfolder(name="GPS Tracks")
        
        for track_idx, track in enumerate(gps_data.get('tracks', [])):
            for seg_idx, segment in enumerate(track.get('segments', [])):
                if segment.get('points'):
                    coords = []
                    for point in segment['points']:
                        coords.append((
                            point.get('longitude'),
                            point.get('latitude'),
                            point.get('elevation_corrected') or point.get('elevation') or 0
                        ))
                    
                    # Create linestring
                    linestring = track_folder.newlinestring(
                        name=f"Track {track_idx + 1} - Segment {seg_idx + 1}"
                    )
                    linestring.coords = coords
                    linestring.altitudemode = simplekml.AltitudeMode.absolute
                    
                    # Style
                    linestring.style.linestyle.color = simplekml.Color.blue
                    linestring.style.linestyle.width = 4
        
        filename = f"{base_filename}.kml"
        file_path = os.path.join(temp_dir, filename)
        kml.save(file_path)
        
        return {'filename': filename, 'file_path': file_path}
    
    def _export_to_geojson(self, gps_data: Dict, temp_dir: str, base_filename: str) -> Dict:
        """Export GPS data to GeoJSON format."""
        features = []
        
        # Export tracks as LineStrings
        for track_idx, track in enumerate(gps_data.get('tracks', [])):
            for seg_idx, segment in enumerate(track.get('segments', [])):
                if segment.get('points'):
                    coordinates = []
                    for point in segment['points']:
                        coordinates.append([
                            point.get('longitude'),
                            point.get('latitude'),
                            point.get('elevation_corrected') or point.get('elevation') or 0
                        ])
                    
                    feature = {
                        'type': 'Feature',
                        'geometry': {
                            'type': 'LineString',
                            'coordinates': coordinates
                        },
                        'properties': {
                            'name': track.get('name', f'Track {track_idx + 1}'),
                            'segment': seg_idx + 1,
                            'points': len(segment['points'])
                        }
                    }
                    features.append(feature)
        
        # Export waypoints as Points
        for wp_idx, waypoint in enumerate(gps_data.get('waypoints', [])):
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [
                        waypoint.get('longitude'),
                        waypoint.get('latitude'),
                        waypoint.get('elevation') or 0
                    ]
                },
                'properties': {
                    'name': waypoint.get('name', f'Waypoint {wp_idx + 1}'),
                    'description': waypoint.get('description', '')
                }
            }
            features.append(feature)
        
        geojson = {
            'type': 'FeatureCollection',
            'features': features,
            'properties': {
                'export_date': datetime.now().isoformat(),
                'source': 'GeoSuite',
                'total_tracks': len(gps_data.get('tracks', [])),
                'total_waypoints': len(gps_data.get('waypoints', []))
            }
        }
        
        filename = f"{base_filename}.geojson"
        file_path = os.path.join(temp_dir, filename)
        
        with open(file_path, 'w') as f:
            json.dump(geojson, f, indent=2)
        
        return {'filename': filename, 'file_path': file_path}
    
    def _export_to_csv(self, gps_data: Dict, temp_dir: str, base_filename: str) -> Dict:
        """Export GPS data to CSV format."""
        import csv
        
        filename = f"{base_filename}.csv"
        file_path = os.path.join(temp_dir, filename)
        
        with open(file_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow([
                'track_name', 'segment', 'point_index',
                'latitude', 'longitude', 'elevation',
                'elevation_corrected', 'time', 'speed',
                'cumulative_distance'
            ])
            
            # Write data
            cumulative_distance = 0
            for track in gps_data.get('tracks', []):
                for seg_idx, segment in enumerate(track.get('segments', [])):
                    for pt_idx, point in enumerate(segment.get('points', [])):
                        # Calculate distance (simplified)
                        if pt_idx > 0:
                            prev_point = segment['points'][pt_idx - 1]
                            import math
                            lat1, lon1 = prev_point['latitude'], prev_point['longitude']
                            lat2, lon2 = point['latitude'], point['longitude']
                            distance = math.sqrt((lat2-lat1)**2 + (lon2-lon1)**2) * 111000
                            cumulative_distance += distance
                        
                        writer.writerow([
                            track.get('name', ''),
                            seg_idx + 1,
                            pt_idx + 1,
                            point.get('latitude'),
                            point.get('longitude'),
                            point.get('elevation'),
                            point.get('elevation_corrected'),
                            point.get('time', ''),
                            point.get('speed', ''),
                            cumulative_distance
                        ])
        
        return {'filename': filename, 'file_path': file_path}
    
    def _export_to_shapefile(self, gps_data: Dict, temp_dir: str, base_filename: str) -> Dict:
        """Export GPS data to Shapefile format."""
        if geospatial_cpp_available:
            # Use our new C++ write_vector_file
            # First, get GeoJSON representation
            geojson_res = self._export_to_geojson(gps_data, temp_dir, "temp_geojson")
            with open(geojson_res['file_path'], 'r') as f:
                geojson_str = f.read()
            
            shp_dir = os.path.join(temp_dir, base_filename)
            os.makedirs(shp_dir, exist_ok=True)
            shp_path = os.path.join(shp_dir, f"{base_filename}.shp")
            
            geospatial_cpp.write_vector_file(geojson_str, shp_path, "ESRI Shapefile")
            
            # Create ZIP of shapefile components
            zip_filename = f"{base_filename}_shapefile.zip"
            zip_path = os.path.join(temp_dir, zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in os.listdir(shp_dir):
                    file_path = os.path.join(shp_dir, file)
                    zipf.write(file_path, file)
            
            return {'filename': zip_filename, 'file_path': zip_path}
        else:
            # Fallback to GeoJSON if C++ module not compiled yet
            return self._export_to_geojson(gps_data, temp_dir, base_filename)
    
    def _export_watershed_geojson(self, watershed_data: Dict, temp_dir: str, base_filename: str) -> Dict:
        """Export watershed data to GeoJSON."""
        features = []
        
        # Watershed boundary
        if watershed_data.get('watershed', {}).get('boundary'):
            features.append({
                'type': 'Feature',
                'geometry': watershed_data['watershed']['boundary'],
                'properties': {
                    'type': 'watershed_boundary',
                    'area_km2': watershed_data['watershed'].get('area_km2'),
                    'perimeter_km': watershed_data['watershed'].get('perimeter_km')
                }
            })
        
        # Stream network
        if watershed_data.get('streams', {}).get('network'):
            stream_features = watershed_data['streams']['network'].get('features', [])
            features.extend(stream_features)
        
        geojson = {
            'type': 'FeatureCollection',
            'features': features,
            'properties': {
                'export_date': datetime.now().isoformat(),
                'data_type': 'watershed_analysis',
                'pour_point': watershed_data.get('pour_point'),
                'statistics': watershed_data.get('watershed', {}).get('elevation_stats', {})
            }
        }
        
        filename = f"{base_filename}.geojson"
        file_path = os.path.join(temp_dir, filename)
        
        with open(file_path, 'w') as f:
            json.dump(geojson, f, indent=2)
        
        return {'filename': filename, 'file_path': file_path}
    
    def _export_watershed_shapefile(self, watershed_data: Dict, temp_dir: str, base_filename: str) -> Dict:
        """Export watershed data to Shapefile."""
        if geospatial_cpp_available:
            # Create GeoJSON first
            geojson_export = self._export_watershed_geojson(watershed_data, temp_dir, base_filename)
            with open(geojson_export['file_path'], 'r') as f:
                geojson_str = f.read()
            
            # Save to shapefile using C++
            shp_dir = os.path.join(temp_dir, f"{base_filename}_shp")
            os.makedirs(shp_dir, exist_ok=True)
            shp_path = os.path.join(shp_dir, f"{base_filename}.shp")
            
            geospatial_cpp.write_vector_file(geojson_str, shp_path, "ESRI Shapefile")
            
            # Create ZIP
            zip_filename = f"{base_filename}_shapefile.zip"
            zip_path = os.path.join(temp_dir, zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in os.listdir(shp_dir):
                    file_path = os.path.join(shp_dir, file)
                    zipf.write(file_path, file)
            
            return {'filename': zip_filename, 'file_path': zip_path}
        else:
            return self._export_watershed_geojson(watershed_data, temp_dir, base_filename)
    
    def _export_watershed_pdf(self, watershed_data: Dict, temp_dir: str, base_filename: str) -> Dict:
        """Export watershed data to PDF report."""
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        import matplotlib.pyplot as plt
        import io
        
        filename = f"{base_filename}.pdf"
        file_path = os.path.join(temp_dir, filename)
        
        # Create PDF document
        doc = SimpleDocTemplate(
            file_path,
            pagesize=landscape(letter),
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1  # Center
        )
        story.append(Paragraph("Watershed Analysis Report", title_style))
        
        # Metadata
        meta_style = ParagraphStyle(
            'Meta',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.grey
        )
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", meta_style))
        story.append(Spacer(1, 20))
        
        # Statistics table
        if watershed_data.get('watershed'):
            stats = watershed_data['watershed']
            data = [
                ['Metric', 'Value'],
                ['Area', f"{stats.get('area_km2', 0):.2f} km²"],
                ['Perimeter', f"{stats.get('perimeter_km', 0):.2f} km"],
                ['Max Elevation', f"{stats.get('elevation_stats', {}).get('max', 0):.0f} m"],
                ['Min Elevation', f"{stats.get('elevation_stats', {}).get('min', 0):.0f} m"],
                ['Average Elevation', f"{stats.get('elevation_stats', {}).get('mean', 0):.0f} m"],
                ['Total Ascent', f"{stats.get('elevation_gain', 0):.0f} m"],
                ['Total Descent', f"{stats.get('elevation_loss', 0):.0f} m"]
            ]
            
            table = Table(data, colWidths=[2*inch, 2*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(table)
            story.append(Spacer(1, 30))
        
        # Stream network info
        if watershed_data.get('streams'):
            streams = watershed_data['streams']
            story.append(Paragraph("Stream Network", styles['Heading2']))
            
            stream_data = [
                ['Metric', 'Value'],
                ['Total Length', f"{streams.get('total_length_km', 0):.2f} km"],
                ['Number of Segments', streams.get('total_segments', 0)],
                ['Drainage Density', f"{streams.get('total_length_km', 0) / (stats.get('area_km2', 1) or 1):.2f} km/km²"]
            ]
            
            stream_table = Table(stream_data, colWidths=[2*inch, 2*inch])
            stream_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(stream_table)
        
        # Build PDF
        doc.build(story)
        
        return {'filename': filename, 'file_path': file_path}
    
    def _export_watershed_png(self, watershed_data: Dict, temp_dir: str, base_filename: str) -> Dict:
        """Export watershed visualization to PNG."""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
            from matplotlib.colors import LinearSegmentedColormap
            import numpy as np
            
            filename = f"{base_filename}.png"
            file_path = os.path.join(temp_dir, filename)
            
            # Create figure
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # Plot watershed boundary
            if watershed_data.get('watershed', {}).get('boundary'):
                # This is simplified - in production, you'd plot the actual geometry
                ax.text(0.5, 0.5, 'Watershed Visualization', 
                       ha='center', va='center', fontsize=20, transform=ax.transAxes)
            
            # Add title and info
            ax.set_title('Watershed Analysis', fontsize=16, fontweight='bold')
            
            if watershed_data.get('watershed'):
                stats = watershed_data['watershed']
                info_text = f"""
                Area: {stats.get('area_km2', 0):.2f} km²
                Perimeter: {stats.get('perimeter_km', 0):.2f} km
                Max Elevation: {stats.get('elevation_stats', {}).get('max', 0):.0f} m
                Min Elevation: {stats.get('elevation_stats', {}).get('min', 0):.0f} m
                """
                ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
                       verticalalignment='top', fontsize=10,
                       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            # Remove axes for cleaner look
            ax.axis('off')
            
            # Save figure
            plt.tight_layout()
            plt.savefig(file_path, dpi=300, bbox_inches='tight', facecolor='white')
            plt.close()
            
            return {'filename': filename, 'file_path': file_path}
            
        except ImportError:
            # Create a simple text file if matplotlib not available
            return self._export_watershed_text(watershed_data, temp_dir, base_filename)
    
    def _export_watershed_text(self, watershed_data: Dict, temp_dir: str, base_filename: str) -> Dict:
        """Export watershed data as text file."""
        filename = f"{base_filename}.txt"
        file_path = os.path.join(temp_dir, filename)
        
        with open(file_path, 'w') as f:
            f.write("WATERSHED ANALYSIS REPORT\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            if watershed_data.get('watershed'):
                stats = watershed_data['watershed']
                f.write("WATERSHED STATISTICS\n")
                f.write("-" * 30 + "\n")
                f.write(f"Area: {stats.get('area_km2', 0):.2f} km²\n")
                f.write(f"Perimeter: {stats.get('perimeter_km', 0):.2f} km\n")
                f.write(f"Max Elevation: {stats.get('elevation_stats', {}).get('max', 0):.0f} m\n")
                f.write(f"Min Elevation: {stats.get('elevation_stats', {}).get('min', 0):.0f} m\n")
                f.write(f"Average Elevation: {stats.get('elevation_stats', {}).get('mean', 0):.0f} m\n")
                f.write(f"Total Ascent: {stats.get('elevation_gain', 0):.0f} m\n")
                f.write(f"Total Descent: {stats.get('elevation_loss', 0):.0f} m\n\n")
            
            if watershed_data.get('streams'):
                streams = watershed_data['streams']
                f.write("STREAM NETWORK\n")
                f.write("-" * 30 + "\n")
                f.write(f"Total Length: {streams.get('total_length_km', 0):.2f} km\n")
                f.write(f"Number of Segments: {streams.get('total_segments', 0)}\n")
                
                if streams.get('drainage_orders'):
                    f.write("\nStream Order Distribution:\n")
                    for order, count in streams['drainage_orders'].items():
                        f.write(f"  Order {order}: {count} segments\n")
        
        return {'filename': filename, 'file_path': file_path}
    
    def _export_marine_geotiff(self, marine_data: Dict, temp_dir: str, base_filename: str) -> Dict:
        """Export marine data to GeoTIFF."""
        # This is a simplified implementation
        # In production, you would use GDAL/rasterio to create proper GeoTIFF
        
        filename = f"{base_filename}.tif"
        file_path = os.path.join(temp_dir, filename)
        
        # Create a placeholder file with metadata
        with open(file_path, 'w') as f:
            f.write("GeoTIFF Export - Marine Chart Data\n")
            f.write(f"Export Date: {datetime.now().isoformat()}\n")
            f.write(f"Chart Name: {marine_data.get('metadata', {}).get('name', 'Unknown')}\n")
            f.write(f"Bounds: {marine_data.get('bounds', {})}\n")
        
        return {'filename': filename, 'file_path': file_path}
    
    def _export_marine_image(self, marine_data: Dict, temp_dir: str, base_filename: str, format: str) -> Dict:
        """Export marine chart as image."""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import numpy as np
            
            filename = f"{base_filename}.{format}"
            file_path = os.path.join(temp_dir, filename)
            
            # Create a simple image representation
            width, height = 800, 600
            image = Image.new('RGB', (width, height), color='white')
            draw = ImageDraw.Draw(image)
            
            # Draw title
            title = marine_data.get('metadata', {}).get('name', 'Marine Chart')
            # Note: In production, you would need to handle fonts properly
            draw.text((width//2, 30), title, fill='black', anchor='mm')
            
            # Draw bounds info
            bounds = marine_data.get('bounds', {})
            bounds_text = f"Bounds: N{bounds.get('north', 0):.4f} S{bounds.get('south', 0):.4f} " \
                         f"E{bounds.get('east', 0):.4f} W{bounds.get('west', 0):.4f}"
            draw.text((width//2, 60), bounds_text, fill='blue', anchor='mm')
            
            # Draw soundings count
            if marine_data.get('soundings'):
                soundings_text = f"Soundings: {len(marine_data['soundings'])}"
                draw.text((width//2, 90), soundings_text, fill='green', anchor='mm')
            
            # Save image
            image.save(file_path, format.upper())
            
            return {'filename': filename, 'file_path': file_path}
            
        except ImportError:
            # Fallback to text export
            return self._export_marine_text(marine_data, temp_dir, base_filename)
    
    def _export_marine_pdf(self, marine_data: Dict, temp_dir: str, base_filename: str) -> Dict:
        """Export marine data to PDF."""
        # Similar to watershed PDF export
        return self._export_watershed_pdf(marine_data, temp_dir, base_filename)
    
    def _export_marine_text(self, marine_data: Dict, temp_dir: str, base_filename: str) -> Dict:
        """Export marine data as text file."""
        filename = f"{base_filename}.txt"
        file_path = os.path.join(temp_dir, filename)
        
        with open(file_path, 'w') as f:
            f.write("MARINE CHART DATA EXPORT\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            metadata = marine_data.get('metadata', {})
            f.write("CHART METADATA\n")
            f.write("-" * 30 + "\n")
            f.write(f"Name: {metadata.get('name', 'Unknown')}\n")
            f.write(f"Scale: 1:{metadata.get('scale', 'N/A')}\n")
            f.write(f"Projection: {metadata.get('projection', 'N/A')}\n\n")
            
            bounds = marine_data.get('bounds', {})
            f.write("CHART BOUNDS\n")
            f.write("-" * 30 + "\n")
            f.write(f"North: {bounds.get('north', 0):.6f}°\n")
            f.write(f"South: {bounds.get('south', 0):.6f}°\n")
            f.write(f"East: {bounds.get('east', 0):.6f}°\n")
            f.write(f"West: {bounds.get('west', 0):.6f}°\n\n")
            
            if marine_data.get('soundings'):
                f.write(f"SOUNDINGS ({len(marine_data['soundings'])} total)\n")
                f.write("-" * 30 + "\n")
                for i, sounding in enumerate(marine_data['soundings'][:10]):  # First 10 only
                    f.write(f"{i+1}. Lat: {sounding.get('latitude', 0):.6f}, "
                           f"Lon: {sounding.get('longitude', 0):.6f}, "
                           f"Depth: {sounding.get('depth', 0)} {sounding.get('unit', 'm')}\n")
                
                if len(marine_data['soundings']) > 10:
                    f.write(f"... and {len(marine_data['soundings']) - 10} more soundings\n")
        
        return {'filename': filename, 'file_path': file_path}
    
    def _export_hecras_geojson(self, results: Dict, temp_dir: str, base_filename: str) -> Dict:
        """Export HEC-RAS results to GeoJSON."""
        features = []
        
        # Water surface elevations
        if results.get('water_surface_elevations'):
            for station, elevation in results['water_surface_elevations'].items():
                # Simplified - in production, you would have actual coordinates
                feature = {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [0, 0]  # Placeholder
                    },
                    'properties': {
                        'station': station,
                        'water_surface_elevation': elevation,
                        'type': 'wse'
                    }
                }
                features.append(feature)
        
        geojson = {
            'type': 'FeatureCollection',
            'features': features,
            'properties': {
                'export_date': datetime.now().isoformat(),
                'data_type': 'hecras_results',
                'model_type': results.get('model_type', 'unknown')
            }
        }
        
        filename = f"{base_filename}.geojson"
        file_path = os.path.join(temp_dir, filename)
        
        with open(file_path, 'w') as f:
            json.dump(geojson, f, indent=2)
        
        return {'filename': filename, 'file_path': file_path}
    
    def _export_hecras_csv(self, results: Dict, temp_dir: str, base_filename: str) -> Dict:
        """Export HEC-RAS results to CSV."""
        import csv
        
        filename = f"{base_filename}.csv"
        file_path = os.path.join(temp_dir, filename)
        
        with open(file_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow(['Station', 'Water_Surface_Elevation', 'Velocity', 'Froude_Number'])
            
            # Write data
            wse = results.get('water_surface_elevations', {})
            velocities = results.get('velocities', {})
            froude = results.get('froude_numbers', {})
            
            stations = set(list(wse.keys()) + list(velocities.keys()) + list(froude.keys()))
            
            for station in sorted(stations):
                writer.writerow([
                    station,
                    wse.get(station, ''),
                    velocities.get(station, ''),
                    froude.get(station, '')
                ])
        
        return {'filename': filename, 'file_path': file_path}
    
    def _export_hecras_pdf(self, results: Dict, temp_dir: str, base_filename: str) -> Dict:
        """Export HEC-RAS results to PDF."""
        return self._export_watershed_pdf(results, temp_dir, base_filename)
    
    def _export_hecras_excel(self, results: Dict, temp_dir: str, base_filename: str) -> Dict:
        """Export HEC-RAS results to Excel."""
        try:
            import pandas as pd
            
            # Create DataFrame from results
            data = []
            wse = results.get('water_surface_elevations', {})
            velocities = results.get('velocities', {})
            froude = results.get('froude_numbers', {})
            
            stations = set(list(wse.keys()) + list(velocities.keys()) + list(froude.keys()))
            
            for station in sorted(stations):
                data.append({
                    'Station': station,
                    'Water_Surface_Elevation': wse.get(station),
                    'Velocity': velocities.get(station),
                    'Froude_Number': froude.get(station)
                })
            
            df = pd.DataFrame(data)
            
            filename = f"{base_filename}.xlsx"
            file_path = os.path.join(temp_dir, filename)
            
            # Save to Excel
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='HEC-RAS Results', index=False)
                
                # Add summary sheet
                summary_data = {
                    'Metric': ['Total Stations', 'Average WSE', 'Max Velocity', 'Model Type'],
                    'Value': [
                        len(stations),
                        df['Water_Surface_Elevation'].mean() if not df.empty else 0,
                        df['Velocity'].max() if not df.empty else 0,
                        results.get('model_type', 'Unknown')
                    ]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            return {'filename': filename, 'file_path': file_path}
            
        except ImportError:
            # Fallback to CSV if pandas not available
            return self._export_hecras_csv(results, temp_dir, base_filename)
    
    def _add_metadata_file(self, data: Dict, main_file_path: str):
        """Add metadata file alongside main export."""
        metadata = {
            'export_date': datetime.now().isoformat(),
            'source': 'GeoSuite',
            'software_version': '2.0.0',
            'data_summary': self._generate_data_summary(data)
        }
        
        metadata_path = main_file_path + '.meta.json'
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _generate_data_summary(self, data: Dict) -> Dict:
        """Generate summary of data for metadata."""
        summary = {}
        
        if 'tracks' in data:
            summary['tracks'] = len(data['tracks'])
            summary['total_points'] = sum(
                len(segment.get('points', []))
                for track in data.get('tracks', [])
                for segment in track.get('segments', [])
            )
        
        if 'watershed' in data:
            summary['watershed_area_km2'] = data['watershed'].get('area_km2')
            summary['stream_segments'] = data.get('streams', {}).get('total_segments')
        
        if 'soundings' in data:
            summary['soundings_count'] = len(data['soundings'])
        
        return summary
    
    def _get_mime_type(self, format: str) -> str:
        """Get MIME type for format."""
        mime_types = {
            'gpx': 'application/gpx+xml',
            'kml': 'application/vnd.google-earth.kml+xml',
            'geojson': 'application/geo+json',
            'csv': 'text/csv',
            'shp': 'application/zip',  # Shapefiles are zipped
            'zip': 'application/zip',
            'pdf': 'application/pdf',
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'tif': 'image/tiff',
            'tiff': 'image/tiff',
            'geotiff': 'image/tiff',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'txt': 'text/plain',
            'json': 'application/json',
        }
        
        return mime_types.get(format.lower(), 'application/octet-stream')