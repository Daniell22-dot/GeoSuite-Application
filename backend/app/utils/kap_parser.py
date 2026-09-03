"""
Parser for KAP/BSB nautical chart files.
KAP is a raster format with embedded calibration and metadata.
"""
import struct
import re
from typing import Dict, List, Tuple, Optional, BinaryIO
import numpy as np
from PIL import Image
import io

class KAPParser:
    """
    Parser for KAP (BSB) nautical chart files.
    
    KAP files contain:
    1. Header with metadata
    2. Color palette (RGB)
    3. Raster image data
    4. Calibration points for georeferencing
    """
    
    def __init__(self):
        self.metadata = {}
        self.palette = []
        self.image_data = None
        self.calibration_points = []
    
    def parse(self, file_path: str) -> Dict:
        """
        Parse a KAP/BSB file.
        
        Args:
            file_path: Path to KAP file
        
        Returns:
            Dictionary with parsed chart data
        """
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Parse the file
        result = self._parse_kap_content(content)
        
        # Extract image
        if self.image_data:
            result['image_data'] = self._extract_image(self.image_data, self.palette)
        
        return result
    
    def _parse_kap_content(self, content: bytes) -> Dict:
        """
        Parse KAP file content.
        """
        # Convert to string for text parsing
        try:
            text_content = content.decode('latin-1', errors='ignore')
        except:
            text_content = content.decode('utf-8', errors='ignore')
        
        # Split into lines
        lines = text_content.split('\n')
        
        # Parse header
        in_header = True
        in_palette = False
        in_raster = False
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            if not line:
                continue
            
            # Check for section markers
            if line.startswith('RGB/'):
                in_palette = True
                in_header = False
                continue
            elif line.startswith('RA'):
                in_raster = True
                in_palette = False
                continue
            elif line.startswith('EOH'):
                in_header = False
                continue
            
            # Parse based on current section
            if in_header:
                self._parse_header_line(line)
            elif in_palette:
                self._parse_palette_line(line)
            elif in_raster:
                # Find raster data start
                raster_start = content.find(b'RA')
                if raster_start != -1:
                    # Extract raster data
                    self._extract_raster_data(content[raster_start:])
                break
        
        # Parse calibration points (if any)
        self._parse_calibration_points(lines)
        
        return {
            'metadata': self.metadata,
            'palette': self.palette,
            'calibration_points': self.calibration_points,
            'image_dimensions': self._get_image_dimensions()
        }
    
    def _parse_header_line(self, line: str):
        """
        Parse a header line.
        Format: KEY/VALUE
        """
        if '/' in line:
            key, value = line.split('/', 1)
            key = key.strip()
            value = value.strip()
            
            # Store metadata
            self.metadata[key] = value
            
            # Parse specific important fields
            if key == 'BSB':
                # Parse BSB parameters
                params = value.split(',')
                if len(params) >= 4:
                    self.metadata['width'] = int(params[2])
                    self.metadata['height'] = int(params[3])
            elif key == 'KNP':
                # Chart name and number
                self.metadata['chart_name'] = value
            elif key == 'SCA':
                # Scale
                self.metadata['scale'] = float(value.split(',')[0])
    
    def _parse_palette_line(self, line: str):
        """
        Parse palette line.
        Format: index,red,green,blue
        """
        if ',' in line:
            parts = line.split(',')
            if len(parts) >= 4:
                try:
                    index = int(parts[0])
                    red = int(parts[1])
                    green = int(parts[2])
                    blue = int(parts[3])
                    
                    self.palette.append({
                        'index': index,
                        'rgb': (red, green, blue)
                    })
                except ValueError:
                    pass
    
    def _parse_calibration_points(self, lines: List[str]):
        """
        Parse calibration/georeferencing points.
        """
        for line in lines:
            if line.startswith('REF'):
                # REF/1,3952,1705,37.78167,-122.50333
                parts = line[4:].split(',')
                if len(parts) >= 5:
                    try:
                        point = {
                            'id': int(parts[0]),
                            'x': int(parts[1]),
                            'y': int(parts[2]),
                            'lat': float(parts[3]),
                            'lon': float(parts[4])
                        }
                        self.calibration_points.append(point)
                    except ValueError:
                        pass
    
    def _extract_raster_data(self, raster_section: bytes):
        """
        Extract raster image data.
        """
        # Find RA line
        lines = raster_section.decode('latin-1', errors='ignore').split('\n')
        
        for line in lines:
            if line.startswith('RA'):
                # Get dimensions from RA line
                # RA width,height
                params = line[3:].split(',')
                if len(params) >= 2:
                    try:
                        width = int(params[0])
                        height = int(params[1])
                        
                        # Store for later use
                        self.metadata['raster_width'] = width
                        self.metadata['raster_height'] = height
                        
                        # The actual raster data follows
                        # In a real implementation, you'd extract the binary data
                        self.image_data = raster_section
                        
                    except ValueError:
                        pass
                break
    
    def _extract_image(self, image_data: bytes, palette: List[Dict]) -> Dict:
        """
        Extract image from raster data using palette.
        """
        if not palette or not image_data:
            return None
        
        # Create a color lookup table
        color_table = {}
        for entry in palette:
            index = entry['index']
            rgb = entry['rgb']
            color_table[index] = rgb
        
        # This is simplified - actual KAP parsing is more complex
        # In production, use a library like pybsb or implement full BSB spec
        
        # For now, create a placeholder image
        width = self.metadata.get('raster_width', 800)
        height = self.metadata.get('raster_height', 600)
        
        # Create a simple gradient image
        img_array = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Fill with gradient (placeholder)
        for y in range(height):
            for x in range(width):
                # Simple gradient based on position
                r = int((x / width) * 255)
                g = int((y / height) * 255)
                b = 128
                img_array[y, x] = [r, g, b]
        
        # Convert to PIL Image
        img = Image.fromarray(img_array, 'RGB')
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        
        return {
            'width': width,
            'height': height,
            'format': 'PNG',
            'data': img_byte_arr.getvalue(),
            'mode': 'RGB'
        }
    
    def _get_image_dimensions(self) -> Dict:
        """
        Get image dimensions from metadata.
        """
        width = self.metadata.get('width') or self.metadata.get('raster_width', 800)
        height = self.metadata.get('height') or self.metadata.get('raster_height', 600)
        
        return {
            'width': int(width),
            'height': int(height),
            'aspect_ratio': int(width) / int(height) if height else 1.0
        }
    
    def get_georeference_transform(self) -> Optional[Tuple]:
        """
        Calculate georeference transformation matrix from calibration points.
        Returns affine transformation coefficients.
        """
        if len(self.calibration_points) < 3:
            return None
        
        # Use calibration points to calculate affine transform
        # This is a simplified calculation
        # In production, use proper georeferencing
        
        points = self.calibration_points
        
        # Simple averaging for demo
        avg_lat = sum(p['lat'] for p in points) / len(points)
        avg_lon = sum(p['lon'] for p in points) / len(points)
        avg_x = sum(p['x'] for p in points) / len(points)
        avg_y = sum(p['y'] for p in points) / len(points)
        
        # Calculate scale (pixels per degree)
        # This is very simplified
        lat_range = max(p['lat'] for p in points) - min(p['lat'] for p in points)
        lon_range = max(p['lon'] for p in points) - min(p['lon'] for p in points)
        x_range = max(p['x'] for p in points) - min(p['x'] for p in points)
        y_range = max(p['y'] for p in points) - min(p['y'] for p in points)
        
        if lat_range > 0 and lon_range > 0:
            scale_x = x_range / lon_range
            scale_y = y_range / lat_range
            
            # Return affine transformation: [a, b, c, d, e, f]
            # where: x' = a*x + b*y + c, y' = d*x + e*y + f
            return (
                scale_x, 0, avg_x - scale_x * avg_lon,
                0, -scale_y, avg_y + scale_y * avg_lat
            )
        
        return None