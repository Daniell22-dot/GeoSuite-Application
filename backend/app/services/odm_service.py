"""
OpenDroneMap (ODM) integration service.
Wraps ODM CLI for photogrammetry processing of drone images.

Supports two modes:
  1. Local subprocess — ODM installed directly on the machine
  2. Docker container — ODM runs inside the opendronemap/odm Docker image
"""
import os
import re
import json
import shutil
import subprocess
import tempfile
from typing import Dict, List, Optional, Callable


class ODMService:
    """Wraps OpenDroneMap for photogrammetry processing."""

    # Valid ODM flags for sane defaults
    DEFAULT_ARGS = [
        "--mesh-octree-depth", "11",
        "--mesh-size", "200000",
        "--min-num-features", "2000",
        "--openskies-path", "odm_orthophoto",
        "--ignore-gcp", "false",
    ]

    def __init__(self, odm_path: str = "run.py", use_docker: bool = False):
        self.odm_path = odm_path
        self.use_docker = use_docker

    def is_available(self) -> bool:
        """Check if ODM is installed and reachable."""
        if self.use_docker:
            return self._check_docker_odm()
        return self._check_local_odm()

    def _check_local_odm(self) -> bool:
        """Check if ODM's run.py exists or 'odm' is on PATH."""
        if os.path.isfile(self.odm_path):
            return True
        try:
            result = subprocess.run(
                ["odm", "--help"],
                capture_output=True, timeout=10
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _check_docker_odm(self) -> bool:
        """Check if the ODM Docker image is available."""
        try:
            result = subprocess.run(
                ["docker", "images", "-q", "opendronemap/odm"],
                capture_output=True, text=True, timeout=10
            )
            return bool(result.stdout.strip())
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def process_survey(
        self,
        images_dir: str,
        output_dir: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        extra_args: Optional[List[str]] = None,
    ) -> Dict:
        """
        Run ODM on a set of drone images.

        Args:
            images_dir: Directory containing drone images (JPEG/TIFF)
            output_dir: Where ODM writes its outputs
            progress_callback: fn(progress_float, message_str) for updates
            extra_args: Additional ODM CLI flags

        Returns:
            Dict with output paths and metadata
        """
        os.makedirs(output_dir, exist_ok=True)

        cmd = self._build_command(images_dir, output_dir, extra_args or [])

        if progress_callback:
            progress_callback(0.0, "Starting ODM processing...")

        try:
            if self.use_docker:
                return self._run_docker(cmd, output_dir, progress_callback)
            else:
                return self._run_local(cmd, output_dir, progress_callback)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output_dir": output_dir,
            }

    def _build_command(self, images_dir: str, output_dir: str,
                       extra_args: List[str]) -> List[str]:
        """Build ODM command line."""
        if self.use_docker:
            cmd = [
                "docker", "run", "--rm",
                "-v", f"{os.path.abspath(images_dir)}:/datasets/images:ro",
                "-v", f"{os.path.abspath(output_dir)}:/datasets/output",
                "opendronemap/odm",
                "--project-path", "/datasets", "output",
                "--source", "/datasets/images",
            ]
        else:
            # Local ODM — try run.py first, then 'odm' CLI
            if os.path.isfile(self.odm_path):
                cmd = ["python", self.odm_path, f"--project-path", os.path.dirname(images_dir), os.path.basename(output_dir)]
            else:
                cmd = [
                    "odm",
                    "--project-path", os.path.dirname(images_dir), os.path.basename(output_dir),
                ]

        cmd.extend(self.DEFAULT_ARGS)
        cmd.extend(extra_args)
        return cmd

    def _run_local(self, cmd: List[str], output_dir: str,
                   progress_callback: Optional[Callable]) -> Dict:
        """Run ODM as a local subprocess with real-time progress parsing."""
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        current_step = ""
        progress_map = {
            "Running ODM": 0.1,
            "Extracting EXIF": 0.15,
            "Running ODM OpenSfM": 0.2,
            "Cell ODM OpenSfM": 0.25,
            "Running ODM MVE": 0.35,
            "Running ODM CMVS": 0.35,
            "Running ODM PMVS": 0.4,
            "Running ODM Meshing": 0.5,
            "Running ODM MVS": 0.6,
            "Running ODM Texturing": 0.65,
            "Running ODM Georeferencing": 0.75,
            "Running ODM Dem": 0.8,
            "Running ODM Orthophoto": 0.9,
            "Running ODM Export": 0.95,
        }

        for line in process.stdout:
            line = line.strip()
            if not line:
                continue

            # Detect step changes
            for step_key, progress_val in progress_map.items():
                if step_key.lower() in line.lower():
                    if step_key != current_step:
                        current_step = step_key
                        if progress_callback:
                            progress_callback(progress_val, step_key)

        process.wait()

        if process.returncode == 0:
            return self._collect_outputs(output_dir, progress_callback)
        else:
            return {
                "success": False,
                "error": f"ODM exited with code {process.returncode}",
                "output_dir": output_dir,
            }

    def _run_docker(self, cmd: List[str], output_dir: str,
                    progress_callback: Optional[Callable]) -> Dict:
        """Run ODM in Docker (no real-time progress, but reliable)."""
        if progress_callback:
            progress_callback(0.1, "Starting ODM Docker container...")

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=14400  # 4 hour timeout
        )

        if result.returncode == 0:
            return self._collect_outputs(output_dir, progress_callback)
        else:
            return {
                "success": False,
                "error": f"ODM Docker failed: {result.stderr[-500:] if result.stderr else 'unknown error'}",
                "output_dir": output_dir,
            }

    def _collect_outputs(self, output_dir: str,
                         progress_callback: Optional[Callable]) -> Dict:
        """Gather ODM output file paths."""
        outputs = {
            "success": True,
            "output_dir": output_dir,
            "files": {},
        }

        # Map expected ODM outputs
        output_map = {
            "orthophoto": "odm_orthophoto",
            "dsm": "odm_dem",
            "dtm": "odm_dem",
            "point_cloud": "odm_georeferencing",
            "mesh": "odm_meshing",
            "texture": "odm_texturing",
            "tiles": "potree_pointcloud",
        }

        for key, subdir in output_map.items():
            subdir_path = os.path.join(output_dir, subdir)
            if os.path.isdir(subdir_path):
                # Find the main output file
                for f in os.listdir(subdir_path):
                    if f.endswith(('.tif', '.tiff', '.laz', '.las', '.ply', '.obj', '.mbtiles')):
                        outputs["files"][key] = os.path.join(subdir_path, f)

        # Also check root for orthophoto
        for f in os.listdir(output_dir):
            if 'orthophoto' in f.lower() and f.endswith(('.tif', '.tiff')):
                outputs["files"]["orthophoto"] = os.path.join(output_dir, f)
            elif f.endswith('.laz') and 'georeferencing' not in f:
                outputs["files"]["point_cloud"] = os.path.join(output_dir, f)

        # Convert orthophoto to Cloud Optimized GeoTIFF (COG)
        orthophoto = outputs["files"].get("orthophoto")
        if orthophoto and orthophoto.endswith(('.tif', '.tiff')):
            cog_path = self._convert_to_cog(orthophoto)
            if cog_path:
                outputs["files"]["cog"] = cog_path

        if progress_callback:
            progress_callback(1.0, "Processing complete")

        return outputs

    def _convert_to_cog(self, input_tif: str) -> Optional[str]:
        """Convert a GeoTIFF to Cloud Optimized GeoTIFF using gdal_translate."""
        try:
            cog_path = input_tif.replace('.tif', '_cog.tif')
            cmd = [
                "gdal_translate",
                input_tif, cog_path,
                "-co", "TILED=YES",
                "-co", "COMPRESS=DEFLATE",
                "-co", "BLOCKXSIZE=256",
                "-co", "BLOCKYSIZE=256",
                "-co", "COPY_SRC_OVERVIEWS=YES",
                "--config", "GDAL_TIFF_OVR_BLOCKSIZE", "256",
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=600)
            if result.returncode == 0 and os.path.exists(cog_path):
                return cog_path
        except Exception:
            pass
        return None

    def get_help(self) -> str:
        """Return ODM help text."""
        cmd = [self.odm_path, "--help"] if os.path.isfile(self.odm_path) else ["odm", "--help"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return result.stdout
        except Exception as e:
            return f"Could not get ODM help: {e}"


class TileService:
    """Generate web-friendly tiles from processed drone outputs."""

    @staticmethod
    def generate_pmtiles(input_tif: str, output_pmtiles: str,
                         max_zoom: int = 18) -> Optional[str]:
        """Convert a COG to PMTiles for browser rendering."""
        try:
            cmd = [
                "tippecanoe",
                "-o", output_pmtiles,
                "--maximum-zoom", str(max_zoom),
                "--generate-xy-layer-name", "drone",
                "--no-tile-size-limit",
                input_tif,
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=3600)
            if result.returncode == 0 and os.path.exists(output_pmtiles):
                return output_pmtiles
        except Exception:
            pass
        return None

    @staticmethod
    def generate_mbtiles(input_tif: str, output_mbtiles: str,
                         max_zoom: int = 18) -> Optional[str]:
        """Generate MBTiles from a COG."""
        try:
            cmd = [
                "tippecanoe",
                "-o", output_mbtiles,
                "--maximum-zoom", str(max_zoom),
                "--generate-xy-layer-name", "drone",
                input_tif,
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=3600)
            if result.returncode == 0 and os.path.exists(output_mbtiles):
                return output_mbtiles
        except Exception:
            pass
        return None
