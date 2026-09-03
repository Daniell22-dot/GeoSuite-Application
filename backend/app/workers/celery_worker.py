"""
Celery worker for asynchronous tasks.
Handles long-running operations like watershed analysis, 
large file conversions, and batch processing.
"""
from celery import Celery
import os
import tempfile
from typing import Dict, Any, List
import time

from app.services.watershed_service import WatershedService
from app.services.marine_service import MarineChartService
from app.services.gps_service import GPSService

# Create Celery app
celery_app = Celery(
    'geosuite',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0')
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_max_tasks_per_child=100,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3000,  # 50 minutes soft limit
    broker_connection_retry_on_startup=True
)

@celery_app.task(bind=True, name='process_watershed_analysis')
def process_watershed_analysis(self, dem_path: str, pour_point: Dict) -> Dict:
    """
    Process watershed analysis asynchronously.
    
    Args:
        dem_path: Path to DEM file
        pour_point: Dictionary with latitude and longitude
    
    Returns:
        Watershed analysis results
    """
    self.update_state(state='PROGRESS', meta={'status': 'Starting analysis'})
    
    try:
        watershed_service = WatershedService()
        
        # Update progress
        self.update_state(state='PROGRESS', meta={'status': 'Reading DEM'})
        
        # Delineate watershed
        result = watershed_service.delineate_watershed(
            dem_path,
            (pour_point['latitude'], pour_point['longitude'])
        )
        
        # Update progress
        self.update_state(state='PROGRESS', meta={'status': 'Extracting streams'})
        
        # Extract stream network
        streams = watershed_service.extract_stream_network(dem_path)
        
        # Update progress
        self.update_state(state='PROGRESS', meta={'status': 'Calculating flow paths'})
        
        # Calculate flow path
        flow_path = watershed_service.calculate_flow_path(
            dem_path,
            (pour_point['latitude'], pour_point['longitude'])
        )
        
        return {
            'success': True,
            'watershed': result.__dict__,
            'streams': streams,
            'flow_path': flow_path,
            'task_id': self.request.id
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'task_id': self.request.id
        }

@celery_app.task(bind=True, name='process_marine_chart')
def process_marine_chart(self, chart_path: str) -> Dict:
    """
    Process marine chart file asynchronously.
    
    Args:
        chart_path: Path to marine chart file
    
    Returns:
        Processed chart data
    """
    self.update_state(state='PROGRESS', meta={'status': 'Parsing chart file'})
    
    try:
        marine_service = MarineChartService()
        
        # Determine file type
        file_ext = os.path.splitext(chart_path)[1].lower()
        
        if file_ext in ['.kap', '.bsb']:
            # Process KAP/BSB file
            self.update_state(state='PROGRESS', meta={'status': 'Processing KAP chart'})
            result = marine_service.process_kap_file(chart_path)
            
        elif file_ext in ['.dwg', '.dxf']:
            # Process CAD file
            self.update_state(state='PROGRESS', meta={'status': 'Processing CAD file'})
            result = marine_service.process_dwg_file(chart_path)
            
        else:
            return {
                'success': False,
                'error': f'Unsupported file type: {file_ext}',
                'task_id': self.request.id
            }
        
        return {
            'success': True,
            'result': result,
            'task_id': self.request.id
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'task_id': self.request.id
        }

@celery_app.task(bind=True, name='batch_process_gpx')
def batch_process_gpx(self, gpx_files: List[str], 
                     correct_elevation: bool = True) -> Dict:
    """
    Process multiple GPX files in batch.
    
    Args:
        gpx_files: List of GPX file paths
        correct_elevation: Whether to correct elevation
    
    Returns:
        Batch processing results
    """
    results = []
    total_files = len(gpx_files)
    
    gps_service = GPSService()
    
    for i, gpx_file in enumerate(gpx_files):
        # Update progress
        progress = (i + 1) / total_files * 100
        self.update_state(
            state='PROGRESS',
            meta={
                'status': f'Processing file {i+1}/{total_files}',
                'progress': progress,
                'current_file': os.path.basename(gpx_file)
            }
        )
        
        try:
            # Parse GPX file
            gpx_data = gps_service.parse_gpx(gpx_file)
            
            # Correct elevation if requested
            if correct_elevation:
                gpx_data = gps_service.correct_gpx_elevation(gpx_data)
            
            results.append({
                'file': os.path.basename(gpx_file),
                'success': True,
                'data': gpx_data
            })
            
        except Exception as e:
            results.append({
                'file': os.path.basename(gpx_file),
                'success': False,
                'error': str(e)
            })
    
    return {
        'success': True,
        'total_files': total_files,
        'successful': len([r for r in results if r['success']]),
        'failed': len([r for r in results if not r['success']]),
        'results': results,
        'task_id': self.request.id
    }

@celery_app.task(bind=True, name='generate_elevation_profile')
def generate_elevation_profile(self, coordinates: List[Dict], 
                              dem_source: str = "srtm") -> Dict:
    """
    Generate elevation profile from coordinates.
    
    Args:
        coordinates: List of {'latitude': x, 'longitude': y} dictionaries
        dem_source: DEM source to use
    
    Returns:
        Elevation profile data
    """
    self.update_state(state='PROGRESS', meta={'status': 'Initializing'})
    
    try:
        from app.utils.dem_processor import DEMProcessor
        
        dem_processor = DEMProcessor()
        
        # Extract lat/lon pairs
        lat_lon_pairs = [(c['latitude'], c['longitude']) for c in coordinates]
        
        # Update progress
        self.update_state(state='PROGRESS', meta={'status': 'Fetching elevations'})
        
        # Get elevations
        elevations = dem_processor.get_elevation_profile(lat_lon_pairs, dem_source)
        
        # Calculate statistics
        if elevations:
            import numpy as np
            elev_array = np.array(elevations)
            
            stats = {
                'min': float(np.min(elev_array)),
                'max': float(np.max(elev_array)),
                'mean': float(np.mean(elev_array)),
                'std': float(np.std(elev_array)),
                'total_points': len(elevations)
            }
            
            # Calculate cumulative ascent/descent
            if len(elev_array) > 1:
                diffs = np.diff(elev_array)
                stats['total_ascent'] = float(np.sum(diffs[diffs > 0]))
                stats['total_descent'] = float(np.sum(-diffs[diffs < 0]))
        
        # Create profile data
        profile_data = []
        for i, (coord, elev) in enumerate(zip(coordinates, elevations)):
            profile_data.append({
                'point_number': i + 1,
                'latitude': coord['latitude'],
                'longitude': coord['longitude'],
                'elevation': elev,
                'cumulative_distance': 0  # Would need distance calculation
            })
        
        return {
            'success': True,
            'profile': profile_data,
            'statistics': stats,
            'dem_source': dem_source,
            'task_id': self.request.id
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'task_id': self.request.id
        }

@celery_app.task(bind=True, name='merge_marine_charts')
def merge_marine_charts(self, chart_paths: List[str], 
                       output_format: str = "geotiff") -> Dict:
    """
    Merge multiple marine charts into one.
    
    Args:
        chart_paths: List of chart file paths
        output_format: Output format (geotiff, geojson, etc.)
    
    Returns:
        Merge results
    """
    self.update_state(state='PROGRESS', meta={'status': 'Initializing merge'})
    
    try:
        marine_service = MarineChartService()
        
        # Update progress
        self.update_state(state='PROGRESS', meta={'status': 'Processing charts'})
        
        # Merge charts
        output_path = marine_service.merge_charts(chart_paths, output_format)
        
        # Read output file
        with open(output_path, 'rb') as f:
            file_content = f.read()
        
        return {
            'success': True,
            'output_path': output_path,
            'file_size': len(file_content),
            'output_format': output_format,
            'task_id': self.request.id
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'task_id': self.request.id
        }

# Task status checker
@celery_app.task(bind=True, name='check_task_status')
def check_task_status(self, task_id: str) -> Dict:
    """
    Check the status of a Celery task.
    
    Args:
        task_id: Celery task ID
    
    Returns:
        Task status information
    """
    task = celery_app.AsyncResult(task_id)
    
    response = {
        'task_id': task_id,
        'status': task.status,
        'ready': task.ready()
    }
    
    if task.status == 'PROGRESS':
        response['progress'] = task.info.get('progress', 0)
        response['status_message'] = task.info.get('status', '')
        
    elif task.status == 'SUCCESS':
        response['result'] = task.result
        
    elif task.status == 'FAILURE':
        response['error'] = str(task.info)
    
    return response


@celery_app.task(bind=True, name='process_drone_survey')
def process_drone_survey(self, survey_id: str, images_dir: str,
                         output_dir: str) -> Dict:
    """
    Process a drone survey with OpenDroneMap.

    Args:
        survey_id: Survey identifier
        images_dir: Path to directory containing drone images
        output_dir: Path for ODM outputs

    Returns:
        Processing results with output file paths
    """
    from app.services.odm_service import ODMService, TileService
    from app.config import settings

    self.update_state(state='PROGRESS', meta={
        'status': 'Initializing ODM',
        'progress': 0.0,
    })

    try:
        odm = ODMService(
            odm_path=settings.ODM_PATH or "run.py",
            use_docker=settings.ODM_DOCKER,
        )

        if not odm.is_available():
            return {
                'success': False,
                'error': 'OpenDroneMap is not installed. '
                         'Install locally or set ODM_DOCKER=true and pull opendronemap/odm image.',
                'task_id': self.request.id,
            }

        def progress_callback(progress, message):
            self.update_state(state='PROGRESS', meta={
                'status': message,
                'progress': progress,
            })

        # Run ODM
        result = odm.process_survey(
            images_dir=images_dir,
            output_dir=output_dir,
            progress_callback=progress_callback,
        )

        # Generate tiles for web viewing if orthomosaic exists
        cog_path = result.get("files", {}).get("cog")
        if cog_path:
            self.update_state(state='PROGRESS', meta={
                'status': 'Generating web tiles',
                'progress': 0.95,
            })
            tile_path = os.path.join(output_dir, "tiles.mbtiles")
            TileService.generate_mbtiles(cog_path, tile_path)
            result["files"]["tiles"] = tile_path

        result['task_id'] = self.request.id
        return result

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'task_id': self.request.id,
        }