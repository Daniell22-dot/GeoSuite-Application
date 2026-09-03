"""
Elevation service — thin wrapper around DEMProcessor.
Provides elevation correction, profiling, and batch lookups.
"""
from typing import Dict, List, Optional
from app.utils.dem_processor import DEMProcessor


class ElevationService:
    def __init__(self):
        self.dem_processor = DEMProcessor()

    def get_elevation(self, lat: float, lon: float,
                      dem_source: str = "srtm") -> Optional[float]:
        return self.dem_processor.get_elevation(lat, lon, dem_source)

    def get_elevations(self, coordinates: List[Dict],
                       dem_source: str = "srtm") -> List[float]:
        """Get elevations for a list of {latitude, longitude} dicts."""
        results = []
        for coord in coordinates:
            elev = self.dem_processor.get_elevation(
                coord['latitude'], coord['longitude'], dem_source
            )
            results.append(elev if elev is not None else 0.0)
        return results

    def correct_gps_elevation(self, gpx_data: Dict,
                              dem_source: str = "srtm") -> Dict:
        return self.dem_processor.correct_gpx_elevation(gpx_data, dem_source)

    def get_elevation_profile(self, coordinates: List[Dict],
                              dem_source: str = "srtm") -> Dict:
        """Return elevation profile with statistics for a list of coordinate dicts."""
        lat_lon_pairs = [(c['latitude'], c['longitude']) for c in coordinates]
        elevations = self.dem_processor.get_elevation_profile(
            lat_lon_pairs, dem_source
        )

        import numpy as np
        elev_array = np.array(elevations)

        stats = {
            'min': float(np.min(elev_array)) if len(elev_array) > 0 else 0,
            'max': float(np.max(elev_array)) if len(elev_array) > 0 else 0,
            'mean': float(np.mean(elev_array)) if len(elev_array) > 0 else 0,
            'total_points': len(elevations),
        }

        if len(elev_array) > 1:
            diffs = np.diff(elev_array)
            stats['total_ascent'] = float(np.sum(diffs[diffs > 0]))
            stats['total_descent'] = float(np.sum(-diffs[diffs < 0]))
        else:
            stats['total_ascent'] = 0.0
            stats['total_descent'] = 0.0

        profile = [
            {
                'latitude': coord['latitude'],
                'longitude': coord['longitude'],
                'elevation': elev,
            }
            for coord, elev in zip(coordinates, elevations)
        ]

        return {'profile': profile, 'statistics': stats, 'dem_source': dem_source}

    def process_gpx_elevations(self, gpx_data: Dict,
                               dem_source: str = "srtm") -> Dict:
        return self.dem_processor.correct_gpx_elevation(gpx_data, dem_source)
