"""
File upload and conversion routes.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
import os
import io
import zipfile
import tempfile
import uuid
from typing import List
import shutil

from app.services.file_converter import FileConverterService
from app.services.gps_service import GPSService
from app.services.marine_service import MarineChartService
from app.services.watershed_service import WatershedService

router = APIRouter()
file_converter = FileConverterService()
gps_service = GPSService()
marine_service = MarineChartService()
watershed_service = WatershedService()

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    file_type: str = "auto"
):
    """
    Upload a file for processing.
    
    Supported file types:
    - GPS: .gpx, .kml, .geojson, .csv
    - Marine: .kap, .bsb, .dwg, .dxf
    - DEM: .tif, .tiff, .hgt, .asc
    - General: .shp, .zip (with shapefile)
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Create temp file
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, file.filename)
    
    try:
        # Save uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Determine file type from extension
        file_ext = os.path.splitext(file.filename)[1].lower()[1:]
        
        # Process based on file type
        if file_ext in ['gpx', 'kml', 'geojson', 'csv']:
            # GPS data
            result = gps_service.parse_gpx(file_path)
            result['file_type'] = 'gps'
            
        elif file_ext in ['kap', 'bsb']:
            # Marine chart
            result = marine_service.process_kap_file(file_path)
            result['file_type'] = 'marine'
            
        elif file_ext in ['dwg', 'dxf']:
            # CAD file
            result = marine_service.process_dwg_file(file_path)
            result['file_type'] = 'cad'
            
        elif file_ext in ['tif', 'tiff', 'hgt', 'asc', 'dem']:
            # DEM file
            result = {
                'success': True,
                'file_type': 'dem',
                'file_path': file_path,
                'file_name': file.filename,
                'file_size': os.path.getsize(file_path)
            }
            
        elif file_ext == 'shp' or file_ext == 'zip':
            # Shapefile
            result = {
                'success': True,
                'file_type': 'vector',
                'file_path': file_path,
                'file_name': file.filename
            }
            
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type: {file_ext}"
            )
        
        # Add common metadata
        result['original_filename'] = file.filename
        result['file_size'] = os.path.getsize(file_path)
        result['temp_path'] = file_path
        
        return result
        
    except Exception as e:
        # Cleanup on error
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/convert")
async def convert_file(
    background_tasks: BackgroundTasks,
    input_file: UploadFile = File(...),
    output_format: str = "geojson"
):
    """
    Convert a file to another format.
    """
    # Save uploaded file temporarily
    temp_dir = tempfile.mkdtemp()
    input_path = os.path.join(temp_dir, input_file.filename)
    
    try:
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(input_file.file, buffer)
        
        # Convert file
        result = file_converter.convert_file(input_path, output_format)
        
        # Schedule cleanup
        background_tasks.add_task(
            _cleanup_temp_files,
            [input_path, result['output_file']]
        )
        
        # Return file as download
        return StreamingResponse(
            io.BytesIO(result['file_content']),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename=converted.{output_format}"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/formats")
async def get_supported_formats():
    """
    Get all supported file formats and conversions.
    """
    formats = file_converter.get_supported_conversions()
    
    return {
        "supported_conversions": formats,
        "input_formats": list(formats.keys()),
        "output_formats": list(set(
            fmt for sublist in formats.values() for fmt in sublist
        ))
    }

@router.post("/batch-convert")
async def batch_convert_files(
    files: List[UploadFile] = File(...),
    output_format: str = "geojson",
    output_zip: bool = True
):
    """
    Convert multiple files at once.
    Returns a ZIP file if output_zip is True.
    """
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Save all files temporarily
    temp_dir = tempfile.mkdtemp()
    input_paths = []
    
    try:
        for file in files:
            file_path = os.path.join(temp_dir, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            input_paths.append(file_path)
        
        # Convert all files
        results = file_converter.batch_convert(input_paths, output_format)
        
        if output_zip and results['successful'] > 0:
            # Create ZIP file with all converted files
            zip_path = os.path.join(temp_dir, "converted_files.zip")
            
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for result in results['results']:
                    if result['success']:
                        zipf.write(
                            result['output_file'],
                            os.path.basename(result['output_file'])
                        )
            
            # Return ZIP file
            with open(zip_path, 'rb') as f:
                content = f.read()
            
            return StreamingResponse(
                io.BytesIO(content),
                media_type="application/zip",
                headers={
                    "Content-Disposition": "attachment; filename=converted_files.zip"
                }
            )
        
        else:
            # Return results as JSON
            return results
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Cleanup
        _cleanup_temp_files(input_paths)

def _cleanup_temp_files(file_paths: List[str]):
    """
    Clean up temporary files.
    """
    for file_path in file_paths:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        # Also try to remove parent directory if empty
        dir_path = os.path.dirname(file_path)
        if os.path.exists(dir_path) and not os.listdir(dir_path):
            try:
                os.rmdir(dir_path)
            except:
                pass