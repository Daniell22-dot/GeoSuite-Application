"""
GDAL wrapper service for geospatial operations.
Provides a unified interface for GDAL/OSGeo operations.
"""
import os
import tempfile
import json
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import subprocess
import shutil

try:
    from osgeo import gdal, ogr, osr, gdalconst
    GDAL_AVAILABLE = True
except ImportError:
    GDAL_AVAILABLE = False
    print("Warning: GDAL not installed. Some geospatial features will be disabled.")

class GDALWrapper:
    """
    Wrapper for GDAL operations with error handling and convenience methods.
    """
    
    def __init__(self):
        self.gdal_available = GDAL_AVAILABLE
        
        if self.gdal_available:
            # Set GDAL configuration options
            gdal.SetConfigOption('GDAL_NUM_THREADS', 'ALL_CPUS')
            gdal.SetConfigOption('GDAL_CACHEMAX', '512')
            gdal.UseExceptions()
    
    def check_gdal(self) -> bool:
        """Check if GDAL is available."""
        return self.gdal_available
    
    def get_gdal_version(self) -> str:
        """Get GDAL version."""
        if not self.gdal_available:
            return "GDAL not installed"
        return gdal.__version__
    
    def process_dem_file(self, file_path: str) -> Dict[str, Any]:
        """
        Process DEM file and extract metadata.
        
        Args:
            file_path: Path to DEM file
        
        Returns:
            Dictionary with DEM information
        """
        if not self.gdal_available:
            return self._fallback_dem_processing(file_path)
        
        try:
            # Open DEM file
            dataset = gdal.Open(file_path, gdal.GA_ReadOnly)
            if dataset is None:
                raise ValueError(f"Could not open DEM file: {file_path}")
            
            # Get basic information
            width = dataset.RasterXSize
            height = dataset.RasterYSize
            bands = dataset.RasterCount
            projection = dataset.GetProjection()
            geotransform = dataset.GetGeoTransform()
            
            # Calculate bounds
            if geotransform and geotransform != (0, 1, 0, 0, 0, 1):
                min_x = geotransform[0]
                max_y = geotransform[3]
                max_x = min_x + geotransform[1] * width
                min_y = max_y + geotransform[5] * height
                
                # Convert to lat/lon if needed
                if projection:
                    source_srs = osr.SpatialReference()
                    source_srs.ImportFromWkt(projection)
                    
                    target_srs = osr.SpatialReference()
                    target_srs.ImportFromEPSG(4326)  # WGS84
                    
                    transform = osr.CoordinateTransformation(source_srs, target_srs)
                    
                    # Transform corners
                    corners = [
                        (min_x, max_y),  # NW
                        (max_x, max_y),  # NE
                        (max_x, min_y),  # SE
                        (min_x, min_y),  # SW
                    ]
                    
                    transformed = []
                    for x, y in corners:
                        point = ogr.Geometry(ogr.wkbPoint)
                        point.AddPoint(x, y)
                        point.Transform(transform)
                        transformed.append((point.GetX(), point.GetY()))
                    
                    lons = [p[0] for p in transformed]
                    lats = [p[1] for p in transformed]
                    
                    bounds = {
                        'west': min(lons),
                        'east': max(lons),
                        'south': min(lats),
                        'north': max(lats),
                    }
                else:
                    bounds = {
                        'west': min_x,
                        'east': max_x,
                        'south': min_y,
                        'north': max_y,
                    }
            else:
                bounds = None
            
            # Get statistics from first band
            band = dataset.GetRasterBand(1)
            nodata = band.GetNoDataValue()
            
            # Calculate resolution
            resolution = None
            if geotransform and geotransform[1] != 0:
                resolution = abs(geotransform[1])
            
            # Get metadata
            metadata = {
                'driver': dataset.GetDriver().ShortName,
                'width': width,
                'height': height,
                'bands': bands,
                'data_type': gdal.GetDataTypeName(band.DataType),
                'nodata_value': nodata,
                'projection_wkt': projection,
                'geotransform': geotransform,
                'file_size': os.path.getsize(file_path),
            }
            
            # Try to get min/max values
            try:
                min_val, max_val, mean_val, std_val = band.ComputeStatistics(False)
                metadata.update({
                    'min_value': float(min_val),
                    'max_value': float(max_val),
                    'mean_value': float(mean_val),
                    'std_value': float(std_val),
                })
            except:
                pass
            
            # Close dataset
            dataset = None
            
            return {
                'success': True,
                'bounds': bounds,
                'resolution': resolution,
                'metadata': metadata,
                'source': self._detect_dem_source(file_path),
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'bounds': None,
                'metadata': {}
            }
    
    def process_raster_file(self, file_path: str) -> Dict[str, Any]:
        """
        Process any raster file (GeoTIFF, PNG with world file, etc.)
        
        Args:
            file_path: Path to raster file
        
        Returns:
            Dictionary with raster information
        """
        if not self.gdal_available:
            return self._fallback_raster_processing(file_path)
        
        try:
            # Try to open as GDAL dataset
            dataset = gdal.Open(file_path, gdal.GA_ReadOnly)
            if dataset is None:
                # Try to find world file
                world_file = self._find_world_file(file_path)
                if world_file:
                    # Create VRT with world file
                    vrt_path = self._create_vrt_with_world(file_path, world_file)
                    dataset = gdal.Open(vrt_path, gdal.GA_ReadOnly)
                else:
                    raise ValueError(f"Could not open raster file and no world file found: {file_path}")
            
            # Get basic information
            width = dataset.RasterXSize
            height = dataset.RasterYSize
            bands = dataset.RasterCount
            projection = dataset.GetProjection()
            geotransform = dataset.GetGeoTransform()
            
            # Calculate bounds if georeferenced
            bounds = None
            if geotransform and geotransform != (0, 1, 0, 0, 0, 1):
                min_x = geotransform[0]
                max_y = geotransform[3]
                max_x = min_x + geotransform[1] * width
                min_y = max_y + geotransform[5] * height
                
                bounds = {
                    'west': min_x,
                    'east': max_x,
                    'south': min_y,
                    'north': max_y,
                }
                
                # Try to convert to WGS84
                if projection:
                    try:
                        source_srs = osr.SpatialReference()
                        source_srs.ImportFromWkt(projection)
                        
                        target_srs = osr.SpatialReference()
                        target_srs.ImportFromEPSG(4326)
                        
                        transform = osr.CoordinateTransformation(source_srs, target_srs)
                        
                        point = ogr.Geometry(ogr.wkbPoint)
                        point.AddPoint(min_x, max_y)
                        point.Transform(transform)
                        
                        bounds = {
                            'west': point.GetX(),
                            'east': point.GetX() + (max_x - min_x),
                            'south': point.GetY() - (max_y - min_y),
                            'north': point.GetY(),
                        }
                    except:
                        pass
            
            # Get metadata
            metadata = {
                'driver': dataset.GetDriver().ShortName,
                'width': width,
                'height': height,
                'bands': bands,
                'projection': projection,
                'geotransform': geotransform,
                'is_georeferenced': bounds is not None,
            }
            
            # Get band information
            band_info = []
            for i in range(1, min(bands, 4) + 1):  # First 3 bands max
                band = dataset.GetRasterBand(i)
                band_info.append({
                    'band': i,
                    'data_type': gdal.GetDataTypeName(band.DataType),
                    'color_interpretation': gdal.GetColorInterpretationName(band.GetColorInterpretation()),
                    'overviews': band.GetOverviewCount(),
                })
            
            metadata['bands'] = band_info
            
            dataset = None
            
            return {
                'success': True,
                'bounds': bounds,
                'metadata': metadata,
                'is_georeferenced': bounds is not None,
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'bounds': None,
                'metadata': {}
            }
    
    def reproject_raster(self, input_path: str, output_path: str, 
                        target_epsg: int = 4326, resample_method: str = 'bilinear') -> Dict[str, Any]:
        """
        Reproject raster to target coordinate system.
        
        Args:
            input_path: Input raster file
            output_path: Output raster file
            target_epsg: Target EPSG code
            resample_method: Resampling method
        
        Returns:
            Dictionary with reprojection results
        """
        if not self.gdal_available:
            return {'success': False, 'error': 'GDAL not available'}
        
        try:
            # Open source dataset
            src_ds = gdal.Open(input_path, gdal.GA_ReadOnly)
            if src_ds is None:
                raise ValueError(f"Could not open input file: {input_path}")
            
            # Define target SRS
            target_srs = osr.SpatialReference()
            target_srs.ImportFromEPSG(target_epsg)
            
            # Get source SRS
            src_srs = osr.SpatialReference()
            src_srs.ImportFromWkt(src_ds.GetProjection())
            
            # Define resampling method
            resample_methods = {
                'nearest': gdal.GRA_NearestNeighbour,
                'bilinear': gdal.GRA_Bilinear,
                'cubic': gdal.GRA_Cubic,
                'cubicspline': gdal.GRA_CubicSpline,
                'lanczos': gdal.GRA_Lanczos,
                'average': gdal.GRA_Average,
                'mode': gdal.GRA_Mode,
            }
            
            resample_algo = resample_methods.get(resample_method, gdal.GRA_Bilinear)
            
            # Perform warp
            result = gdal.Warp(
                output_path,
                src_ds,
                dstSRS=target_srs,
                resampleAlg=resample_algo,
                format='GTiff',
                creationOptions=['COMPRESS=LZW', 'TILED=YES', 'BIGTIFF=IF_SAFER']
            )
            
            if result is None:
                raise ValueError("Reprojection failed")
            
            src_ds = None
            result = None
            
            return {
                'success': True,
                'output_path': output_path,
                'target_epsg': target_epsg,
                'resample_method': resample_method,
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'output_path': None,
            }
    
    def clip_raster(self, input_path: str, output_path: str, 
                   bounds: Dict[str, float], target_epsg: int = None) -> Dict[str, Any]:
        """
        Clip raster to specified bounds.
        
        Args:
            input_path: Input raster file
            output_path: Output raster file
            bounds: {west, east, south, north}
            target_epsg: Optional target EPSG for bounds
        
        Returns:
            Dictionary with clipping results
        """
        if not self.gdal_available:
            return {'success': False, 'error': 'GDAL not available'}
        
        try:
            # Open source dataset
            src_ds = gdal.Open(input_path, gdal.GA_ReadOnly)
            if src_ds is None:
                raise ValueError(f"Could not open input file: {input_path}")
            
            # Convert bounds if target EPSG specified
            if target_epsg and target_epsg != 4326:
                # Convert bounds to raster's CRS
                src_srs = osr.SpatialReference()
                src_srs.ImportFromWkt(src_ds.GetProjection())
                
                target_srs = osr.SpatialReference()
                target_srs.ImportFromEPSG(target_epsg)
                
                transform = osr.CoordinateTransformation(target_srs, src_srs)
                
                # Transform bounds corners
                corners = [
                    (bounds['west'], bounds['north']),
                    (bounds['east'], bounds['north']),
                    (bounds['east'], bounds['south']),
                    (bounds['west'], bounds['south']),
                ]
                
                transformed = []
                for x, y in corners:
                    point = ogr.Geometry(ogr.wkbPoint)
                    point.AddPoint(x, y)
                    point.Transform(transform)
                    transformed.append((point.GetX(), point.GetY()))
                
                lons = [p[0] for p in transformed]
                lats = [p[1] for p in transformed]
                
                clip_bounds = [min(lons), min(lats), max(lons), max(lats)]
            else:
                clip_bounds = [bounds['west'], bounds['south'], bounds['east'], bounds['north']]
            
            # Perform clip
            result = gdal.Translate(
                output_path,
                src_ds,
                projWin=clip_bounds,
                format='GTiff',
                creationOptions=['COMPRESS=LZW', 'TILED=YES']
            )
            
            if result is None:
                raise ValueError("Clipping failed")
            
            src_ds = None
            result = None
            
            return {
                'success': True,
                'output_path': output_path,
                'bounds': bounds,
                'clip_bounds': clip_bounds,
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'output_path': None,
            }
    
    def merge_rasters(self, input_paths: List[str], output_path: str) -> Dict[str, Any]:
        """
        Merge multiple raster files into a mosaic.
        
        Args:
            input_paths: List of input raster files
            output_path: Output mosaic file
        
        Returns:
            Dictionary with merging results
        """
        if not self.gdal_available:
            return {'success': False, 'error': 'GDAL not available'}
        
        try:
            # Check all input files exist
            for path in input_paths:
                if not os.path.exists(path):
                    raise ValueError(f"Input file not found: {path}")
            
            # Build VRT first
            vrt_path = output_path.replace('.tif', '.vrt')
            vrt = gdal.BuildVRT(vrt_path, input_paths)
            if vrt is None:
                raise ValueError("Failed to build VRT")
            vrt = None
            
            # Convert VRT to GeoTIFF
            result = gdal.Translate(
                output_path,
                vrt_path,
                format='GTiff',
                creationOptions=['COMPRESS=LZW', 'TILED=YES', 'BIGTIFF=IF_SAFER']
            )
            
            if result is None:
                raise ValueError("Failed to create mosaic")
            
            # Clean up VRT
            if os.path.exists(vrt_path):
                os.remove(vrt_path)
            
            result = None
            
            return {
                'success': True,
                'output_path': output_path,
                'num_inputs': len(input_paths),
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'output_path': None,
            }
    
    def raster_to_vector(self, input_path: str, output_path: str, 
                        band: int = 1, mask_value: float = None) -> Dict[str, Any]:
        """
        Convert raster to vector (polygonize).
        
        Args:
            input_path: Input raster file
            output_path: Output vector file
            band: Band to polygonize
            mask_value: Value to use as mask
        
        Returns:
            Dictionary with vectorization results
        """
        if not self.gdal_available:
            return {'success': False, 'error': 'GDAL not available'}
        
        try:
            # Open raster
            src_ds = gdal.Open(input_path, gdal.GA_ReadOnly)
            if src_ds is None:
                raise ValueError(f"Could not open input file: {input_path}")
            
            src_band = src_ds.GetRasterBand(band)
            
            # Create output shapefile
            driver = ogr.GetDriverByName('ESRI Shapefile')
            if os.path.exists(output_path):
                driver.DeleteDataSource(output_path)
            
            dst_ds = driver.CreateDataSource(output_path)
            
            # Create layer
            srs = osr.SpatialReference()
            srs.ImportFromWkt(src_ds.GetProjection())
            
            layer = dst_ds.CreateLayer('polygons', srs, ogr.wkbPolygon)
            
            # Add field for raster value
            field_defn = ogr.FieldDefn('value', ogr.OFTReal)
            layer.CreateField(field_defn)
            
            # Polygonize
            if mask_value is not None:
                # Create mask band
                mask_band = src_band.GetMaskBand()
                result = gdal.Polygonize(src_band, mask_band, layer, 0, [], callback=None)
            else:
                result = gdal.Polygonize(src_band, None, layer, 0, [], callback=None)
            
            if result != 0:
                raise ValueError("Polygonization failed")
            
            src_ds = None
            dst_ds = None
            
            return {
                'success': True,
                'output_path': output_path,
                'feature_count': layer.GetFeatureCount() if 'layer' in locals() else 0,
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'output_path': None,
            }
    
    def calculate_slope(self, dem_path: str, output_path: str, 
                       use_degrees: bool = True) -> Dict[str, Any]:
        """
        Calculate slope from DEM.
        
        Args:
            dem_path: Input DEM file
            output_path: Output slope file
            use_degrees: Return slope in degrees (True) or percent (False)
        
        Returns:
            Dictionary with slope calculation results
        """
        if not self.gdal_available:
            return {'success': False, 'error': 'GDAL not available'}
        
        try:
            # Open DEM
            dem_ds = gdal.Open(dem_path, gdal.GA_ReadOnly)
            if dem_ds is None:
                raise ValueError(f"Could not open DEM file: {dem_path}")
            
            # Calculate slope
            slope_type = 1 if use_degrees else 2  # 1=degrees, 2=percent
            
            # Create output
            driver = gdal.GetDriverByName('GTiff')
            dst_ds = driver.Create(
                output_path,
                dem_ds.RasterXSize,
                dem_ds.RasterYSize,
                1,
                gdal.GDT_Float32
            )
            dst_ds.SetGeoTransform(dem_ds.GetGeoTransform())
            dst_ds.SetProjection(dem_ds.GetProjection())
            
            # Process
            gdal.DEMProcessing(
                dst_ds,
                dem_ds,
                'slope',
                format='GTiff',
                slopeFormat=slope_type,
                computeEdges=True
            )
            
            dem_ds = None
            dst_ds = None
            
            return {
                'success': True,
                'output_path': output_path,
                'slope_units': 'degrees' if use_degrees else 'percent',
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'output_path': None,
            }
    
    def calculate_aspect(self, dem_path: str, output_path: str) -> Dict[str, Any]:
        """
        Calculate aspect from DEM.
        
        Args:
            dem_path: Input DEM file
            output_path: Output aspect file
        
        Returns:
            Dictionary with aspect calculation results
        """
        if not self.gdal_available:
            return {'success': False, 'error': 'GDAL not available'}
        
        try:
            # Open DEM
            dem_ds = gdal.Open(dem_path, gdal.GA_ReadOnly)
            if dem_ds is None:
                raise ValueError(f"Could not open DEM file: {dem_path}")
            
            # Create output
            driver = gdal.GetDriverByName('GTiff')
            dst_ds = driver.Create(
                output_path,
                dem_ds.RasterXSize,
                dem_ds.RasterYSize,
                1,
                gdal.GDT_Float32
            )
            dst_ds.SetGeoTransform(dem_ds.GetGeoTransform())
            dst_ds.SetProjection(dem_ds.GetProjection())
            
            # Calculate aspect
            gdal.DEMProcessing(
                dst_ds,
                dem_ds,
                'aspect',
                format='GTiff',
                computeEdges=True
            )
            
            dem_ds = None
            dst_ds = None
            
            return {
                'success': True,
                'output_path': output_path,
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'output_path': None,
            }
    
    def extract_raster_values(self, raster_path: str, coordinates: List[dict]) -> Dict[str, Any]:
        """
        Extract raster values at specified coordinates.
        
        Args:
            raster_path: Path to raster file
            coordinates: List of {latitude, longitude} points
        
        Returns:
            Dictionary with extracted values
        """
        if not self.gdal_available:
            return self._fallback_extract_values(raster_path, coordinates)
        
        try:
            # Open raster
            dataset = gdal.Open(raster_path, gdal.GA_ReadOnly)
            if dataset is None:
                raise ValueError(f"Could not open raster file: {raster_path}")
            
            # Get geotransform
            geotransform = dataset.GetGeoTransform()
            if not geotransform or geotransform == (0, 1, 0, 0, 0, 1):
                raise ValueError("Raster is not georeferenced")
            
            # Get projection
            projection = dataset.GetProjection()
            source_srs = osr.SpatialReference()
            if projection:
                source_srs.ImportFromWkt(projection)
            
            # Target SRS (WGS84)
            target_srs = osr.SpatialReference()
            target_srs.ImportFromEPSG(4326)
            
            # Create coordinate transformation if needed
            transform = None
            if projection:
                transform = osr.CoordinateTransformation(target_srs, source_srs)
            
            values = []
            
            for coord in coordinates:
                x, y = coord['longitude'], coord['latitude']
                
                # Transform coordinates if needed
                if transform:
                    point = ogr.Geometry(ogr.wkbPoint)
                    point.AddPoint(x, y)
                    point.Transform(transform)
                    x, y = point.GetX(), point.GetY()
                
                # Convert to pixel coordinates
                pixel_x = int((x - geotransform[0]) / geotransform[1])
                pixel_y = int((y - geotransform[3]) / geotransform[5])
                
                # Check bounds
                if (0 <= pixel_x < dataset.RasterXSize and 
                    0 <= pixel_y < dataset.RasterYSize):
                    
                    # Read value from each band
                    band_values = []
                    for band_num in range(1, dataset.RasterCount + 1):
                        band = dataset.GetRasterBand(band_num)
                        value = band.ReadAsArray(pixel_x, pixel_y, 1, 1)[0, 0]
                        
                        # Handle nodata
                        nodata = band.GetNoDataValue()
                        if nodata is not None and value == nodata:
                            value = None
                        
                        band_values.append(value)
                    
                    values.append({
                        'latitude': coord['latitude'],
                        'longitude': coord['longitude'],
                        'values': band_values,
                        'pixel_x': pixel_x,
                        'pixel_y': pixel_y,
                    })
                else:
                    values.append({
                        'latitude': coord['latitude'],
                        'longitude': coord['longitude'],
                        'values': None,
                        'error': 'Coordinate outside raster bounds',
                    })
            
            dataset = None
            
            return {
                'success': True,
                'values': values,
                'num_bands': dataset.RasterCount if 'dataset' in locals() else 0,
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'values': [],
            }
    
    def _detect_dem_source(self, file_path: str) -> str:
        """Detect DEM source from filename and metadata."""
        filename = os.path.basename(file_path).lower()
        
        if 'srtm' in filename:
            return 'srtm'
        elif 'aster' in filename:
            return 'aster'
        elif 'lidar' in filename or 'las' in filename:
            return 'lidar'
        elif 'alos' in filename:
            return 'alos'
        elif 'copernicus' in filename:
            return 'copernicus'
        elif file_path.endswith('.hgt'):
            return 'srtm'
        else:
            return 'uploaded'
    
    def _find_world_file(self, raster_path: str) -> Optional[str]:
        """Find world file for raster."""
        base, ext = os.path.splitext(raster_path)
        
        # Common world file extensions
        world_extensions = [
            '.wld', '.jgw', '.tfw', '.pgw', '.gfw', '.bpw', '.bmpw',
            '.sdw', '.jpw', '.j2w', '.pmw', '.pgw', '.mgw'
        ]
        
        for world_ext in world_extensions:
            world_file = base + world_ext
            if os.path.exists(world_file):
                return world_file
        
        return None
    
    def _create_vrt_with_world(self, raster_path: str, world_file: str) -> str:
        """Create VRT file with world file georeferencing."""
        # Read world file
        with open(world_file, 'r') as f:
            lines = f.readlines()
        
        if len(lines) >= 6:
            pixel_width = float(lines[0].strip())
            rotation1 = float(lines[1].strip())
            rotation2 = float(lines[2].strip())
            pixel_height = float(lines[3].strip())
            upper_left_x = float(lines[4].strip())
            upper_left_y = float(lines[5].strip())
        else:
            raise ValueError("Invalid world file format")
        
        # Create VRT content
        vrt_content = f"""<VRTDataset rasterXSize="1000" rasterYSize="1000">
  <SRS>EPSG:4326</SRS>
  <GeoTransform>{upper_left_x}, {pixel_width}, {rotation1}, {upper_left_y}, {rotation2}, {pixel_height}</GeoTransform>
  <VRTRasterBand dataType="Byte" band="1">
    <ColorInterp>Gray</ColorInterp>
    <SimpleSource>
      <SourceFilename relativeToVRT="1">{raster_path}</SourceFilename>
      <SourceBand>1</SourceBand>
    </SimpleSource>
  </VRTRasterBand>
</VRTDataset>"""
        
        # Write VRT file
        vrt_path = raster_path + '.vrt'
        with open(vrt_path, 'w') as f:
            f.write(vrt_content)
        
        return vrt_path
    
    def _fallback_dem_processing(self, file_path: str) -> Dict[str, Any]:
        """Fallback DEM processing when GDAL is not available."""
        import struct
        
        try:
            # Very basic HGT file detection
            if file_path.endswith('.hgt'):
                # SRTM HGT files are 1201x1201 or 3601x3601
                file_size = os.path.getsize(file_path)
                
                if file_size == 1201 * 1201 * 2:  # 16-bit signed
                    width = height = 1201
                elif file_size == 3601 * 3601 * 2:
                    width = height = 3601
                else:
                    width = height = int((file_size / 2) ** 0.5)
                
                # Try to get bounds from filename
                # SRTM files are named like N37W123.hgt
                filename = os.path.basename(file_path)
                if len(filename) == 11:  # N37W123.hgt
                    lat_dir = filename[0]
                    lat_val = int(filename[1:3])
                    lon_dir = filename[3]
                    lon_val = int(filename[4:7])
                    
                    if lat_dir == 'S':
                        lat_val = -lat_val
                    if lon_dir == 'W':
                        lon_val = -lon_val
                    
                    bounds = {
                        'west': lon_val,
                        'east': lon_val + 1,
                        'south': lat_val,
                        'north': lat_val + 1,
                    }
                else:
                    bounds = None
                
                return {
                    'success': True,
                    'bounds': bounds,
                    'resolution': 90 if width == 1201 else 30,  # Approximate
                    'metadata': {
                        'width': width,
                        'height': height,
                        'file_size': file_size,
                        'format': 'SRTM HGT',
                    },
                    'source': 'srtm',
                }
            else:
                return {
                    'success': False,
                    'error': 'GDAL required for non-HGT DEM files',
                    'bounds': None,
                    'metadata': {},
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'bounds': None,
                'metadata': {},
            }
    
    def _fallback_raster_processing(self, file_path: str) -> Dict[str, Any]:
        """Fallback raster processing when GDAL is not available."""
        try:
            from PIL import Image
            
            # Try to open with PIL
            with Image.open(file_path) as img:
                width, height = img.size
                bands = len(img.getbands())
                mode = img.mode
                
                metadata = {
                    'width': width,
                    'height': height,
                    'bands': bands,
                    'mode': mode,
                    'format': img.format,
                    'file_size': os.path.getsize(file_path),
                }
            
            return {
                'success': True,
                'bounds': None,
                'metadata': metadata,
                'is_georeferenced': False,
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'bounds': None,
                'metadata': {},
            }
    
    def _fallback_extract_values(self, raster_path: str, coordinates: List[dict]) -> Dict[str, Any]:
        """Fallback value extraction when GDAL is not available."""
        return {
            'success': False,
            'error': 'GDAL required for raster value extraction',
            'values': [],
        }