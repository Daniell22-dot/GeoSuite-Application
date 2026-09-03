import gpxpy
import gpxpy.gpx
import json
from typing import Dict, List, Optional, Tuple
import numpy as np
from datetime import datetime
import tempfile
import os
import csv
from pyproj import Transformer, Geod
from app.services.elevation_service import ElevationService
from app.utils.dem_processor import DEMProcessor

try:
    from fastkml import kml as fastkml
    fastkml_available = True
except ImportError:
    fastkml_available = False

class GPSService:
    def __init__(self):
        self.elevation_service = ElevationService()
        self.dem_processor = DEMProcessor()
        self.geod = Geod(ellps="WGS84")
    
    def parse_gpx(self, file_path: str) -> Dict:
        """Parse GPX file with comprehensive data extraction"""
        with open(file_path, 'r') as gpx_file:
            gpx = gpxpy.parse(gpx_file)
        
        result = {
            "metadata": self._extract_metadata(gpx),
            "tracks": [],
            "waypoints": [],
            "routes": [],
            "statistics": {}
        }
        
        # Process tracks
        for track in gpx.tracks:
            track_data = self._process_track(track)
            result["tracks"].append(track_data)
        
        # Process waypoints
        for waypoint in gpx.waypoints:
            result["waypoints"].append({
                "name": waypoint.name or "",
                "description": waypoint.description or "",
                "latitude": waypoint.latitude,
                "longitude": waypoint.longitude,
                "elevation": waypoint.elevation,
                "time": waypoint.time.isoformat() if waypoint.time else None
            })
        
        # Process routes
        for route in gpx.routes:
            route_data = self._process_route(route)
            result["routes"].append(route_data)
        
        # Calculate overall statistics
        result["statistics"] = self._calculate_statistics(result)
        
        return result
    
    def parse_gps_file(self, file_path: str) -> Dict:
        """Dispatch GPS file parsing based on extension."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".gpx":
            return self.parse_gpx(file_path)
        elif ext == ".kml":
            return self._parse_kml(file_path)
        elif ext == ".csv":
            return self._parse_csv(file_path)
        elif ext in (".geojson", ".json"):
            return self._parse_geojson(file_path)
        else:
            raise ValueError(f"Unsupported GPS file format: {ext}")
    
    def _parse_kml(self, file_path: str) -> Dict:
        """Parse KML file and extract placemarks and tracks."""
        if not fastkml_available:
            raise ImportError("fastkml is required for KML parsing")
        
        with open(file_path, "rb") as f:
            doc = fastkml.KML()
            doc.from_string(f.read())
        
        features = []
        
        def collect_features(obj):
            if hasattr(obj, "features"):
                for feature in obj.features():
                    if hasattr(feature, "geometry") and feature.geometry:
                        geom = feature.geometry
                        props = {
                            "name": feature.name or "",
                            "description": getattr(feature, "description", "") or "",
                        }
                        if geom.geom_type == "Point":
                            coords = list(geom.coords)[0]
                            features.append({
                                "type": "Feature",
                                "geometry": {"type": "Point", "coordinates": [coords[0], coords[1], coords[2] if len(coords) > 2 else None]},
                                "properties": {**props, "feature_type": "placemark"},
                            })
                        elif geom.geom_type == "LineString":
                            coords = [list(c) for c in geom.coords]
                            features.append({
                                "type": "Feature",
                                "geometry": {"type": "LineString", "coordinates": coords},
                                "properties": {**props, "feature_type": "track"},
                            })
                    collect_features(feature)
        
        for root in doc.features():
            collect_features(root)
        
        waypoints = []
        tracks = []
        routes = []
        for feat in features:
            geom = feat.get("geometry", {})
            props = feat.get("properties", {})
            if geom.get("type") == "Point":
                coords = geom.get("coordinates", [0, 0])
                waypoints.append({
                    "name": props.get("name", ""),
                    "description": props.get("description", ""),
                    "longitude": coords[0],
                    "latitude": coords[1],
                    "elevation": coords[2] if len(coords) > 2 else None,
                })
            elif geom.get("type") == "LineString":
                coords = geom.get("coordinates", [])
                points = []
                for coord in coords:
                    points.append({
                        "longitude": coord[0],
                        "latitude": coord[1],
                        "elevation": coord[2] if len(coord) > 2 else None,
                    })
                tracks.append({
                    "name": props.get("name", "KML Track"),
                    "segments": [{"points": points, "points_count": len(points)}],
                })
        
        return {
            "metadata": {"name": os.path.basename(file_path), "source": "kml"},
            "tracks": tracks,
            "waypoints": waypoints,
            "routes": routes,
            "statistics": self._calculate_statistics({
                "tracks": tracks,
                "waypoints": waypoints,
                "routes": routes,
            }),
        }
    
    def _parse_csv(self, file_path: str) -> Dict:
        """Parse CSV spot-heights. Expects columns: easting/northing/elevation or lat/lon/elevation."""
        with open(file_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        if not rows:
            raise ValueError("CSV file is empty")
        
        headers = [h.strip().lower() for h in rows[0].keys()]
        waypoints = []
        for row in rows:
            vals = {k.strip().lower(): v for k, v in row.items()}
            lat = vals.get("lat") or vals.get("latitude")
            lon = vals.get("lon") or vals.get("long") or vals.get("longitude")
            easting = vals.get("easting") or vals.get("x")
            northing = vals.get("northing") or vals.get("y")
            elev = vals.get("elevation") or vals.get("altitude") or vals.get("z") or vals.get("height")
            if lat is not None and lon is not None:
                waypoints.append({
                    "name": vals.get("name", ""),
                    "description": vals.get("description", ""),
                    "latitude": float(lat),
                    "longitude": float(lon),
                    "elevation": float(elev) if elev is not None else None,
                })
            elif easting is not None and northing is not None:
                transformer = Transformer.from_crs("EPSG:4326", "EPSG:4326", always_xy=True)
                lon_f, lat_f = float(easting), float(northing)
                waypoints.append({
                    "name": vals.get("name", ""),
                    "description": vals.get("description", ""),
                    "latitude": lat_f,
                    "longitude": lon_f,
                    "elevation": float(elev) if elev is not None else None,
                })
            else:
                continue
        
        if not waypoints:
            raise ValueError("CSV does not contain recognizable coordinate columns (lat/lon or easting/northing)")
        
        return {
            "metadata": {"name": os.path.basename(file_path), "source": "csv"},
            "tracks": [],
            "waypoints": waypoints,
            "routes": [],
            "statistics": {
                "total_waypoints": len(waypoints),
                "total_tracks": 0,
                "total_routes": 0,
                "total_points": len(waypoints),
            },
        }
    
    def _parse_geojson(self, file_path: str) -> Dict:
        """Parse GeoJSON file and normalize to GPS structure."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        waypoints = []
        tracks = []
        routes = []
        
        def extract_point_coords(geom):
            if geom.get("type") == "Point":
                coords = geom.get("coordinates", [0, 0])
                return coords[0], coords[1], coords[2] if len(coords) > 2 else None
            return None
        
        features = data.get("features", [])
        for feat in features:
            geom = feat.get("geometry", {})
            props = feat.get("properties", {})
            gtype = geom.get("type")
            if gtype == "Point":
                lon, lat, elev = extract_point_coords(geom)
                waypoints.append({
                    "name": props.get("name", ""),
                    "description": props.get("description", ""),
                    "longitude": lon,
                    "latitude": lat,
                    "elevation": elev,
                })
            elif gtype == "LineString":
                coords = geom.get("coordinates", [])
                points = []
                for coord in coords:
                    points.append({
                        "longitude": coord[0],
                        "latitude": coord[1],
                        "elevation": coord[2] if len(coord) > 2 else None,
                    })
                tracks.append({
                    "name": props.get("name", "GeoJSON Track"),
                    "segments": [{"points": points, "points_count": len(points)}],
                })
        
        return {
            "metadata": {"name": os.path.basename(file_path), "source": "geojson"},
            "tracks": tracks,
            "waypoints": waypoints,
            "routes": routes,
            "statistics": self._calculate_statistics({
                "tracks": tracks,
                "waypoints": waypoints,
                "routes": routes,
            }),
        }
    
    def _process_track(self, track) -> Dict:
        """Process a single track with segments"""
        track_data = {
            "name": track.name or "Unnamed Track",
            "description": track.description or "",
            "segments": [],
            "length_2d": 0,
            "length_3d": 0,
            "elevation_gain": 0,
            "elevation_loss": 0
        }
        
        for segment in track.segments:
            segment_data = self._process_segment(segment)
            track_data["segments"].append(segment_data)
            
            # Accumulate track statistics
            track_data["length_2d"] += segment_data.get("length_2d", 0)
            track_data["length_3d"] += segment_data.get("length_3d", 0)
            track_data["elevation_gain"] += segment_data.get("elevation_gain", 0)
            track_data["elevation_loss"] += segment_data.get("elevation_loss", 0)
        
        return track_data
    
    def _process_segment(self, segment) -> Dict:
        """Process track segment with elevation correction"""
        points = []
        elevations = []
        times = []
        
        for point in segment.points:
            points.append({
                "latitude": point.latitude,
                "longitude": point.longitude,
                "elevation_raw": point.elevation,
                "time": point.time.isoformat() if point.time else None
            })
            elevations.append(point.elevation or 0)
            if point.time:
                times.append(point.time)
        
        # Calculate distances
        length_2d = self._calculate_distance_2d(points)
        length_3d = self._calculate_distance_3d(points)
        
        # Correct elevation
        corrected_data = self.elevation_service.correct_segment_elevation(points)
        
        # Calculate elevation statistics
        elevation_gain, elevation_loss = self._calculate_elevation_stats(
            corrected_data["corrected_points"]
        )
        
        return {
            "points": corrected_data["corrected_points"],
            "points_count": len(points),
            "length_2d": length_2d,
            "length_3d": length_3d,
            "elevation_gain": elevation_gain,
            "elevation_loss": elevation_loss,
            "elevation_min": corrected_data.get("elevation_min", 0),
            "elevation_max": corrected_data.get("elevation_max", 0),
            "duration": self._calculate_duration(times),
            "speed_stats": self._calculate_speed_stats(points, times)
        }
    
    def _process_route(self, route):
        """Process route data"""
        route_points = []
        for point in route.points:
            route_points.append({
                "latitude": point.latitude,
                "longitude": point.longitude,
                "elevation": point.elevation,
                "name": point.name or "",
                "description": point.description or ""
            })
        
        return {
            "name": route.name or "Unnamed Route",
            "points": route_points,
            "points_count": len(route_points)
        }
    
    def _calculate_distance_2d(self, points: List[Dict]) -> float:
        """Calculate 2D distance using geodesic"""
        if len(points) < 2:
            return 0
        
        total_distance = 0
        for i in range(len(points) - 1):
            lat1, lon1 = points[i]["latitude"], points[i]["longitude"]
            lat2, lon2 = points[i+1]["latitude"], points[i+1]["longitude"]
            
            _, _, distance = self.geod.inv(lon1, lat1, lon2, lat2)
            total_distance += abs(distance)
        
        return total_distance
    
    def _calculate_distance_3d(self, points: List[Dict]) -> float:
        """Calculate 3D distance considering elevation"""
        if len(points) < 2:
            return 0
        
        total_distance = 0
        for i in range(len(points) - 1):
            lat1, lon1, elev1 = points[i]["latitude"], points[i]["longitude"], points[i].get("elevation", 0)
            lat2, lon2, elev2 = points[i+1]["latitude"], points[i+1]["longitude"], points[i+1].get("elevation", 0)
            
            # 2D distance
            _, _, dist_2d = self.geod.inv(lon1, lat1, lon2, lat2)
            
            # 3D distance (Pythagorean theorem)
            dist_3d = np.sqrt(dist_2d**2 + (elev2 - elev1)**2)
            total_distance += abs(dist_3d)
        
        return total_distance
    
    def _calculate_elevation_stats(self, points: List[Dict]) -> Tuple[float, float]:
        """Calculate elevation gain and loss"""
        if len(points) < 2:
            return 0, 0
        
        gain = 0
        loss = 0
        
        for i in range(len(points) - 1):
            elev1 = points[i].get("elevation_corrected", points[i].get("elevation", 0))
            elev2 = points[i+1].get("elevation_corrected", points[i+1].get("elevation", 0))
            
            diff = elev2 - elev1
            if diff > 0:
                gain += diff
            else:
                loss += abs(diff)
        
        return gain, loss
    
    def _calculate_duration(self, times: List[datetime]) -> Optional[float]:
        """Calculate duration in seconds"""
        if len(times) >= 2:
            return (times[-1] - times[0]).total_seconds()
        return None
    
    def _calculate_speed_stats(self, points: List[Dict], times: List[datetime]) -> Dict:
        """Calculate speed statistics"""
        if len(points) < 2 or len(times) < 2:
            return {}
        
        speeds = []
        for i in range(len(points) - 1):
            if i < len(times) - 1:
                time_diff = (times[i+1] - times[i]).total_seconds()
                if time_diff > 0:
                    lat1, lon1 = points[i]["latitude"], points[i]["longitude"]
                    lat2, lon2 = points[i+1]["latitude"], points[i+1]["longitude"]
                    
                    _, _, distance = self.geod.inv(lon1, lat1, lon2, lat2)
                    speed = distance / time_diff
                    speeds.append(speed)
        
        if speeds:
            return {
                "avg": np.mean(speeds),
                "max": np.max(speeds),
                "min": np.min(speeds),
                "units": "m/s"
            }
        return {}
    
    def _extract_metadata(self, gpx) -> Dict:
        """Extract GPX metadata"""
        metadata = {
            "name": gpx.name or "Unnamed",
            "description": gpx.description or "",
            "author": gpx.author_name or "",
            "email": gpx.author_email or "",
            "link": gpx.link or "",
            "time": gpx.time.isoformat() if gpx.time else None,
            "keywords": gpx.keywords or "",
            "bounds": {}
        }
        
        if gpx.bounds:
            metadata["bounds"] = {
                "min_lat": gpx.bounds.min_latitude,
                "max_lat": gpx.bounds.max_latitude,
                "min_lon": gpx.bounds.min_longitude,
                "max_lon": gpx.bounds.max_longitude
            }
        
        return metadata
    
    def _calculate_statistics(self, data: Dict) -> Dict:
        """Calculate comprehensive statistics"""
        stats = {
            "total_tracks": len(data["tracks"]),
            "total_waypoints": len(data["waypoints"]),
            "total_routes": len(data["routes"]),
            "total_points": 0,
            "total_distance_2d": 0,
            "total_distance_3d": 0,
            "total_elevation_gain": 0,
            "total_elevation_loss": 0
        }
        
        for track in data["tracks"]:
            stats["total_distance_2d"] += track.get("length_2d", 0)
            stats["total_distance_3d"] += track.get("length_3d", 0)
            stats["total_elevation_gain"] += track.get("elevation_gain", 0)
            stats["total_elevation_loss"] += track.get("elevation_loss", 0)
            
            for segment in track.get("segments", []):
                stats["total_points"] += segment.get("points_count", 0)
        
        return stats
    
    def export_to_format(self, data: Dict, format: str) -> str:
        """Export to different formats"""
        if format.lower() == "geojson":
            return self._export_to_geojson(data)
        elif format.lower() == "kml":
            return self._export_to_kml(data)
        elif format.lower() == "csv":
            return self._export_to_csv(data)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _export_to_geojson(self, data: Dict) -> str:
        """Export to GeoJSON format"""
        features = []
        
        # Export tracks
        for track_idx, track in enumerate(data["tracks"]):
            for seg_idx, segment in enumerate(track["segments"]):
                coordinates = []
                for point in segment["points"]:
                    coordinates.append([
                        point["longitude"],
                        point["latitude"],
                        point.get("elevation_corrected", point.get("elevation", 0))
                    ])
                
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coordinates
                    },
                    "properties": {
                        "name": track["name"],
                        "segment": seg_idx,
                        "distance_2d": segment.get("length_2d", 0),
                        "distance_3d": segment.get("length_3d", 0),
                        "elevation_gain": segment.get("elevation_gain", 0),
                        "elevation_loss": segment.get("elevation_loss", 0)
                    }
                }
                features.append(feature)
        
        # Export waypoints
        for wp in data["waypoints"]:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [wp["longitude"], wp["latitude"], wp.get("elevation", 0)]
                },
                "properties": {
                    "name": wp["name"],
                    "description": wp["description"]
                }
            }
            features.append(feature)
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        return json.dumps(geojson, indent=2)
    
    def _export_to_kml(self, data: Dict) -> str:
        """Export to KML format"""
        kml_template = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{name}</name>
    <description>{description}</description>
    {content}
  </Document>
</kml>"""
        
        placemarks = []
        
        # Add tracks
        for track in data["tracks"]:
            for segment in track["segments"]:
                coords = []
                for point in segment["points"]:
                    elev = point.get("elevation_corrected", point.get("elevation", 0))
                    coords.append(f"{point['longitude']},{point['latitude']},{elev}")
                
                placemark = f"""
    <Placemark>
      <name>{track['name']}</name>
      <LineString>
        <extrude>1</extrude>
        <tessellate>1</tessellate>
        <altitudeMode>absolute</altitudeMode>
        <coordinates>
          {' '.join(coords)}
        </coordinates>
      </LineString>
    </Placemark>"""
                placemarks.append(placemark)
        
        content = "\n".join(placemarks)
        return kml_template.format(
            name=data["metadata"].get("name", "Exported Data"),
            description=data["metadata"].get("description", ""),
            content=content
        )
    
    def _export_to_csv(self, data: Dict) -> str:
        """Export to CSV format"""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(["type", "name", "latitude", "longitude", "elevation", "time", "distance_2d", "distance_3d"])
        
        # Write track points
        for track in data["tracks"]:
            for segment in track["segments"]:
                cumulative_2d = 0
                cumulative_3d = 0
                
                for i, point in enumerate(segment["points"]):
                    if i > 0:
                        # Calculate incremental distances
                        prev_point = segment["points"][i-1]
                        lat1, lon1 = prev_point["latitude"], prev_point["longitude"]
                        lat2, lon2 = point["latitude"], point["longitude"]
                        elev1 = prev_point.get("elevation_corrected", prev_point.get("elevation", 0))
                        elev2 = point.get("elevation_corrected", point.get("elevation", 0))
                        
                        _, _, dist_2d = self.geod.inv(lon1, lat1, lon2, lat2)
                        dist_3d = np.sqrt(dist_2d**2 + (elev2 - elev1)**2)
                        
                        cumulative_2d += abs(dist_2d)
                        cumulative_3d += abs(dist_3d)
                    
                    writer.writerow([
                        "track_point",
                        track["name"],
                        point["latitude"],
                        point["longitude"],
                        point.get("elevation_corrected", point.get("elevation", 0)),
                        point.get("time", ""),
                        cumulative_2d,
                        cumulative_3d
                    ])
        
        return output.getvalue()