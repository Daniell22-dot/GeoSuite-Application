"""
Watershed analysis routes.
Handles DEM processing, watershed delineation, and hydrological analysis.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import tempfile
import os
import uuid
import json

from app.services.watershed_service import WatershedService
from app.services.r_service import RService
from app.database import get_db
from app.models.geospatial import User, DEMFile, WatershedAnalysis
from app.services.auth_service import auth_service
from app.utils.gdal_wrapper import GDALWrapper

router = APIRouter()
watershed_service = WatershedService()
r_service = RService()
gdal_wrapper = GDALWrapper()

@router.post("/upload-dem")
async def upload_dem_file(
    file: UploadFile = File(...),
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Upload a Digital Elevation Model (DEM) file.
    
    Supported formats:
    - GeoTIFF (.tif, .tiff)
    - SRTM HGT (.hgt)
    - ASCII Grid (.asc)
    - USGS DEM (.dem)
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Check file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    supported_extensions = ['.tif', '.tiff', '.hgt', '.asc', '.dem']
    
    if file_ext not in supported_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported DEM format. Supported: {', '.join(supported_extensions)}"
        )
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Process DEM file
        result = gdal_wrapper.process_dem_file(temp_path)
        
        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to process DEM file'))
        
        # Generate unique filename
        dem_id = uuid.uuid4()
        dem_filename = f"dem_{dem_id}{file_ext}"
        dem_path = os.path.join("data", "dem", dem_filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(dem_path), exist_ok=True)
        
        # Move file to permanent location
        os.rename(temp_path, dem_path)
        
        # Create database record
        dem_file = DEMFile(
            id=dem_id,
            user_id=user.id,
            name=file.filename,
            file_path=dem_path,
            resolution=result.get('resolution', 0),
            bounds=result.get('bounds'),
            source=result.get('source', 'uploaded'),
            metadata=result.get('metadata', {}),
        )
        
        db.add(dem_file)
        db.commit()
        db.refresh(dem_file)
        
        return {
            "success": True,
            "message": "DEM file uploaded successfully",
            "dem_id": str(dem_file.id),
            "data": result
        }
        
    except Exception as e:
        # Clean up temp file if it exists
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise HTTPException(status_code=500, detail=f"Error processing DEM file: {str(e)}")

@router.post("/delineate")
async def delineate_watershed(
    dem_id: str,
    pour_point: dict,
    background_tasks: BackgroundTasks = None,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Delineate watershed from DEM at specified pour point.
    
    Args:
        dem_id: ID of the DEM file
        pour_point: {latitude, longitude} coordinates
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Validate pour point
    if not pour_point or 'latitude' not in pour_point or 'longitude' not in pour_point:
        raise HTTPException(status_code=400, detail="Invalid pour point coordinates")
    
    try:
        dem_uuid = uuid.UUID(dem_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid DEM ID format")
    
    # Get DEM file
    dem_file = db.query(DEMFile).filter(
        DEMFile.id == dem_uuid,
        DEMFile.user_id == user.id
    ).first()
    
    if not dem_file:
        raise HTTPException(status_code=404, detail="DEM file not found")
    
    # Check if file exists
    if not os.path.exists(dem_file.file_path):
        raise HTTPException(status_code=404, detail="DEM file not found on server")
    
    try:
        # Delineate watershed
        result = watershed_service.delineate_watershed(
            dem_file_path=dem_file.file_path,
            pour_point=pour_point
        )
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', 'Watershed delineation failed'))
        
        # Create analysis record
        analysis = WatershedAnalysis(
            id=uuid.uuid4(),
            user_id=user.id,
            dem_id=dem_file.id,
            name=f"Watershed at {pour_point['latitude']:.4f}, {pour_point['longitude']:.4f}",
            pour_point=pour_point,
            area_km2=result.get('watershed', {}).get('area_km2', 0),
            perimeter_km=result.get('watershed', {}).get('perimeter_km', 0),
            stream_length_km=result.get('streams', {}).get('total_length_km', 0),
            elevation_stats=result.get('watershed', {}).get('elevation_stats', {}),
            results=result,
            status="completed"
        )
        
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
        # Run additional analysis in background if needed
        if background_tasks:
            background_tasks.add_task(
                run_additional_analysis_async,
                analysis_id=str(analysis.id),
                dem_path=dem_file.file_path,
                watershed_data=result
            )
        
        return {
            "success": True,
            "message": "Watershed delineated successfully",
            "analysis_id": str(analysis.id),
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Watershed delineation failed: {str(e)}")

@router.post("/extract-streams")
async def extract_stream_network(
    dem_id: str,
    threshold: float = 1000,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Extract stream network from DEM.
    
    Args:
        dem_id: ID of the DEM file
        threshold: Flow accumulation threshold for stream initiation
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        dem_uuid = uuid.UUID(dem_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid DEM ID format")
    
    # Get DEM file
    dem_file = db.query(DEMFile).filter(
        DEMFile.id == dem_uuid,
        DEMFile.user_id == user.id
    ).first()
    
    if not dem_file:
        raise HTTPException(status_code=404, detail="DEM file not found")
    
    try:
        # Extract stream network
        result = watershed_service.extract_stream_network(
            dem_file_path=dem_file.file_path,
            threshold=threshold
        )
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stream extraction failed: {str(e)}")

@router.post("/flow-path")
async def calculate_flow_path(
    dem_id: str,
    start_point: dict,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Calculate flow path from starting point.
    
    Args:
        dem_id: ID of the DEM file
        start_point: {latitude, longitude} starting coordinates
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        dem_uuid = uuid.UUID(dem_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid DEM ID format")
    
    # Get DEM file
    dem_file = db.query(DEMFile).filter(
        DEMFile.id == dem_uuid,
        DEMFile.user_id == user.id
    ).first()
    
    if not dem_file:
        raise HTTPException(status_code=404, detail="DEM file not found")
    
    try:
        # Calculate flow path
        result = watershed_service.calculate_flow_path(
            dem_file_path=dem_file.file_path,
            start_point=start_point
        )
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Flow path calculation failed: {str(e)}")

@router.post("/flow-accumulation")
async def calculate_flow_accumulation(
    dem_id: str,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Calculate flow accumulation grid from DEM.
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        dem_uuid = uuid.UUID(dem_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid DEM ID format")
    
    # Get DEM file
    dem_file = db.query(DEMFile).filter(
        DEMFile.id == dem_uuid,
        DEMFile.user_id == user.id
    ).first()
    
    if not dem_file:
        raise HTTPException(status_code=404, detail="DEM file not found")
    
    try:
        # Calculate flow accumulation
        result = watershed_service.calculate_flow_accumulation(
            dem_file_path=dem_file.file_path
        )
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Flow accumulation calculation failed: {str(e)}")

@router.post("/r-analysis")
async def run_r_analysis(
    analysis_type: str,
    data: dict,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Run R-based hydrological analysis.
    
    analysis_type options:
    - fdc: Flow Duration Curve
    - uhg: Unit Hydrograph
    - idf: Intensity-Duration-Frequency
    - distribution: Statistical distribution fitting
    - nse: Nash-Sutcliffe Efficiency
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        if analysis_type == "fdc":
            # Flow Duration Curve
            flow_data = data.get("flow_data", [])
            result = r_service.calculate_flow_duration_curve(flow_data)
            
        elif analysis_type == "uhg":
            # Unit Hydrograph
            rainfall = data.get("rainfall", [])
            runoff = data.get("runoff", [])
            method = data.get("method", "snyder")
            result = r_service.calculate_unit_hydrograph(rainfall, runoff, method)
            
        elif analysis_type == "idf":
            # IDF Analysis
            rainfall_data = data.get("rainfall_data", [])
            result = r_service.perform_hyetograph_analysis(rainfall_data)
            
        elif analysis_type == "distribution":
            # Distribution fitting
            values = data.get("values", [])
            distribution = data.get("distribution", "gev")
            result = r_service.fit_distribution(values, distribution)
            
        elif analysis_type == "nse":
            # Nash-Sutcliffe Efficiency
            observed = data.get("observed", [])
            simulated = data.get("simulated", [])
            nse = r_service.calculate_nash_sutcliffe(observed, simulated)
            result = {"nash_sutcliffe_efficiency": nse}
            
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported analysis type: {analysis_type}")
        
        return {
            "success": True,
            "analysis_type": analysis_type,
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"R analysis failed: {str(e)}")

@router.get("/analyses")
async def get_watershed_analyses(
    limit: int = 50,
    offset: int = 0,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Get user's watershed analyses.
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    analyses = db.query(WatershedAnalysis).filter(
        WatershedAnalysis.user_id == user.id
    ).order_by(
        WatershedAnalysis.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    return {
        "analyses": [
            {
                "id": str(analysis.id),
                "name": analysis.name,
                "dem_id": str(analysis.dem_id),
                "pour_point": analysis.pour_point,
                "area_km2": analysis.area_km2,
                "perimeter_km": analysis.perimeter_km,
                "stream_length_km": analysis.stream_length_km,
                "status": analysis.status,
                "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
                "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None
            }
            for analysis in analyses
        ],
        "total": db.query(WatershedAnalysis).filter(WatershedAnalysis.user_id == user.id).count()
    }

@router.get("/analyses/{analysis_id}")
async def get_analysis_details(
    analysis_id: str,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Get detailed watershed analysis results.
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        analysis_uuid = uuid.UUID(analysis_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid analysis ID format")
    
    analysis = db.query(WatershedAnalysis).filter(
        WatershedAnalysis.id == analysis_uuid,
        WatershedAnalysis.user_id == user.id
    ).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return {
        "analysis": {
            "id": str(analysis.id),
            "name": analysis.name,
            "dem_id": str(analysis.dem_id),
            "pour_point": analysis.pour_point,
            "area_km2": analysis.area_km2,
            "perimeter_km": analysis.perimeter_km,
            "stream_length_km": analysis.stream_length_km,
            "elevation_stats": analysis.elevation_stats,
            "status": analysis.status,
            "results": analysis.results,
            "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
            "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None
        }
    }

@router.delete("/analyses/{analysis_id}")
async def delete_analysis(
    analysis_id: str,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Delete a watershed analysis.
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        analysis_uuid = uuid.UUID(analysis_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid analysis ID format")
    
    analysis = db.query(WatershedAnalysis).filter(
        WatershedAnalysis.id == analysis_uuid,
        WatershedAnalysis.user_id == user.id
    ).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    db.delete(analysis)
    db.commit()
    
    return {"success": True, "message": "Analysis deleted successfully"}

@router.get("/dem-files")
async def get_dem_files(
    limit: int = 50,
    offset: int = 0,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Get user's DEM files.
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    dem_files = db.query(DEMFile).filter(
        DEMFile.user_id == user.id
    ).order_by(
        DEMFile.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    return {
        "dem_files": [
            {
                "id": str(dem.id),
                "name": dem.name,
                "resolution": dem.resolution,
                "bounds": dem.bounds,
                "source": dem.source,
                "created_at": dem.created_at.isoformat() if dem.created_at else None
            }
            for dem in dem_files
        ],
        "total": db.query(DEMFile).filter(DEMFile.user_id == user.id).count()
    }

async def run_additional_analysis_async(analysis_id: str, dem_path: str, watershed_data: dict):
    """
    Background task for additional watershed analysis.
    """
    from app.database import SessionLocal
    db = SessionLocal()
    
    try:
        analysis_uuid = uuid.UUID(analysis_id)
        analysis = db.query(WatershedAnalysis).filter(WatershedAnalysis.id == analysis_uuid).first()
        
        if analysis:
            # Run additional analyses
            try:
                # Calculate flow accumulation
                flow_accum = watershed_service.calculate_flow_accumulation(dem_path)
                if flow_accum.get('success'):
                    if not analysis.results:
                        analysis.results = {}
                    analysis.results['flow_accumulation'] = flow_accum.get('data')
                
                # Extract streams with different thresholds
                streams = watershed_service.extract_stream_network(dem_path, threshold=500)
                if streams.get('success'):
                    if not analysis.results:
                        analysis.results = {}
                    analysis.results['streams_detailed'] = streams.get('data')
                
                db.commit()
                
            except Exception as e:
                print(f"Error in additional analysis for {analysis_id}: {e}")
                
    finally:
        db.close()