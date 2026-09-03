import numpy as np
from scipy import ndimage
import whitebox
import pysheds
from typing import Dict, List, Tuple, Optional
import json
from dataclasses import dataclass
import tempfile
import os

try:
    import geospatial_cpp
    geospatial_cpp_available = True
except ImportError:
    geospatial_cpp_available = False

wbt = whitebox.WhiteboxTools()

@dataclass
class WatershedResult:
    watershed_id: str
    pour_point: Tuple[float, float]
    area_km2: float
    perimeter_km: float
    stream_network: Dict
    flow_accumulation: np.ndarray
    drainage_area: Dict
    subwatersheds: List[Dict]

class WatershedService:
    def __init__(self):
        self.wbt = wbt
        self.pysheds_grid = None
    
    def delineate_watershed(self, dem_path: str, pour_point: Tuple[float, float]) -> WatershedResult:
        """Delineate watershed from DEM"""
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        
        try:
            # 1. Fill sinks in DEM
            filled_dem = os.path.join(temp_dir, "filled_dem.tif")
            self.wbt.fill_depressions(
                dem_path,
                filled_dem
            )
            
            # 2. Calculate flow direction
            flow_dir = os.path.join(temp_dir, "flow_dir.tif")
            self.wbt.d8_pointer(
                filled_dem,
                flow_dir
            )
            
            # 3. Calculate flow accumulation
            flow_acc = os.path.join(temp_dir, "flow_acc.tif")
            self.wbt.d8_flow_accumulation(
                filled_dem,
                flow_acc
            )
            
            # 4. Extract streams
            streams = os.path.join(temp_dir, "streams.tif")
            self.wbt.extract_streams(
                flow_acc,
                streams,
                threshold=1000
            )
            
            # 5. Snap pour point
            snapped_pour_point = os.path.join(temp_dir, "snapped_pour.tif")
            self.wbt.snap_pour_points(
                pour_point[0], pour_point[1],  # x, y coordinates
                flow_acc,
                snapped_pour_point,
                snap_dist=100
            )
            
            # 6. Delineate watershed
            watershed = os.path.join(temp_dir, "watershed.tif")
            self.wbt.watershed(
                flow_dir,
                snapped_pour_point,
                watershed
            )
            
            # 7. Calculate watershed properties
            properties = self._calculate_watershed_properties(watershed, filled_dem)
            
            # 8. Extract stream network
            stream_network = self._extract_stream_network(streams, flow_dir)
            
            # 9. Calculate subwatersheds
            subwatersheds = self._calculate_subwatersheds(stream_network, watershed)
            
            # 10. Read results
            if geospatial_cpp_available:
                watershed_array = geospatial_cpp.read_raster_to_array(watershed)
                flow_acc_array = geospatial_cpp.read_raster_to_array(flow_acc)
            else:
                watershed_array = np.array([])
                flow_acc_array = np.array([])
            
            result = WatershedResult(
                watershed_id=f"ws_{hash(str(pour_point))}",
                pour_point=pour_point,
                area_km2=properties['area_km2'],
                perimeter_km=properties['perimeter_km'],
                stream_network=stream_network,
                flow_accumulation=flow_acc_array.tolist(),
                drainage_area=properties['drainage_area'],
                subwatersheds=subwatersheds
            )
            
            return result
            
        finally:
            # Cleanup temp files
            import shutil
            shutil.rmtree(temp_dir)
    
    def calculate_flow_accumulation(self, dem_path: str, output_path: Optional[str] = None) -> np.ndarray:
        """Calculate flow accumulation from DEM"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Fill sinks
            filled_dem = os.path.join(temp_dir, "filled_dem.tif")
            self.wbt.fill_depressions(dem_path, filled_dem)
            
            # Calculate flow accumulation
            flow_acc = os.path.join(temp_dir, "flow_acc.tif")
            self.wbt.d8_flow_accumulation(filled_dem, flow_acc)
            
            # Read result
            if geospatial_cpp_available:
                flow_acc_array = geospatial_cpp.read_raster_to_array(flow_acc)
            else:
                flow_acc_array = np.array([])
            
            # Save if output path provided
            if output_path:
                import shutil
                shutil.copy2(flow_acc, output_path)
            
            return flow_acc_array
            
        finally:
            import shutil
            shutil.rmtree(temp_dir)
    
    def extract_stream_network(self, dem_path: str, threshold: float = 1000) -> Dict:
        """Extract stream network from DEM"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Fill sinks
            filled_dem = os.path.join(temp_dir, "filled_dem.tif")
            self.wbt.fill_depressions(dem_path, filled_dem)
            
            # Calculate flow accumulation
            flow_acc = os.path.join(temp_dir, "flow_acc.tif")
            self.wbt.d8_flow_accumulation(filled_dem, flow_acc)
            
            # Extract streams
            streams = os.path.join(temp_dir, "streams.tif")
            self.wbt.extract_streams(flow_acc, streams, threshold=threshold)
            
            # Vectorize streams
            stream_vector = os.path.join(temp_dir, "streams.shp")
            self.wbt.raster_streams_to_vector(
                streams,
                filled_dem,
                stream_vector
            )
            
            # Read and process stream network
            stream_network = self._vector_to_geojson(stream_vector)
            
            return {
                "threshold": threshold,
                "stream_count": len(stream_network.get('features', [])),
                "network": stream_network,
                "total_length_km": self._calculate_stream_length(stream_network)
            }
            
        finally:
            import shutil
            shutil.rmtree(temp_dir)
    
    def calculate_flow_path(self, dem_path: str, start_point: Tuple[float, float]) -> Dict:
        """Calculate flow path from a point"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Fill sinks
            filled_dem = os.path.join(temp_dir, "filled_dem.tif")
            self.wbt.fill_depressions(dem_path, filled_dem)
            
            # Calculate flow direction
            flow_dir = os.path.join(temp_dir, "flow_dir.tif")
            self.wbt.d8_pointer(filled_dem, flow_dir)
            
            # Trace flow path
            flow_path = os.path.join(temp_dir, "flow_path.tif")
            self.wbt.trace_downslope_flowpath(
                flow_dir,
                start_point[0], start_point[1],
                flow_path
            )
            
            # Convert to vector
            path_vector = os.path.join(temp_dir, "flow_path.shp")
            self.wbt.raster_to_vector_lines(flow_path, path_vector)
            
            # Read flow path
            if geospatial_cpp_available:
                path_array = geospatial_cpp.read_raster_to_array(flow_path)
                profile = None # we don't need profile if we have get_geotransform
            else:
                path_array = np.array([])
            
            # Calculate path statistics
            path_coords = np.argwhere(path_array > 0)
            
            if len(path_coords) > 0 and geospatial_cpp_available:
                # Convert to lat/lon
                coords = []
                transform = geospatial_cpp.get_geotransform(flow_path)
                for coord in path_coords:
                    # GDAL pixel to latlon
                    x_col = coord[1]
                    y_row = coord[0]
                    lon = transform[0] + x_col * transform[1] + y_row * transform[2]
                    lat = transform[3] + x_col * transform[4] + y_row * transform[5]
                    coords.append([float(lon), float(lat)])
                
                # Calculate elevation profile
                elevations = self._extract_elevation_profile(coords, filled_dem)
                
                # Calculate slope
                slopes = self._calculate_slopes(coords, elevations)
                
                return {
                    "path_coordinates": coords,
                    "elevation_profile": elevations,
                    "slopes": slopes,
                    "length_km": self._calculate_path_length(coords),
                    "start_point": start_point,
                    "end_point": coords[-1] if coords else start_point,
                    "drop_elevation": elevations[0] - elevations[-1] if elevations else 0,
                    "average_slope": np.mean(slopes) if slopes else 0
                }
            
            return {"path_coordinates": [], "error": "No flow path found"}
            
        finally:
            import shutil
            shutil.rmtree(temp_dir)
    
    def _calculate_watershed_properties(self, watershed_path: str, dem_path: str) -> Dict:
        """Calculate watershed properties"""
        if geospatial_cpp_available:
            watershed = geospatial_cpp.read_raster_to_array(watershed_path)
            transform = geospatial_cpp.get_geotransform(watershed_path)
            dem = geospatial_cpp.read_raster_to_array(dem_path)
        else:
            watershed = np.array([])
            dem = np.array([])
            transform = [0]*6
        
        # Calculate area
        pixel_area = abs(transform[1] * transform[5])  # pixel width * pixel height
        watershed_pixels = np.sum(watershed > 0)
        area_m2 = watershed_pixels * pixel_area
        area_km2 = area_m2 / 1e6
        
        # Calculate perimeter
        from skimage import measure
        contours = measure.find_contours(watershed, 0.5)
        perimeter_pixels = sum([len(contour) for contour in contours])
        perimeter_m = perimeter_pixels * np.sqrt(pixel_area)
        perimeter_km = perimeter_m / 1000
        
        # Calculate elevation statistics
        watershed_elevations = dem[watershed > 0]
        
        # Calculate drainage area (simplified)
        drainage_area = {
            "total": area_km2,
            "main_channel_length": 0,  # Would need stream network
            "average_slope": 0,  # Would need more calculation
            "relief": float(np.max(watershed_elevations) - np.min(watershed_elevations))
        }
        
        return {
            "area_m2": area_m2,
            "area_km2": area_km2,
            "perimeter_m": perimeter_m,
            "perimeter_km": perimeter_km,
            "elevation_stats": {
                "min": float(np.min(watershed_elevations)),
                "max": float(np.max(watershed_elevations)),
                "mean": float(np.mean(watershed_elevations)),
                "std": float(np.std(watershed_elevations))
            },
            "drainage_area": drainage_area
        }
    
    def _extract_stream_network(self, streams_path: str, flow_dir_path: str) -> Dict:
        """Extract stream network from raster"""
        if geospatial_cpp_available:
            streams = geospatial_cpp.read_raster_to_array(streams_path)
            flow_dir = geospatial_cpp.read_raster_to_array(flow_dir_path)
            transform = geospatial_cpp.get_geotransform(flow_dir_path)
        else:
            streams = np.array([])
            flow_dir = np.array([])
            transform = [0]*6
        
        # Find stream pixels
        stream_coords = np.argwhere(streams > 0)
        
        # Group into segments
        segments = []
        visited = np.zeros_like(streams, dtype=bool)
        
        for coord in stream_coords:
            if not visited[coord[0], coord[1]]:
                segment = self._trace_stream_segment(
                    coord, streams, flow_dir, visited
                )
                if segment:
                    # Convert to coordinates
                    coords = []
                    for pixel in segment:
                        x_col = pixel[1]
                        y_row = pixel[0]
                        lon = transform[0] + x_col * transform[1] + y_row * transform[2]
                        lat = transform[3] + x_col * transform[4] + y_row * transform[5]
                        coords.append([float(lon), float(lat)])
                    
                    segments.append({
                        "coordinates": coords,
                        "length": len(coords),
                        "order": self._calculate_strahler_order(segment, flow_dir)
                    })
        
        return {
            "segments": segments,
            "total_segments": len(segments),
            "total_length_pixels": len(stream_coords),
            "drainage_orders": self._calculate_drainage_orders(segments)
        }
    
    def _trace_stream_segment(self, start, streams, flow_dir, visited):
        """Trace a stream segment"""
        segment = []
        current = tuple(start)
        
        while (0 <= current[0] < streams.shape[0] and 
               0 <= current[1] < streams.shape[1] and
               streams[current] > 0 and not visited[current]):
            
            visited[current] = True
            segment.append(current)
            
            # Move downstream based on flow direction
            dir_code = flow_dir[current]
            if dir_code == 0:  # No flow direction
                break
            
            # D8 flow direction offsets
            d8_offsets = {
                1: (0, 1),    # East
                2: (1, 1),    # Southeast
                4: (1, 0),    # South
                8: (1, -1),   # Southwest
                16: (0, -1),  # West
                32: (-1, -1), # Northwest
                64: (-1, 0),  # North
                128: (-1, 1)  # Northeast
            }
            
            if dir_code in d8_offsets:
                offset = d8_offsets[dir_code]
                current = (current[0] + offset[0], current[1] + offset[1])
            else:
                break
        
        return segment
    
    def _calculate_strahler_order(self, segment, flow_dir):
        """Calculate Strahler stream order for a segment"""
        # Simplified calculation
        if len(segment) < 10:
            return 1
        elif len(segment) < 50:
            return 2
        elif len(segment) < 200:
            return 3
        else:
            return 4
    
    def _calculate_drainage_orders(self, segments):
        """Calculate distribution of drainage orders"""
        orders = {}
        for segment in segments:
            order = segment.get('order', 1)
            orders[order] = orders.get(order, 0) + 1
        
        return orders
    
    def _vector_to_geojson(self, shapefile_path: str) -> Dict:
        """Convert shapefile to GeoJSON"""
        if geospatial_cpp_available:
            geojson_str = geospatial_cpp.vector_to_geojson(shapefile_path)
            return json.loads(geojson_str)
        return {"type": "FeatureCollection", "features": []}
    
    def _calculate_stream_length(self, stream_network: Dict) -> float:
        """Calculate total stream length in kilometers"""
        from geopy.distance import geodesic
        
        total_length = 0
        
        for feature in stream_network.get('features', []):
            geometry = feature.get('geometry', {})
            if geometry.get('type') == 'LineString':
                coords = geometry.get('coordinates', [])
                for i in range(len(coords) - 1):
                    point1 = (coords[i][1], coords[i][0])  # lat, lon
                    point2 = (coords[i+1][1], coords[i+1][0])
                    total_length += geodesic(point1, point2).kilometers
        
        return total_length
    
    def _extract_elevation_profile(self, coords: List[List[float]], dem_path: str) -> List[float]:
        """Extract elevation profile along coordinates"""
        elevations = []
        
        if geospatial_cpp_available:
            import math
            for coord in coords:
                lon, lat = coord
                elevation = geospatial_cpp.sample_raster_at_point(dem_path, float(lon), float(lat))
                if not math.isnan(elevation):
                    elevations.append(float(elevation))
        
        return elevations
    
    def _calculate_slopes(self, coords: List[List[float]], elevations: List[float]) -> List[float]:
        """Calculate slopes between points"""
        slopes = []
        
        for i in range(len(coords) - 1):
            if i < len(elevations) - 1:
                # Calculate horizontal distance
                from geopy.distance import geodesic
                point1 = (coords[i][1], coords[i][0])
                point2 = (coords[i+1][1], coords[i+1][0])
                distance = geodesic(point1, point2).meters
                
                if distance > 0:
                    elevation_diff = elevations[i+1] - elevations[i]
                    slope = elevation_diff / distance
                    slopes.append(slope)
        
        return slopes
    
    def _calculate_path_length(self, coords: List[List[float]]) -> float:
        """Calculate total path length in kilometers"""
        from geopy.distance import geodesic
        
        total_length = 0
        
        for i in range(len(coords) - 1):
            point1 = (coords[i][1], coords[i][0])
            point2 = (coords[i+1][1], coords[i+1][0])
            total_length += geodesic(point1, point2).kilometers
        
        return total_length
    
    def _calculate_subwatersheds(self, stream_network: Dict, watershed_mask) -> List[Dict]:
        """Calculate subwatersheds from stream network"""
        subwatersheds = []
        
        # Simplified implementation
        # In production, use stream confluences to define subwatersheds
        
        return subwatersheds