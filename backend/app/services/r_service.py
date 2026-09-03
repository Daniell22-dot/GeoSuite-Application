"""
R integration service for statistical hydrology and advanced analysis.
Uses rpy2 to call R functions from Python.
"""
import tempfile
import os
import sys
import json
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
from pathlib import Path
import subprocess

# Set R_HOME if needed — auto-detect across platforms
if 'R_HOME' not in os.environ:
    _r_candidates = []
    if sys.platform == 'win32':
        import glob
        _r_candidates = glob.glob(r'C:\Program Files\R\R-*')
    else:
        _r_candidates = ['/usr/lib/R', '/usr/local/lib/R', '/opt/R']

    for _candidate in _r_candidates:
        if os.path.exists(_candidate):
            os.environ['R_HOME'] = _candidate
            break

class RService:
    """
    Service for R integration.
    Provides access to R's hydrological and statistical packages.
    """
    
    def __init__(self):
        self.R_AVAILABLE = False
        
        try:
            # First, try to import rpy2 and activate converters
            import rpy2.robjects as ro
            from rpy2.robjects import pandas2ri, numpy2ri
            from rpy2.robjects.packages import importr, isinstalled
            
            # Activate automatic converters done  once globally
            pandas2ri.activate()
            numpy2ri.activate()
            
            # Store references
            self.ro = ro
            self.importr = importr
            self.isinstalled = isinstalled
            
            self.R_AVAILABLE = True
            
            # Import common R packages
            self.base = importr("base")
            self.stats = importr("stats")
            self.graphics = importr("graphics")
            self.utils = importr("utils")
            
            # Import hydrological packages if available
            self.hydro = self._safe_import("hydroGOF")
            self.topmodel = self._safe_import("topmodel")
            self.hydrostats = self._safe_import("hydrostats")
            self.lmom = self._safe_import("lmom")
            self.nsRFA = self._safe_import("nsRFA")
            
        except ImportError as e:
            print(f"Warning: rpy2 not installed or R not configured properly: {e}")
            print("R integration disabled. Using Python fallback methods.")
        except Exception as e:
            print(f"Warning: Error initializing R: {e}")
            print("R integration partially disabled. Some features may use fallback methods.")
    
    def _safe_import(self, package_name: str):
        """Safely import an R package."""
        if not self.R_AVAILABLE:
            return None
        
        try:
            if self.isinstalled(package_name):
                return self.importr(package_name)
            else:
                print(f"Warning: R package '{package_name}' is not installed.")
                return None
        except Exception as e:
            print(f"Warning: Could not import R package '{package_name}': {e}")
            return None
    
    def calculate_flow_duration_curve(self, flow_data: List[float]) -> Dict:
        """
        Calculate flow duration curve using R's hydrostats package.
        
        Args:
            flow_data: List of flow values (m³/s)
        
        Returns:
            Dictionary with FDC data
        """
        if not self.R_AVAILABLE or self.hydrostats is None:
            return self._fallback_fdc(flow_data)
        
        try:
            # Convert Python list to R vector
            r_flow = self.ro.FloatVector(flow_data)
            
            # Calculate FDC
            fdc_result = self.hydrostats.FDC(r_flow)
            
            # Extract results
            exceedance = [float(x) for x in fdc_result.rx2("Exceedance")]
            flow = [float(x) for x in fdc_result.rx2("Flow")]
            
            # Calculate statistics
            flow_data_array = np.array(flow_data)
            stats = {
                "mean_flow": float(np.mean(flow_data_array)),
                "median_flow": float(np.median(flow_data_array)),
                "max_flow": float(np.max(flow_data_array)),
                "min_flow": float(np.min(flow_data_array)),
                "q10": float(np.percentile(flow_data_array, 90)),  # Flow exceeded 10% of time
                "q50": float(np.percentile(flow_data_array, 50)),  # Flow exceeded 50% of time
                "q90": float(np.percentile(flow_data_array, 10)),  # Flow exceeded 90% of time
            }
            
            return {
                "exceedance_probability": exceedance,
                "flow_values": flow,
                "statistics": stats
            }
            
        except Exception as e:
            print(f"Error calculating FDC with R: {e}")
            return self._fallback_fdc(flow_data)
    
    def fit_distribution(self, data: List[float], distribution: str = "gev") -> Dict:
        """
        Fit a statistical distribution to data using R's lmom package.
        
        Args:
            data: List of values (e.g., annual maximum flows)
            distribution: Distribution type (gev, gumbel, gamma, lognormal, etc.)
        
        Returns:
            Dictionary with fitted distribution parameters
        """
        if not self.R_AVAILABLE or self.lmom is None:
            return self._fallback_distribution(data, distribution)
        
        try:
            r_data = self.ro.FloatVector(data)
            
            # Calculate L-moments
            lmoments = self.lmom.samlmu(r_data)
            
            # Fit distribution based on type
            distribution_lower = distribution.lower()
            if distribution_lower == "gev":
                params = self.lmom.pelgev(lmoments)
            elif distribution_lower == "gumbel":
                params = self.lmom.pelgum(lmoments)
            elif distribution_lower == "gamma":
                params = self.lmom.pelgam(lmoments)
            elif distribution_lower == "lognormal":
                params = self.lmom.pelln3(lmoments)
            else:
                print(f"Unsupported distribution: {distribution}, using GEV as default")
                params = self.lmom.pelgev(lmoments)
                distribution_lower = "gev"
            
            # Convert parameters to Python
            param_dict = {}
            param_names = ["location", "scale", "shape"]
            for i, name in enumerate(param_names):
                if i < len(params):
                    param_dict[name] = float(params[i])
                else:
                    param_dict[name] = None
            
            # Calculate goodness of fit
            quantiles = self.ro.FloatVector([0.01, 0.1, 0.5, 0.9, 0.99])
            fitted = self.lmom.quagev(quantiles, params) if distribution_lower == "gev" else None
            
            quantile_dict = {}
            if fitted is not None:
                quantile_labels = ["q1", "q10", "q50", "q90", "q99"]
                for i, label in enumerate(quantile_labels):
                    if i < len(fitted):
                        quantile_dict[label] = float(fitted[i])
            
            return {
                "distribution": distribution_lower,
                "parameters": param_dict,
                "lmoments": [float(x) for x in lmoments],
                "quantiles": quantile_dict
            }
            
        except Exception as e:
            print(f"Error fitting distribution with R: {e}")
            return self._fallback_distribution(data, distribution)
    
    def calculate_unit_hydrograph(self, rainfall: List[float], runoff: List[float],
                                 method: str = "snyder") -> Dict:
        """
        Calculate unit hydrograph using R's topmodel or custom methods.
        
        Args:
            rainfall: Rainfall time series (mm)
            runoff: Runoff time series (mm)
            method: Method to use (snyder, scs, clark)
        
        Returns:
            Dictionary with unit hydrograph data
        """
        if not self.R_AVAILABLE:
            return self._fallback_unit_hydrograph(rainfall, runoff, method)
        
        try:
            # Convert to numpy arrays for easier manipulation
            rainfall_array = np.array(rainfall)
            runoff_array = np.array(runoff)
            
            # Different methods
            method_lower = method.lower()
            if method_lower == "snyder":
                # Snyder's synthetic unit hydrograph
                # This is simplified - actual implementation would use proper R functions
                if self.topmodel is not None:
                    # Use topmodel package if available
                    r_rain = self.ro.FloatVector(rainfall)
                    r_runoff = self.ro.FloatVector(runoff)
                    # Placeholder for actual topmodel usage
                    pass
                
                # Simplified Snyder's method
                n = len(rainfall_array)
                lag_time = 0.47 * (n ** 0.38) if n > 0 else 0  # Snyder's lag equation
                peak_time = lag_time * 0.6
                peak_flow = 2.08 / peak_time if peak_time > 0 else 0
                
                # Generate synthetic hydrograph
                time_to_peak = int(max(1, peak_time))
                time_base = int(max(3, 2.67 * peak_time))
                
                times = list(range(time_base))
                flows = []
                
                for t in times:
                    if t <= time_to_peak:
                        flows.append(peak_flow * (t / time_to_peak))
                    else:
                        decay = (t - time_to_peak) / (time_base - time_to_peak)
                        flows.append(peak_flow * np.exp(-decay))
                
                return {
                    "method": "snyder",
                    "lag_time": float(lag_time),
                    "peak_time": float(peak_time),
                    "peak_flow": float(peak_flow),
                    "time_base": time_base,
                    "times": times,
                    "flows": [float(f) for f in flows]
                }
            else:
                # Default to simple deconvolution
                return self._simple_deconvolution(rainfall, runoff)
                
        except Exception as e:
            print(f"Error calculating unit hydrograph: {e}")
            return self._fallback_unit_hydrograph(rainfall, runoff, method)
    
    def perform_hyetograph_analysis(self, rainfall_data: List[Dict]) -> Dict:
        """
        Analyze rainfall hyetograph for intensity-duration-frequency.
        
        Args:
            rainfall_data: List of {timestamp, rainfall_mm} dictionaries
        
        Returns:
            Dictionary with IDF analysis results
        """
        if not self.R_AVAILABLE:
            return self._fallback_idf_analysis(rainfall_data)
        
        try:
            # Extract rainfall values
            rainfall = [d.get("rainfall_mm", 0) for d in rainfall_data]
            rainfall_array = np.array(rainfall)
            
            # Calculate maximum intensities for different durations
            durations = [5, 10, 15, 30, 60, 120, 180, 360, 720, 1440]  # minutes
            max_intensities = {}
            
            for duration in durations:
                # Calculate rolling maximum for duration
                if len(rainfall_array) >= duration:
                    # Use convolution to find maximum rolling sum
                    kernel = np.ones(duration)
                    rolling_sum = np.convolve(rainfall_array, kernel, mode='valid')
                    if len(rolling_sum) > 0:
                        max_rain = np.max(rolling_sum)
                        intensity = max_rain / (duration/60)  # Convert to mm/hr
                        max_intensities[str(duration)] = float(intensity)
            
            # Fit IDF curve if we have enough data points
            durations_num = [float(d) for d in max_intensities.keys()]
            intensities = list(max_intensities.values())
            
            idf_equation = "Insufficient data"
            k = m = None
            
            if len(durations_num) > 2:
                # Log-log regression for IDF parameters
                log_d = np.log(durations_num)
                log_i = np.log(intensities)
                
                try:
                    # Linear regression in log space
                    coeffs = np.polyfit(log_d, log_i, 1)
                    
                    # IDF equation: i = k / d^m
                    k = np.exp(coeffs[1])
                    m = -coeffs[0]
                    
                    idf_equation = f"i = {k:.2f} / d^{m:.2f}"
                except:
                    idf_equation = "Regression failed"
            
            return {
                "durations": list(max_intensities.keys()),
                "max_intensities": max_intensities,
                "idf_equation": idf_equation,
                "parameters": {
                    "k": float(k) if k is not None else None,
                    "m": float(m) if m is not None else None
                }
            }
            
        except Exception as e:
            print(f"Error in hyetograph analysis: {e}")
            return self._fallback_idf_analysis(rainfall_data)
    
    def calculate_nash_sutcliffe(self, observed: List[float], simulated: List[float]) -> float:
        """
        Calculate Nash-Sutcliffe efficiency coefficient.
        
        Args:
            observed: Observed values
            simulated: Simulated values
        
        Returns:
            Nash-Sutcliffe efficiency coefficient
        """
        if not self.R_AVAILABLE or self.hydro is None:
            return self._calculate_nse_python(observed, simulated)
        
        try:
            r_obs = self.ro.FloatVector(observed)
            r_sim = self.ro.FloatVector(simulated)
            
            nse = self.hydro.NSE(r_sim, r_obs)
            return float(nse[0])
            
        except Exception as e:
            print(f"Error calculating NSE with R: {e}")
            return self._calculate_nse_python(observed, simulated)
    
    def _fallback_fdc(self, flow_data: List[float]) -> Dict:
        """Fallback FDC calculation in Python."""
        flow_array = np.array(flow_data)
        sorted_flow = np.sort(flow_array)[::-1]  # Descending order
        n = len(sorted_flow)
        exceedance = [(i + 1) / (n + 1) * 100 for i in range(n)]
        
        return {
            "exceedance_probability": exceedance,
            "flow_values": sorted_flow.tolist(),
            "statistics": {
                "mean_flow": float(np.mean(flow_array)),
                "median_flow": float(np.median(flow_array)),
                "max_flow": float(np.max(flow_array)),
                "min_flow": float(np.min(flow_array)),
                "q10": float(np.percentile(flow_array, 90)),
                "q50": float(np.percentile(flow_array, 50)),
                "q90": float(np.percentile(flow_array, 10))
            }
        }
    
    def _fallback_distribution(self, data: List[float], distribution: str) -> Dict:
        """Fallback distribution fitting in Python."""
        try:
            from scipy import stats
        except ImportError:
            # Very basic fallback if scipy is not available
            data_array = np.array(data)
            return {
                "distribution": "empirical",
                "parameters": {
                    "mean": float(np.mean(data_array)),
                    "std": float(np.std(data_array)),
                    "location": None,
                    "scale": None,
                    "shape": None
                },
                "lmoments": [],
                "quantiles": {}
            }
        
        data_array = np.array(data)
        distribution_lower = distribution.lower()
        
        try:
            if distribution_lower == "gev":
                params = stats.genextreme.fit(data_array)
                dist_name = "gev"
                param_dict = {
                    "location": float(params[1]),
                    "scale": float(params[2]),
                    "shape": float(params[0])
                }
            elif distribution_lower == "gumbel":
                params = stats.gumbel_r.fit(data_array)
                dist_name = "gumbel"
                param_dict = {
                    "location": float(params[0]),
                    "scale": float(params[1]),
                    "shape": None
                }
            elif distribution_lower == "gamma":
                params = stats.gamma.fit(data_array)
                dist_name = "gamma"
                param_dict = {
                    "location": 0.0,
                    "scale": float(params[1]),
                    "shape": float(params[0])
                }
            elif distribution_lower == "lognormal":
                params = stats.lognorm.fit(data_array)
                dist_name = "lognormal"
                param_dict = {
                    "location": 0.0,
                    "scale": float(params[2]),
                    "shape": float(params[0])
                }
            else:
                # Default to normal
                params = stats.norm.fit(data_array)
                dist_name = "normal"
                param_dict = {
                    "location": float(params[0]),
                    "scale": float(params[1]),
                    "shape": None
                }
            
            return {
                "distribution": dist_name,
                "parameters": param_dict,
                "lmoments": [],
                "quantiles": {}
            }
        except:
            # Very basic fallback
            return {
                "distribution": "empirical",
                "parameters": {
                    "mean": float(np.mean(data_array)),
                    "std": float(np.std(data_array)),
                    "location": None,
                    "scale": None,
                    "shape": None
                },
                "lmoments": [],
                "quantiles": {}
            }
    
    def _fallback_unit_hydrograph(self, rainfall: List[float], runoff: List[float],
                                 method: str) -> Dict:
        """Fallback unit hydrograph calculation."""
        # Simple deconvolution
        return self._simple_deconvolution(rainfall, runoff)
    
    def _simple_deconvolution(self, rainfall: List[float], runoff: List[float]) -> Dict:
        """Simple deconvolution to estimate unit hydrograph."""
        # This is a very simplified implementation
        rainfall_array = np.array(rainfall)
        runoff_array = np.array(runoff)
        
        # Normalize rainfall
        total_rain = np.sum(rainfall_array)
        if total_rain > 0:
            effective_rain = rainfall_array * 0.8  # Simple runoff coefficient
        else:
            effective_rain = rainfall_array
        
        # Simple estimation (would need proper deconvolution)
        n = min(len(rainfall_array), len(runoff_array))
        uhg = []
        
        for i in range(n):
            if effective_rain[i] > 0:
                uhg.append(runoff_array[i] / effective_rain[i])
            else:
                uhg.append(0)
        
        # Smooth the UHG if we have enough points
        if len(uhg) > 3:
            kernel = np.ones(3) / 3
            smoothed = np.convolve(uhg, kernel, mode='valid')
            # Pad to original length
            pad_left = len(uhg) - len(smoothed)
            if pad_left > 0:
                smoothed = np.pad(smoothed, (pad_left//2, pad_left - pad_left//2), 'edge')
            else:
                smoothed = uhg
        else:
            smoothed = uhg
        
        return {
            "method": "simple_deconvolution",
            "unit_hydrograph": [float(x) for x in smoothed],
            "time_steps": list(range(len(smoothed)))
        }
    
    def _fallback_idf_analysis(self, rainfall_data: List[Dict]) -> Dict:
        """Fallback IDF analysis in Python."""
        # Extract rainfall values
        rainfall = [d.get("rainfall_mm", 0) for d in rainfall_data]
        rainfall_array = np.array(rainfall)
        
        # Simple analysis
        durations = [5, 10, 15, 30, 60]
        intensities = {}
        
        for duration in durations:
            if len(rainfall_array) >= duration:
                # Use convolution to find maximum rolling sum
                kernel = np.ones(duration)
                rolling_sum = np.convolve(rainfall_array, kernel, mode='valid')
                if len(rolling_sum) > 0:
                    max_rain = np.max(rolling_sum)
                    intensity = max_rain / (duration/60)  # mm/hr
                    intensities[str(duration)] = float(intensity)
        
        return {
            "durations": list(intensities.keys()),
            "max_intensities": intensities,
            "idf_equation": "i = k / d^m (parameters not calculated)",
            "parameters": {}
        }
    
    def _calculate_nse_python(self, observed: List[float], simulated: List[float]) -> float:
        """Calculate Nash-Sutcliffe efficiency in Python."""
        obs_array = np.array(observed)
        sim_array = np.array(simulated)
        
        # Ensure arrays have same length
        n = min(len(obs_array), len(sim_array))
        obs_array = obs_array[:n]
        sim_array = sim_array[:n]
        
        obs_mean = np.mean(obs_array)
        numerator = np.sum((obs_array - sim_array) ** 2)
        denominator = np.sum((obs_array - obs_mean) ** 2)
        
        if denominator == 0:
            if numerator == 0:
                return 1.0  # Perfect fit
            else:
                return float('-inf')  # Undefined
        
        nse = 1 - (numerator / denominator)
        return float(nse)