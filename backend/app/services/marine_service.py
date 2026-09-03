import os
import struct
from typing import Dict, List, Optional, Tuple
import numpy as np
from PIL import Image, ImageDraw
import json
import zipfile
from io import BytesIO
from dataclasses import dataclass
from app.utils.kap_parser import KAPParser

@dataclass
class ChartMetadata:
    name: str
    scale: float
    projection: str
    bounds: Dict
    sounding_units: str
    depth_units: str
    georef: Dict
    created: str
    updated: str

class MarineChartService:
    def __init__(self):
        self.kap_parser = KAPParser()
        self.supported_formats = ['.kap', '.bsb', '.dwg', '.dxf', '.shp']
    
    def process_kap_file(self, file_path: str) -> Dict:
        """Process KAP/BSB nautical chart file"""
        try:
            # Parse KAP file
            chart_data = self.kap_parser.parse(file_path)
            
            # Extract metadata
            metadata = self._extract_kap_metadata(chart_data)
            
            # Process image data
            image_data = self._process_chart_image(chart_data)
            
            # Extract soundings and contours
            soundings = self._extract_soundings(chart_data)
            contours = self._extract_depth_contours(chart_data)
            
            # Generate georeferenced tiles
            tiles = self._generate_tiles(image_data, metadata)
            
            return {
                "success": True,
                "metadata": metadata.__dict__,
                "image_info": image_data,
                "soundings": soundings,
                "contours": contours,
                "tiles": tiles,
                "bounds": metadata.bounds,
                "format": "KAP/BSB"
            }
            
        except Exception as e:
            raise Exception(f"Failed to process KAP file: {str(e)}")
    
    def process_dwg_file(self, file_path: str) -> Dict:
        """Process DWG/DXF CAD files for nautical charts"""
        try:
            import ezdxf
            
            # Load DWG/DXF file
            doc = ezdxf.readfile(file_path)
            
            # Extract entities
            layers = {}
            for layer in doc.layers:
                layer_name = layer.dxf.name
                entities = []
                
                # Get all entities in this layer
                for entity in doc.modelspace().query(f'*[layer=="{layer_name}"]'):
                    entity_data = self._extract_dxf_entity(entity)
                    if entity_data:
                        entities.append(entity_data)
                
                if entities:
                    layers[layer_name] = entities
            
            # Extract chart information
            metadata = self._extract_dwg_metadata(doc)
            
            # Convert to GeoJSON
            geojson = self._convert_to_geojson(layers)
            
            return {
                "success": True,
                "metadata": metadata,
                "layers": list(layers.keys()),
                "entity_counts": {layer: len(entities) for layer, entities in layers.items()},
                "geojson": geojson,
                "format": "DWG/DXF"
            }
            
        except Exception as e:
            raise Exception(f"Failed to process DWG file: {str(e)}")
    
    def _extract_kap_metadata(self, chart_data: Dict) -> ChartMetadata:
        """Extract metadata from KAP chart"""
        return ChartMetadata(
            name=chart_data.get('NA', 'Unknown Chart'),
            scale=float(chart_data.get('SC', 0)),
            projection=chart_data.get('PR', 'MERCATOR'),
            bounds={
                "north": float(chart_data.get('NO', 0)),
                "south": float(chart_data.get('SO', 0)),
                "east": float(chart_data.get('EA', 0)),
                "west": float(chart_data.get('WE', 0))
            },
            sounding_units=chart_data.get('UN', 'METERS'),
            depth_units=chart_data.get('DU', 'METERS'),
            georef=chart_data.get('GEOREF', {}),
            created=chart_data.get('DT', ''),
            updated=chart_data.get('ED', '')
        )
    
    def _process_chart_image(self, chart_data: Dict) -> Dict:
        """Process chart image data"""
        image_info = {
            "width": chart_data.get('RA', {}).get('width', 0),
            "height": chart_data.get('RA', {}).get('height', 0),
            "color_mode": chart_data.get('RA', {}).get('color_mode', 'RGB'),
            "compression": chart_data.get('RA', {}).get('compression', 'NONE'),
            "palette": chart_data.get('RGB', [])
        }
        
        # Generate thumbnail
        if 'image_data' in chart_data:
            image = Image.frombytes(
                'RGB' if image_info['color_mode'] == 'RGB' else 'P',
                (image_info['width'], image_info['height']),
                chart_data['image_data']
            )
            
            # Create thumbnail
            thumbnail = image.copy()
            thumbnail.thumbnail((400, 400))
            
            # Save to bytes
            img_byte_arr = BytesIO()
            thumbnail.save(img_byte_arr, format='PNG')
            image_info['thumbnail'] = img_byte_arr.getvalue()
        
        return image_info
    
    def _extract_soundings(self, chart_data: Dict) -> List[Dict]:
        """Extract sounding data from chart"""
        soundings = []
        
        if 'SOUNDINGS' in chart_data:
            for sounding in chart_data['SOUNDINGS']:
                soundings.append({
                    "latitude": sounding.get('lat', 0),
                    "longitude": sounding.get('lon', 0),
                    "depth": sounding.get('depth', 0),
                    "unit": sounding.get('unit', 'METERS'),
                    "quality": sounding.get('quality', 'UNKNOWN')
                })
        
        return soundings
    
    def _extract_depth_contours(self, chart_data: Dict) -> List[Dict]:
        """Extract depth contours from chart"""
        contours = []
        
        if 'CONTOURS' in chart_data:
            for contour in chart_data['CONTOURS']:
                points = contour.get('points', [])
                if points:
                    contours.append({
                        "depth": contour.get('depth', 0),
                        "unit": contour.get('unit', 'METERS'),
                        "points": points,
                        "type": contour.get('type', 'DEPTH')
                    })
        
        return contours
    
    def _generate_tiles(self, image_data: Dict, metadata: ChartMetadata) -> Dict:
        """Generate map tiles from chart"""
        tiles = {
            "tile_size": 256,
            "min_zoom": 10,
            "max_zoom": 18,
            "bounds": metadata.bounds,
            "tile_urls": []
        }
        
        # Calculate tile coordinates
        bounds = metadata.bounds
        
        # Simple tile calculation (for production, use proper tile generation)
        center_lat = (bounds['north'] + bounds['south']) / 2
        center_lon = (bounds['east'] + bounds['west']) / 2
        
        # Generate sample tile URLs
        for zoom in range(tiles['min_zoom'], tiles['max_zoom'] + 1):
            tiles['tile_urls'].append({
                "zoom": zoom,
                "url_template": f"/api/v1/marine/tiles/{zoom}/{{x}}/{{y}}.png"
            })
        
        return tiles
    
    def _extract_dxf_entity(self, entity) -> Optional[Dict]:
        """Extract data from DXF entity"""
        try:
            entity_type = entity.dxftype()
            
            if entity_type == 'LINE':
                return {
                    "type": "LineString",
                    "coordinates": [
                        [entity.dxf.start.x, entity.dxf.start.y],
                        [entity.dxf.end.x, entity.dxf.end.y]
                    ],
                    "layer": entity.dxf.layer,
                    "color": entity.dxf.color
                }
            elif entity_type == 'CIRCLE':
                return {
                    "type": "Circle",
                    "center": [entity.dxf.center.x, entity.dxf.center.y],
                    "radius": entity.dxf.radius,
                    "layer": entity.dxf.layer,
                    "color": entity.dxf.color
                }
            elif entity_type == 'POLYLINE' or entity_type == 'LWPOLYLINE':
                points = []
                for vertex in entity.vertices():
                    points.append([vertex.dxf.location.x, vertex.dxf.location.y])
                
                return {
                    "type": "Polygon" if entity.is_closed else "LineString",
                    "coordinates": points,
                    "layer": entity.dxf.layer,
                    "color": entity.dxf.color
                }
            elif entity_type == 'TEXT':
                return {
                    "type": "Text",
                    "position": [entity.dxf.insert.x, entity.dxf.insert.y],
                    "text": entity.dxf.text,
                    "layer": entity.dxf.layer,
                    "color": entity.dxf.color,
                    "height": entity.dxf.height
                }
            
            return None
            
        except Exception as e:
            print(f"Error extracting entity: {e}")
            return None
    
    def _extract_dwg_metadata(self, doc) -> Dict:
        """Extract metadata from DWG file"""
        return {
            "version": doc.dxfversion,
            "layer_count": len(doc.layers),
            "entity_count": len(doc.modelspace()),
            "units": doc.header.get('$INSUNITS', 0),
            "author": doc.header.get('$AUTHOR', ''),
            "comments": doc.header.get('$COMMENTS', ''),
            "created": doc.header.get('$TDCREATE', ''),
            "modified": doc.header.get('$TDUPDATE', '')
        }
    
    def _convert_to_geojson(self, layers: Dict) -> Dict:
        """Convert DWG layers to GeoJSON"""
        features = []
        
        for layer_name, entities in layers.items():
            for entity in entities:
                if entity['type'] in ['LineString', 'Polygon']:
                    feature = {
                        "type": "Feature",
                        "geometry": {
                            "type": entity['type'],
                            "coordinates": entity['coordinates']
                        },
                        "properties": {
                            "layer": layer_name,
                            "color": entity.get('color', 0),
                            "entity_type": entity['type']
                        }
                    }
                    features.append(feature)
        
        return {
            "type": "FeatureCollection",
            "features": features
        }
    
    def merge_charts(self, chart_files: List[str], output_format: str = "geotiff") -> str:
        """Merge multiple charts into one"""
        merged_data = {
            "charts": [],
            "combined_bounds": {
                "north": -90,
                "south": 90,
                "east": -180,
                "west": 180
            }
        }
        
        for file_path in chart_files:
            if file_path.lower().endswith('.kap'):
                chart_data = self.process_kap_file(file_path)
            elif file_path.lower().endswith(('.dwg', '.dxf')):
                chart_data = self.process_dwg_file(file_path)
            else:
                continue
            
            merged_data["charts"].append(chart_data)
            
            # Update combined bounds
            bounds = chart_data.get('bounds', {})
            merged_data["combined_bounds"]["north"] = max(
                merged_data["combined_bounds"]["north"],
                bounds.get('north', -90)
            )
            merged_data["combined_bounds"]["south"] = min(
                merged_data["combined_bounds"]["south"],
                bounds.get('south', 90)
            )
            merged_data["combined_bounds"]["east"] = max(
                merged_data["combined_bounds"]["east"],
                bounds.get('east', -180)
            )
            merged_data["combined_bounds"]["west"] = min(
                merged_data["combined_bounds"]["west"],
                bounds.get('west', 180)
            )
        
        # Save merged data
        output_path = f"data/output/merged_charts_{output_format}.{output_format}"
        
        if output_format == "geotiff":
            self._save_as_geotiff(merged_data, output_path)
        elif output_format == "geojson":
            self._save_as_geojson(merged_data, output_path)
        
        return output_path
    
    def _save_as_geotiff(self, data: Dict, output_path: str):
        """Save merged charts as GeoTIFF"""
        from osgeo import gdal, osr
        
        # Create GeoTIFF
        bounds = data["combined_bounds"]
        
        # Calculate dimensions
        width = 4096
        height = 4096
        
        # Create raster
        driver = gdal.GetDriverByName('GTiff')
        dataset = driver.Create(output_path, width, height, 3, gdal.GDT_Byte)
        
        # Set geotransform
        pixel_width = (bounds["east"] - bounds["west"]) / width
        pixel_height = (bounds["north"] - bounds["south"]) / height
        
        geotransform = (
            bounds["west"], pixel_width, 0,
            bounds["north"], 0, -pixel_height
        )
        dataset.SetGeoTransform(geotransform)
        
        # Set projection
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)  # WGS84
        dataset.SetProjection(srs.ExportToWkt())
        
        # Fill with data (simplified - in reality, you'd composite the charts)
        for i in range(3):
            band = dataset.GetRasterBand(i + 1)
            band.Fill(255)
        
        dataset.FlushCache()
        dataset = None
        
    def _save_as_geojson(self, data: Dict, output_path: str):
        """Save merged charts as GeoJSON"""
        import json
        
        geojson = {
            "type": "FeatureCollection",
            "features": []
        }
        
        for chart in data["charts"]:
            if "geojson" in chart:
                geojson["features"].extend(chart["geojson"]["features"])
        
        with open(output_path, 'w') as f:
            json.dump(geojson, f, indent=2)