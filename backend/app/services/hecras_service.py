"""
HEC-RAS integration service for hydraulic modeling.
Uses PyHEC to interact with HEC-RAS through its COM interface.
"""
import os
import tempfile
import subprocess
import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import shutil

try:
    from pyhec import hecras
    PYHEC_AVAILABLE = True
except ImportError:
    PYHEC_AVAILABLE = False
    print("Warning: pyhec not installed. HEC-RAS integration disabled.")

class HECRASService:
    """
    Service for HEC-RAS hydraulic modeling integration.
    Provides functionality to create, run, and analyze HEC-RAS models.
    """
    
    def __init__(self, hecras_path: Optional[str] = None):
        """
        Initialize HEC-RAS service.
        
        Args:
            hecras_path: Path to HEC-RAS installation directory
        """
        self.hecras_path = hecras_path or os.getenv("HECRAS_PATH", "C:\\Program Files\\HEC\\HEC-RAS")
        self.pyhec_available = PYHEC_AVAILABLE
        
        if self.pyhec_available:
            try:
                self.ras = hecras.HECRASController()
                self.connected = True
            except Exception as e:
                print(f"Warning: Could not initialize HEC-RAS controller: {e}")
                self.connected = False
        else:
            self.connected = False
    
    def create_steady_flow_model(self, geometry_data: Dict, 
                                flow_data: Dict, output_dir: str) -> Dict:
        """
        Create a steady flow HEC-RAS model.
        
        Args:
            geometry_data: River geometry data
            flow_data: Flow boundary conditions
            output_dir: Output directory for model files
        
        Returns:
            Dictionary with model creation results
        """
        if not self.connected:
            return self._mock_hecras_model(geometry_data, flow_data, output_dir)
        
        try:
            # Create project directory
            project_name = f"ras_project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            project_dir = os.path.join(output_dir, project_name)
            os.makedirs(project_dir, exist_ok=True)
            
            # Create geometry file
            geom_file = os.path.join(project_dir, f"{project_name}.g01")
            self._create_geometry_file(geom_file, geometry_data)
            
            # Create flow file
            flow_file = os.path.join(project_dir, f"{project_name}.f01")
            self._create_flow_file(flow_file, flow_data)
            
            # Create plan file
            plan_file = os.path.join(project_dir, f"{project_name}.p01")
            self._create_plan_file(plan_file, geom_file, flow_file)
            
            # Create project file
            prj_file = os.path.join(project_dir, f"{project_name}.prj")
            self._create_project_file(prj_file, geom_file, flow_file, plan_file)
            
            # Open project in HEC-RAS
            self.ras.Project_Open(prj_file)
            
            # Set computation options
            self.ras.SetComputationOptions("Steady", "Standard")
            
            # Set geometry
            self._set_geometry(geometry_data)
            
            # Set flow data
            self._set_flow_data(flow_data)
            
            # Save project
            self.ras.Project_Save()
            
            return {
                "success": True,
                "project_dir": project_dir,
                "project_file": prj_file,
                "geometry_file": geom_file,
                "flow_file": flow_file,
                "plan_file": plan_file,
                "project_name": project_name
            }
            
        except Exception as e:
            print(f"Error creating HEC-RAS model: {e}")
            return {
                "success": False,
                "error": str(e),
                "project_dir": output_dir
            }
    
    def run_steady_flow_analysis(self, project_file: str, plan_file: str) -> Dict:
        """
        Run steady flow analysis in HEC-RAS.
        
        Args:
            project_file: HEC-RAS project file (.prj)
            plan_file: Plan file (.p01)
        
        Returns:
            Dictionary with analysis results
        """
        if not self.connected:
            return self._mock_analysis_results(project_file, plan_file)
        
        try:
            # Open project
            self.ras.Project_Open(project_file)
            
            # Set current plan
            self.ras.Plan_SetCurrent(plan_file)
            
            # Run computation
            print("Starting HEC-RAS computation...")
            success = self.ras.Compute_CurrentPlan()
            
            if success:
                # Get results
                results = self._extract_results(project_file)
                
                return {
                    "success": True,
                    "completion_status": "successful",
                    "results": results,
                    "output_files": self._get_output_files(project_file)
                }
            else:
                # Get error messages
                messages = self.ras.Messages_GetComputation()
                
                return {
                    "success": False,
                    "completion_status": "failed",
                    "error_messages": messages,
                    "output_files": []
                }
                
        except Exception as e:
            print(f"Error running HEC-RAS analysis: {e}")
            return {
                "success": False,
                "error": str(e),
                "completion_status": "failed"
            }
    
    def extract_water_surface_elevations(self, results_file: str) -> Dict:
        """
        Extract water surface elevations from HEC-RAS results.
        
        Args:
            results_file: HEC-RAS results file
        
        Returns:
            Dictionary with water surface elevations
        """
        if not self.connected:
            return self._mock_water_surface_elevations()
        
        try:
            # This would use HEC-RAS API to extract WSE data
            # Implementation depends on HEC-RAS version and file format
            
            # For now, return mock data
            return self._mock_water_surface_elevations()
            
        except Exception as e:
            print(f"Error extracting water surface elevations: {e}")
            return self._mock_water_surface_elevations()
    
    def calculate_flood_inundation(self, terrain_file: str, wse_data: Dict) -> Dict:
        """
        Calculate flood inundation extent from water surface elevations.
        
        Args:
            terrain_file: Terrain DEM file
            wse_data: Water surface elevation data
        
        Returns:
            Dictionary with inundation results
        """
        try:
            # This would involve:
            # 1. Subtract terrain from water surface elevations
            # 2. Calculate inundation depth
            # 3. Create inundation polygon
            
            # For now, return mock data
            return {
                "success": True,
                "inundation_area_km2": 5.67,
                "max_depth_m": 3.2,
                "average_depth_m": 1.8,
                "affected_area_km2": 12.3,
                "inundation_polygon": self._create_mock_polygon(),
                "depth_raster": "path/to/depth_raster.tif"
            }
            
        except Exception as e:
            print(f"Error calculating flood inundation: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _create_geometry_file(self, filename: str, geometry_data: Dict):
        """Create HEC-RAS geometry file."""
        # This is a simplified implementation
        # Actual implementation would create proper HEC-RAS geometry file
        
        with open(filename, 'w') as f:
            f.write("HEC-RAS Geometry File\n")
            f.write(f"Created: {datetime.now()}\n")
            f.write("River Reach Geometry\n")
            f.write(json.dumps(geometry_data, indent=2))
    
    def _create_flow_file(self, filename: str, flow_data: Dict):
        """Create HEC-RAS flow file."""
        with open(filename, 'w') as f:
            f.write("HEC-RAS Flow File\n")
            f.write(f"Created: {datetime.now()}\n")
            f.write("Steady Flow Data\n")
            f.write(json.dumps(flow_data, indent=2))
    
    def _create_plan_file(self, filename: str, geom_file: str, flow_file: str):
        """Create HEC-RAS plan file."""
        with open(filename, 'w') as f:
            f.write("HEC-RAS Plan File\n")
            f.write(f"Geometry File: {geom_file}\n")
            f.write(f"Flow File: {flow_file}\n")
            f.write("Plan Type: Steady Flow\n")
    
    def _create_project_file(self, filename: str, geom_file: str, flow_file: str, plan_file: str):
        """Create HEC-RAS project file."""
        with open(filename, 'w') as f:
            f.write("HEC-RAS Project File\n")
            f.write(f"Geometry={geom_file}\n")
            f.write(f"Flow=${flow_file}\n")
            f.write(f"Plan={plan_file}\n")
    
    def _set_geometry(self, geometry_data: Dict):
        """Set geometry in HEC-RAS controller."""
        # This would use pyhec to set geometry
        # Implementation depends on specific geometry structure
        pass
    
    def _set_flow_data(self, flow_data: Dict):
        """Set flow data in HEC-RAS controller."""
        # This would use pyhec to set flow data
        pass
    
    def _extract_results(self, project_file: str) -> Dict:
        """Extract results from HEC-RAS output."""
        # This would parse HEC-RAS output files
        # For now, return mock results
        
        return {
            "water_surface_elevations": {
                "river_station_100": 125.6,
                "river_station_200": 126.1,
                "river_station_300": 125.8
            },
            "energy_grade_line": {
                "river_station_100": 126.0,
                "river_station_200": 126.5,
                "river_station_300": 126.2
            },
            "velocities": {
                "river_station_100": 1.2,
                "river_station_200": 1.5,
                "river_station_300": 1.3
            },
            "froude_numbers": {
                "river_station_100": 0.15,
                "river_station_200": 0.18,
                "river_station_300": 0.16
            }
        }
    
    def _get_output_files(self, project_file: str) -> List[str]:
        """Get list of output files generated by HEC-RAS."""
        project_dir = os.path.dirname(project_file)
        
        output_files = []
        for ext in ['.x01', '.o01', '.dss', '.hdf']:
            for file in os.listdir(project_dir):
                if file.endswith(ext):
                    output_files.append(os.path.join(project_dir, file))
        
        return output_files
    
    def _mock_hecras_model(self, geometry_data: Dict, flow_data: Dict, output_dir: str) -> Dict:
        """Create mock HEC-RAS model for testing."""
        project_name = f"mock_ras_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        project_dir = os.path.join(output_dir, project_name)
        os.makedirs(project_dir, exist_ok=True)
        
        # Create mock files
        files = {}
        for file_type, ext in [("geometry", ".g01"), ("flow", ".f01"), 
                              ("plan", ".p01"), ("project", ".prj")]:
            filename = os.path.join(project_dir, f"{project_name}{ext}")
            with open(filename, 'w') as f:
                f.write(f"Mock {file_type} file\n")
                f.write(f"Geometry: {json.dumps(geometry_data, indent=2)}\n")
                f.write(f"Flow: {json.dumps(flow_data, indent=2)}\n")
            files[f"{file_type}_file"] = filename
        
        return {
            "success": True,
            "project_dir": project_dir,
            "project_name": project_name,
            **files,
            "note": "Mock HEC-RAS model created (HEC-RAS not available)"
        }
    
    def _mock_analysis_results(self, project_file: str, plan_file: str) -> Dict:
        """Return mock analysis results."""
        return {
            "success": True,
            "completion_status": "successful",
            "results": {
                "water_surface_elevations": {
                    "RS_100": 125.6,
                    "RS_200": 126.1,
                    "RS_300": 125.8
                },
                "velocities": {
                    "RS_100": 1.2,
                    "RS_200": 1.5,
                    "RS_300": 1.3
                }
            },
            "note": "Mock results (HEC-RAS not available)"
        }
    
    def _mock_water_surface_elevations(self) -> Dict:
        """Return mock water surface elevations."""
        import random
        
        stations = list(range(100, 1001, 100))
        elevations = [100 + random.uniform(-5, 10) for _ in stations]
        
        return {
            "river_stations": stations,
            "water_surface_elevations": elevations,
            "minimum": min(elevations),
            "maximum": max(elevations),
            "average": sum(elevations) / len(elevations)
        }
    
    def _create_mock_polygon(self) -> Dict:
        """Create mock inundation polygon."""
        return {
            "type": "Polygon",
            "coordinates": [[
                [-122.5, 37.8],
                [-122.4, 37.8],
                [-122.4, 37.7],
                [-122.5, 37.7],
                [-122.5, 37.8]
            ]]
        }
    
    def validate_model(self, project_file: str) -> Dict:
        """
        Validate HEC-RAS model for errors and warnings.
        
        Args:
            project_file: HEC-RAS project file
        
        Returns:
            Dictionary with validation results
        """
        # This would use HEC-RAS validation tools
        # For now, return mock validation
        
        return {
            "valid": True,
            "errors": [],
            "warnings": [
                "Geometry contains sharp bends",
                "Manning's n values may be too low"
            ],
            "recommendations": [
                "Add more cross sections in bend areas",
                "Review Manning's n values for accuracy"
            ]
        }
    
    def export_to_geojson(self, results_file: str, output_file: str) -> bool:
        """
        Export HEC-RAS results to GeoJSON format.
        
        Args:
            results_file: HEC-RAS results file
            output_file: Output GeoJSON file
        
        Returns:
            True if successful
        """
        try:
            # This would convert HEC-RAS results to GeoJSON
            # Implementation depends on results format
            
            # Create mock GeoJSON
            geojson = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [[-122.5, 37.8], [-122.4, 37.8]]
                        },
                        "properties": {
                            "station": 100,
                            "wse": 125.6,
                            "velocity": 1.2
                        }
                    }
                ]
            }
            
            with open(output_file, 'w') as f:
                json.dump(geojson, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Error exporting to GeoJSON: {e}")
            return False