/**
 * API service for GeoSuite frontend.
 * Handles all API calls with authentication and error handling.
 */
import axios from 'axios';

// API configuration
const API_CONFIG = {
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
  },
};

// Create axios instance
const api = axios.create(API_CONFIG);

// Request interceptor for adding auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle specific error cases
    if (error.response) {
      const { status, data } = error.response;
      
      switch (status) {
        case 401:
          // Unauthorized - clear token and redirect to home (no /login route exists)
          localStorage.removeItem('auth_token');
          localStorage.removeItem('user');
          window.location.href = '/home';
          break;
          
        case 403:
          // Forbidden - show access denied message
          console.error('Access denied:', data.detail || 'You do not have permission');
          break;
          
        case 404:
          // Not found
          console.error('Resource not found:', error.config.url);
          break;
          
        case 429:
          // Rate limited
          console.error('Rate limited:', data.detail || 'Too many requests');
          break;
          
        case 500:
          // Server error
          console.error('Server error:', data.detail || 'Internal server error');
          break;
          
        default:
          console.error('API error:', data.detail || 'Unknown error');
      }
    } else if (error.request) {
      // Network error
      console.error('Network error:', error.message);
    } else {
      // Request configuration error
      console.error('Request error:', error.message);
    }
    
    return Promise.reject(error);
  }
);

/**
 * GPS API functions
 */
export const gpsApi = {
  // Upload GPX file
  uploadGpx: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/api/v1/gps/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
  
  // Correct elevation
  correctElevation: async (gpxData, demSource = 'srtm') => {
    const response = await api.post('/api/v1/gps/correct-elevation', {
      gpx_data: gpxData,
      dem_source: demSource,
    });
    return response.data;
  },
  
  // Convert GPX to other formats
  convertGpx: async (gpxData, targetFormat) => {
    const response = await api.post('/api/v1/gps/convert', {
      gpx_data: gpxData,
      format: targetFormat,
    });
    return response.data;
  },
  
  // Get elevation profile
  getElevationProfile: async (coordinates) => {
    const response = await api.post('/api/v1/gps/elevation-profile', {
      coordinates,
    });
    return response.data;
  },
  
  // Batch process GPX files
  batchProcessGpx: async (files) => {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });
    
    const response = await api.post('/api/v1/gps/batch-process', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};

/**
 * Marine Charts API functions
 */
export const marineApi = {
  // Upload marine chart
  uploadChart: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/api/v1/marine/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
  
  // Process KAP file
  processKapFile: async (filePath) => {
    const response = await api.post('/api/v1/marine/process-kap', {
      file_path: filePath,
    });
    return response.data;
  },
  
  // Process CAD file
  processCadFile: async (filePath) => {
    const response = await api.post('/api/v1/marine/process-cad', {
      file_path: filePath,
    });
    return response.data;
  },
  
  // Get chart tiles
  getChartTiles: async (chartId, zoom, x, y) => {
    const response = await api.get(`/api/v1/marine/tiles/${chartId}/${zoom}/${x}/${y}`);
    return response.data;
  },
  
  // Merge charts
  mergeCharts: async (chartPaths, outputFormat = 'geotiff') => {
    const response = await api.post('/api/v1/marine/merge', {
      chart_paths: chartPaths,
      output_format: outputFormat,
    });
    return response.data;
  },
  
  // Extract soundings
  extractSoundings: async (chartData, depthRange = [0, 100]) => {
    const response = await api.post('/api/v1/marine/extract-soundings', {
      chart_data: chartData,
      depth_range: depthRange,
    });
    return response.data;
  },
};

/**
 * Watershed Analysis API functions
 */
export const watershedApi = {
  // Upload DEM file
  uploadDem: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/api/v1/watershed/upload-dem', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
  
  // Delineate watershed
  delineateWatershed: async (demId, pourPoint) => {
    const response = await api.post('/api/v1/watershed/delineate', {
      dem_id: demId,
      pour_point: pourPoint,
    });
    return response.data;
  },
  
  // Extract stream network
  extractStreams: async (demId, threshold = 1000) => {
    const response = await api.post('/api/v1/watershed/extract-streams', {
      dem_id: demId,
      threshold,
    });
    return response.data;
  },
  
  // Calculate flow path
  calculateFlowPath: async (demId, startPoint) => {
    const response = await api.post('/api/v1/watershed/flow-path', {
      dem_id: demId,
      start_point: startPoint,
    });
    return response.data;
  },
  
  // Calculate flow accumulation
  calculateFlowAccumulation: async (demId) => {
    const response = await api.post('/api/v1/watershed/flow-accumulation', {
      dem_id: demId,
    });
    return response.data;
  },
  
  // Run R analysis
  runRAnalysis: async (analysisType, data) => {
    const response = await api.post('/api/v1/watershed/r-analysis', {
      analysis_type: analysisType,
      data,
    });
    return response.data;
  },
};

/**
 * HEC-RAS API functions
 */
export const hecrasApi = {
  // Create HEC-RAS model
  createModel: async (modelData) => {
    const response = await api.post('/api/v1/hecras/create', modelData);
    return response.data;
  },
  
  // Run simulation
  runSimulation: async (modelId) => {
    const response = await api.post(`/api/v1/hecras/run/${modelId}`);
    return response.data;
  },
  
  // Get simulation results
  getResults: async (simulationId) => {
    const response = await api.get(`/api/v1/hecras/results/${simulationId}`);
    return response.data;
  },
  
  // Calculate flood inundation
  calculateInundation: async (terrainData, wseData) => {
    const response = await api.post('/api/v1/hecras/inundation', {
      terrain: terrainData,
      wse: wseData,
    });
    return response.data;
  },
};

/**
 * File Conversion API functions
 */
export const fileApi = {
  // Convert file format
  convertFile: async (file, targetFormat) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('output_format', targetFormat);
    
    const response = await api.post('/api/v1/files/convert', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      responseType: 'blob',
    });
    return response.data;
  },
  
  // Get supported formats
  getSupportedFormats: async () => {
    const response = await api.get('/api/v1/files/formats');
    return response.data;
  },
  
  // Batch convert files
  batchConvert: async (files, targetFormat, outputZip = true) => {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });
    formData.append('output_format', targetFormat);
    formData.append('output_zip', outputZip.toString());
    
    const response = await api.post('/api/v1/files/batch-convert', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      responseType: outputZip ? 'blob' : 'json',
    });
    return response.data;
  },
};

/**
 * Authentication API functions
 */
export const authApi = {
  // Login
  login: async (email, password) => {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);
    
    const response = await api.post('/api/v1/auth/login', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    if (response.data.access_token) {
      localStorage.setItem('auth_token', response.data.access_token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
    }
    
    return response.data;
  },
  
  // Register
  register: async (userData) => {
    const response = await api.post('/api/v1/auth/register', userData);
    
    if (response.data.access_token) {
      localStorage.setItem('auth_token', response.data.access_token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
    }
    
    return response.data;
  },
  
  // Logout
  logout: () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
  },
  
  // Get current user
  getCurrentUser: async () => {
    const response = await api.get('/api/v1/auth/me');
    return response.data;
  },
  
  // Update profile
  updateProfile: async (userData) => {
    const response = await api.put('/api/v1/auth/profile', userData);
    return response.data;
  },
  
  // Change password
  changePassword: async (currentPassword, newPassword) => {
    const response = await api.post('/api/v1/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return response.data;
  },
  
  // Forgot password
  forgotPassword: async (email) => {
    const response = await api.post('/api/v1/auth/forgot-password', { email });
    return response.data;
  },
  
  // Reset password
  resetPassword: async (token, newPassword) => {
    const response = await api.post('/api/v1/auth/reset-password', {
      token,
      new_password: newPassword,
    });
    return response.data;
  },
};

/**
 * Task Management API functions
 */
export const taskApi = {
  // Start task
  startTask: async (taskType, taskData) => {
    const response = await api.post('/api/v1/tasks/start', {
      task_type: taskType,
      task_data: taskData,
    });
    return response.data;
  },
  
  // Check task status
  checkTaskStatus: async (taskId) => {
    const response = await api.get(`/api/v1/tasks/status/${taskId}`);
    return response.data;
  },
  
  // Get task result
  getTaskResult: async (taskId) => {
    const response = await api.get(`/api/v1/tasks/result/${taskId}`);
    return response.data;
  },
  
  // Cancel task
  cancelTask: async (taskId) => {
    const response = await api.post(`/api/v1/tasks/cancel/${taskId}`);
    return response.data;
  },
  
  // List tasks
  listTasks: async (limit = 50, offset = 0) => {
    const response = await api.get(`/api/v1/tasks?limit=${limit}&offset=${offset}`);
    return response.data;
  },
};

/**
 * Monitoring API functions
 */
export const monitoringApi = {
  // Get metrics
  getMetrics: async () => {
    const response = await api.get('/api/v1/monitoring/metrics', {
      responseType: 'text',
    });
    return response.data;
  },
  
  // Get health status
  getHealth: async () => {
    const response = await api.get('/api/v1/monitoring/health');
    return response.data;
  },
  
  // Get performance report
  getPerformance: async () => {
    const response = await api.get('/api/v1/monitoring/performance');
    return response.data;
  },
  
  // Get logs
  getLogs: async (limit = 100) => {
    const response = await api.get(`/api/v1/monitoring/logs?limit=${limit}`);
    return response.data;
  },
};

/**
 * Utility function to download files
 */
export const downloadFile = (data, filename) => {
  const url = window.URL.createObjectURL(new Blob([data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

/**
 * Utility function to check authentication status
 */
export const isAuthenticated = () => {
  return !!localStorage.getItem('auth_token');
};

/**
 * Utility function to get current user
 */
export const getCurrentUser = () => {
  const userStr = localStorage.getItem('user');
  return userStr ? JSON.parse(userStr) : null;
};

// Export all API modules
export default {
  gps: gpsApi,
  marine: marineApi,
  watershed: watershedApi,
  hecras: hecrasApi,
  files: fileApi,
  auth: authApi,
  tasks: taskApi,
  monitoring: monitoringApi,
  utils: {
    downloadFile,
    isAuthenticated,
    getCurrentUser,
  },
};