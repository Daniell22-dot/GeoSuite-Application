"""
GPS data processing routes.
Handles GPX file uploads, elevation correction, and GPS data analysis.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import tempfile
import os
import uuid

from app.services.gps_service import GPSService
from app.services.elevation_service import ElevationService
from app.services.file_converter import FileConverterService
from app.database import get_db
from app.models.geospatial import User, GPSTrack, GPSPoint
from app.services.auth_service import auth_service

router = APIRouter()
gps_service = GPSService()
elevation_service = ElevationService()
file_converter = FileConverterService()

@router.post("/upload")
async def upload_gps_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Upload and parse a GPS file (GPX, KML, GeoJSON, CSV).
    
    Supported formats:
    - GPX (.gpx): GPS Exchange Format
    - KML (.kml): Google Earth format
    - GeoJSON (.geojson, .json): Web mapping format
    - CSV (.csv): Comma-separated values with lat/lon or easting/northing columns
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    supported_extensions = ['.gpx', '.kml', '.geojson', '.json', '.csv']
    
    if file_ext not in supported_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported: {', '.join(supported_extensions)}"
        )
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        result = gps_service.parse_gps_file(temp_path)
        
        track = GPSTrack(
            id=uuid.uuid4(),
            user_id=user.id,
            name=result.get('metadata', {}).get('name', file.filename),
            description=result.get('metadata', {}).get('description', ''),
            file_name=file.filename,
            file_size=len(content),
            file_type=file_ext[1:],
            points_count=result.get('statistics', {}).get('total_points', 0),
            distance_2d=result.get('statistics', {}).get('total_distance_2d', 0),
            distance_3d=result.get('statistics', {}).get('total_distance_3d', 0),
            elevation_gain=result.get('statistics', {}).get('total_elevation_gain', 0),
            elevation_loss=result.get('statistics', {}).get('total_elevation_loss', 0),
            duration_seconds=result.get('statistics', {}).get('duration', 0),
            start_time=result.get('metadata', {}).get('start_time'),
            end_time=result.get('metadata', {}).get('end_time'),
            bounds=result.get('metadata', {}).get('bounds'),
            metadata=result.get('metadata', {}),
        )
        
        db.add(track)
        db.flush()
        
        point_number = 0
        for track_data in result.get('tracks', []):
            for segment in track_data.get('segments', []):
                for pt in segment.get('points', []):
                    point_number += 1
                    db.add(GPSPoint(
                        track_id=track.id,
                        point_number=point_number,
                        latitude=pt['latitude'],
                        longitude=pt['longitude'],
                        elevation_raw=pt.get('elevation_raw', pt.get('elevation')),
                        elevation_corrected=pt.get('elevation_corrected', pt.get('elevation')),
                        time=datetime.fromisoformat(pt['time']) if pt.get('time') else None,
                    ))
        
        for wp in result.get('waypoints', []):
            point_number += 1
            db.add(GPSPoint(
                track_id=track.id,
                point_number=point_number,
                latitude=wp['latitude'],
                longitude=wp['longitude'],
                elevation_raw=wp.get('elevation'),
            ))
        
        db.commit()
        db.refresh(track)
        
        os.unlink(temp_path)
        
        if background_tasks and result.get('statistics', {}).get('has_elevation', False):
            background_tasks.add_task(
                correct_track_elevation_async,
                track_id=str(track.id),
                dem_source='srtm'
            )
        
        return {
            "success": True,
            "message": "GPS file uploaded successfully",
            "track_id": str(track.id),
            "data": result,
            "statistics": result.get('statistics', {})
        }
        
    except Exception as e:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise HTTPException(status_code=500, detail=f"Error processing GPS file: {str(e)}")

@router.post("/correct-elevation")
async def correct_elevation(
    gpx_data: dict,
    dem_source: str = "srtm",
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Correct elevation data in GPS track using DEM.
    
    Args:
        gpx_data: GPS track data
        dem_source: DEM source (srtm, aster, lidar, local)
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        result = elevation_service.correct_gps_elevation(gpx_data, dem_source)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Elevation correction failed: {str(e)}")

@router.post("/convert")
async def convert_gps_format(
    gpx_data: dict,
    target_format: str,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Convert GPS data to other formats.
    
    Supported target formats:
    - gpx: GPS Exchange Format
    - kml: Google Earth KML
    - geojson: GeoJSON
    - csv: CSV with coordinates
    - shp: Shapefile (zipped)
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        result = file_converter.convert_gps_data(gpx_data, target_format)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")

@router.post("/elevation-profile")
async def get_elevation_profile(
    coordinates: List[dict],
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Get elevation profile for a set of coordinates.
    
    coordinates: List of {latitude, longitude} points
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        profile = elevation_service.get_elevation_profile(coordinates)
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get elevation profile: {str(e)}")

@router.post("/batch-process")
async def batch_process_gps(
    files: List[UploadFile] = File(...),
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Batch process multiple GPS files.
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files per batch")
    
    results = []
    errors = []
    
    for file in files:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.gpx') as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_path = temp_file.name
            
            result = gps_service.parse_gps_file(temp_path)
            results.append({
                "filename": file.filename,
                "success": True,
                "data": result
            })
            
            os.unlink(temp_path)
            
        except Exception as e:
            errors.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    return {
        "total_files": len(files),
        "processed": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors
    }

@router.get("/tracks")
async def get_user_tracks(
    limit: int = 50,
    offset: int = 0,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Get user's GPS tracks.
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    tracks = db.query(GPSTrack).filter(
        GPSTrack.user_id == user.id
    ).order_by(
        GPSTrack.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    return {
        "tracks": [
            {
                "id": str(track.id),
                "name": track.name,
                "description": track.description,
                "file_name": track.file_name,
                "points_count": track.points_count,
                "distance_2d": track.distance_2d,
                "distance_3d": track.distance_3d,
                "elevation_gain": track.elevation_gain,
                "created_at": track.created_at.isoformat() if track.created_at else None
            }
            for track in tracks
        ],
        "total": db.query(GPSTrack).filter(GPSTrack.user_id == user.id).count()
    }

@router.get("/tracks/{track_id}")
async def get_track_details(
    track_id: str,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific track.
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        track_uuid = uuid.UUID(track_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid track ID format")
    
    track = db.query(GPSTrack).filter(
        GPSTrack.id == track_uuid,
        GPSTrack.user_id == user.id
    ).first()
    
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    
    # Get track points
    points = track.points
    
    return {
        "track": {
            "id": str(track.id),
            "name": track.name,
            "description": track.description,
            "file_name": track.file_name,
            "file_size": track.file_size,
            "file_type": track.file_type,
            "points_count": track.points_count,
            "distance_2d": track.distance_2d,
            "distance_3d": track.distance_3d,
            "elevation_gain": track.elevation_gain,
            "elevation_loss": track.elevation_loss,
            "duration_seconds": track.duration_seconds,
            "start_time": track.start_time.isoformat() if track.start_time else None,
            "end_time": track.end_time.isoformat() if track.end_time else None,
            "bounds": track.bounds,
            "metadata": track.metadata,
            "created_at": track.created_at.isoformat() if track.created_at else None
        },
        "points": [
            {
                "latitude": point.latitude,
                "longitude": point.longitude,
                "elevation_raw": point.elevation_raw,
                "elevation_corrected": point.elevation_corrected,
                "time": point.time.isoformat() if point.time else None,
                "speed": point.speed,
                "accuracy": point.accuracy,
                "heart_rate": point.heart_rate,
                "cadence": point.cadence
            }
            for point in points
        ]
    }

@router.delete("/tracks/{track_id}")
async def delete_track(
    track_id: str,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Delete a GPS track.
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        track_uuid = uuid.UUID(track_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid track ID format")
    
    track = db.query(GPSTrack).filter(
        GPSTrack.id == track_uuid,
        GPSTrack.user_id == user.id
    ).first()
    
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    
    db.delete(track)
    db.commit()
    
    return {"success": True, "message": "Track deleted successfully"}

@router.post("/analyze")
async def analyze_gps_track(
    track_data: dict,
    analysis_type: str = "basic",
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Analyze GPS track data.
    
    analysis_type options:
    - basic: Basic statistics
    - speed: Speed analysis
    - elevation: Elevation analysis
    - segments: Segment analysis
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        result = gps_service.analyze_track(track_data, analysis_type)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.post("/smooth")
async def smooth_gps_track(
    track_data: dict,
    method: str = "moving_average",
    window_size: int = 5,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Smooth GPS track data.
    
    method options:
    - moving_average: Simple moving average
    - savgol: Savitzky-Golay filter
    - lowess: LOcally WEighted Scatterplot Smoothing
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        result = gps_service.smooth_track(track_data, method, window_size)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Smoothing failed: {str(e)}")

async def correct_track_elevation_async(track_id: str, dem_source: str = "srtm"):
    """
    Background task to correct elevation for a track.
    """
    from app.database import SessionLocal
    db = SessionLocal()
    
    try:
        track_uuid = uuid.UUID(track_id)
        track = db.query(GPSTrack).filter(GPSTrack.id == track_uuid).first()
        
        if track and track.points:
            # Get track coordinates
            points = track.points
            coordinates = [
                {"latitude": p.latitude, "longitude": p.longitude}
                for p in points
            ]
            
            # Get corrected elevations
            elevations = elevation_service.get_elevations(coordinates, dem_source)
            
            # Update points with corrected elevations
            for i, point in enumerate(points):
                if i < len(elevations):
                    point.elevation_corrected = elevations[i]
            
            db.commit()
            
    except Exception as e:
        print(f"Error correcting elevation for track {track_id}: {e}")
    finally:
        db.close()