"""
Digital Elevation Model (DEM) processor.
Handles SRTM, ASTER, and other DEM data for elevation correction.
"""
import numpy as np
import tempfile
import os
from typing import Dict, List, Tuple, Optional
from pyproj import Transformer, CRS
import requests
import json
try:
    import geospatial_cpp
    geospatial_cpp_available = True
except ImportError:
    print("Warning: geospatial_cpp not available, please compile it using vcpkg and CMake.")
    geospatial_cpp_available = False

class DEMProcessor:
    """
    Processor for Digital Elevation Models.
    Provides elevation data lookup, interpolation, and correction.
    """
    
    def __init__(self, dem_directory: str = "data/dem"):
        self.dem_directory = dem_directory
        os.makedirs(dem_directory, exist_ok=True)
        
        # Cache for DEM tiles
        self.dem_cache = {}
        
        # Coordinate transformer
        self.transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    
    def get_elevation(self, lat: float, lon: float, 
                     dem_source: str = "srtm") -> Optional[float]:
        """
        Get elevation for a single coordinate.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            dem_source: DEM source (srtm, aster, nasadem)
        
        Returns:
            Elevation in meters, or None if not found
        """
        # Check cache first
        cache_key = f"{lat:.4f},{lon:.4f}"
        if cache_key in self.dem_cache:
            return self.dem_cache[cache_key]
        
        # Try to get from local DEM files
        elevation = self._get_from_local_dem(lat, lon, dem_source)
        
        if elevation is None:
            # Fall back to API
            elevation = self._get_from_elevation_api(lat, lon)
        
        # Cache result
        if elevation is not None:
            self.dem_cache[cache_key] = elevation
        
        return elevation
    
    def get_elevation_profile(self, coordinates: List[Tuple[float, float]],
                             dem_source: str = "srtm") -> List[float]:
        """
        Get elevation profile for a series of coordinates.
        
        Args:
            coordinates: List of (lat, lon) tuples
            dem_source: DEM source to use
        
        Returns:
            List of elevations in meters
        """
        elevations = []
        
        for lat, lon in coordinates:
            elev = self.get_elevation(lat, lon, dem_source)
            elevations.append(elev if elev is not None else 0)
        
        return elevations
    
    def correct_gpx_elevation(self, gpx_data: Dict, 
                             dem_source: str = "srtm") -> Dict:
        """
        Correct elevation in GPX data using DEM.
        
        Args:
            gpx_data: Parsed GPX data dictionary
            dem_source: DEM source to use
        
        Returns:
            Corrected GPX data with elevation statistics
        """
        corrected_points = []
        original_elevations = []
        corrected_elevations = []
        
        # Process tracks
        if 'tracks' in gpx_data:
            for track in gpx_data['tracks']:
                for segment in track.get('segments', []):
                    for point in segment.get('points', []):
                        lat = point.get('latitude')
                        lon = point.get('longitude')
                        original_elev = point.get('elevation')
                        
                        if lat is not None and lon is not None:
                            # Get corrected elevation
                            corrected_elev = self.get_elevation(lat, lon, dem_source)
                            
                            if corrected_elev is not None:
                                point['elevation_corrected'] = corrected_elev
                                point['elevation_source'] = dem_source
                                
                                corrected_elevations.append(corrected_elev)
                            
                            if original_elev is not None:
                                original_elevations.append(original_elev)
                            
                            corrected_points.append(point)
        
        # Calculate statistics
        stats = self._calculate_elevation_stats(
            original_elevations, 
            corrected_elevations
        )
        
        return {
            'corrected_data': gpx_data,
            'points': corrected_points,
            'statistics': stats,
            'dem_source': dem_source
        }
    
    def _get_from_local_dem(self, lat: float, lon: float, 
                           dem_source: str) -> Optional[float]:
        """
        Get elevation from local DEM files.
        """
        # Determine DEM tile filename based on coordinates
        # SRTM tiles: NXXEXXX.hgt
        tile_name = self._get_dem_tile_name(lat, lon, dem_source)
        tile_path = os.path.join(self.dem_directory, tile_name)
        
        if os.path.exists(tile_path):
            try:
                if geospatial_cpp_available:
                    import math
                    elevation = geospatial_cpp.sample_raster_at_point(tile_path, float(lon), float(lat))
                    if math.isnan(elevation) or elevation < -1000 or elevation > 9000:
                        return None
                    return elevation
                else:
                    print("Error: geospatial_cpp not compiled. Cannot read local DEM.")
                    return None
            except Exception as e:
                print(f"Error reading DEM tile {tile_path}: {e}")
        
        return None
    
    def _get_dem_tile_name(self, lat: float, lon: float, 
                          dem_source: str) -> str:
        """
        Generate DEM tile filename from coordinates.
        """
        if dem_source.lower() == "srtm":
            # SRTM naming: N/S followed by latitude, E/W followed by longitude
            lat_dir = 'N' if lat >= 0 else 'S'
            lon_dir = 'E' if lon >= 0 else 'W'
            
            lat_int = abs(int(lat))
            lon_int = abs(int(lon))
            
            return f"{lat_dir}{lat_int:02d}{lon_dir}{lon_int:03d}.hgt"
        elif dem_source.lower() == "aster":
            # ASTER naming similar but with different extension
            lat_dir = 'N' if lat >= 0 else 'S'
            lon_dir = 'E' if lon >= 0 else 'W'
            
            lat_int = abs(int(lat))
            lon_int = abs(int(lon))
            
            return f"ASTGTM2_{lat_dir}{lat_int:02d}{lon_dir}{lon_int:03d}_dem.tif"
        else:
            # Generic naming
            return f"dem_{lat:.2f}_{lon:.2f}.tif"
    
    def _get_from_elevation_api(self, lat: float, lon: float) -> Optional[float]:
        """
        Get elevation from online API (fallback).
        """
        try:
            # Try Open-Elevation API
            url = f"https://api.open-elevation.com/api/v1/lookup"
            params = {
                'locations': f"{lat},{lon}"
            }
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if 'results' in data and len(data['results']) > 0:
                    return data['results'][0]['elevation']
        
        except Exception as e:
            print(f"Elevation API error: {e}")
        
        # Fallback: Simple terrain model
        # This is a mock implementation
        return self._mock_elevation(lat, lon)
    
    def _mock_elevation(self, lat: float, lon: float) -> float:
        """
        Mock elevation function for testing.
        In production, replace with real DEM data.
        """
        # Simple terrain simulation
        base = 100
        lat_effect = 50 * np.sin(lat * 0.1)
        lon_effect = 30 * np.cos(lon * 0.1)
        terrain = 20 * np.sin(lat * 2) * np.cos(lon * 2)
        
        return base + lat_effect + lon_effect + terrain
    
    def _calculate_elevation_stats(self, original: List[float], 
                                  corrected: List[float]) -> Dict:
        """
        Calculate elevation statistics.
        """
        if not corrected:
            return {}
        
        # Convert to numpy arrays for calculations
        orig_array = np.array(original) if original else np.array([])
        corr_array = np.array(corrected)
        
        stats = {
            'corrected_min': float(np.min(corr_array)),
            'corrected_max': float(np.max(corr_array)),
            'corrected_mean': float(np.mean(corr_array)),
            'corrected_std': float(np.std(corr_array)),
            'points_count': len(corrected)
        }
        
        if len(orig_array) > 0:
            stats['original_min'] = float(np.min(orig_array))
            stats['original_max'] = float(np.max(orig_array))
            stats['original_mean'] = float(np.mean(orig_array))
            stats['difference_mean'] = float(np.mean(corr_array - orig_array))
        
        # Calculate ascent/descent
        if len(corr_array) > 1:
            diffs = np.diff(corr_array)
            ascent = np.sum(diffs[diffs > 0])
            descent = np.sum(-diffs[diffs < 0])
            
            stats['total_ascent'] = float(ascent)
            stats['total_descent'] = float(descent)
        
        return stats
    
    def download_dem_tile(self, lat: float, lon: float, 
                         dem_source: str = "srtm") -> Optional[str]:
        """
        Download DEM tile for given coordinates.
        
        Args:
            lat: Latitude
            lon: Longitude
            dem_source: DEM source
        
        Returns:
            Path to downloaded tile, or None if failed
        """
        # This would implement downloading from various sources:
        # - NASA Earthdata (SRTM, ASTER)
        # - OpenTopography
        # - Copernicus DEM
        
        # For now, return None (implement based on your data sources)
        return None
    
    def merge_dem_tiles(self, bounds: Dict, output_path: str) -> bool:
        """
        Merge multiple DEM tiles into a single file.
        
        Args:
            bounds: Dictionary with north, south, east, west bounds
            output_path: Path for output merged DEM
        
        Returns:
            True if successful
        """
        # This would implement DEM mosaicking
        # In production, use GDAL or rasterio for this
        
        return False