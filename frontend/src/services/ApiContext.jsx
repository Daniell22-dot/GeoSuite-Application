/**
 * API context and hooks for GeoSuite application.
 * Provides centralized API access and state management.
 */
import React, { createContext, useContext, useState, useCallback } from 'react';
import axios from 'axios';

// Create API context
const ApiContext = createContext();

// API base URL
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for adding auth token
apiClient.interceptors.request.use(
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
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access (no /login route exists; land on home)
      localStorage.removeItem('auth_token');
      window.location.href = '/home';
    }
    return Promise.reject(error);
  }
);

/**
 * Main API provider component
 */
export const ApiProvider = ({ children }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Generic API request handler
   */
  const apiRequest = useCallback(async (method, url, data = null, options = {}) => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient({
        method,
        url,
        data,
        ...options,
      });
      return response.data;
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'API request failed';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Drone survey API functions
   */
  const droneApi = {
    // Create new drone survey
    createSurvey: async (name, description) => {
      return apiRequest('post', '/api/v1/drone/surveys', { name, description });
    },

    // List all surveys
    listSurveys: async () => {
      return apiRequest('get', '/api/v1/drone/surveys');
    },

    // Get survey details
    getSurvey: async (surveyId) => {
      return apiRequest('get', `/api/v1/drone/surveys/${surveyId}`);
    },

    // Upload images to survey
    uploadImages: async (surveyId, files) => {
      const formData = new FormData();
      files.forEach(file => formData.append('files', file));
      return apiRequest('post', `/api/v1/drone/surveys/${surveyId}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },

    // Finalize survey (lock images, begin processing)
    finalizeSurvey: async (surveyId) => {
      return apiRequest('post', `/api/v1/drone/surveys/${surveyId}/finalize`);
    },

    // Process survey with ODM
    processSurvey: async (surveyId) => {
      return apiRequest('post', `/api/v1/drone/surveys/${surveyId}/process`);
    },

    // Delete survey
    deleteSurvey: async (surveyId) => {
      return apiRequest('delete', `/api/v1/drone/surveys/${surveyId}`);
    },
  };

  /**
   * Coordinate transformation API functions
   */
  const transformApi = {
    // Single coordinate transform
    transformSingle: async (easting, northing, direction, zone, method) => {
      return apiRequest('post', '/api/v1/transform/single', {
        easting, northing, direction, zone, method,
      });
    },

    // Bulk coordinate transform
    transformBulk: async (coordinates, direction, zone, method) => {
      return apiRequest('post', '/api/v1/transform/bulk', {
        coordinates, direction, zone, method,
      });
    },

    // Upload Excel file for transformation
    uploadExcel: async (file, direction, zone, method) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('direction', direction);
      formData.append('zone', zone);
      formData.append('method', method);
      return apiRequest('post', '/api/v1/transform/upload-excel', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },

    // Preview Excel columns
    previewExcel: async (file) => {
      const formData = new FormData();
      formData.append('file', file);
      return apiRequest('post', '/api/v1/transform/preview', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },

    // Auto-detect zone from coordinates
    detectZone: async (easting, northing) => {
      return apiRequest('post', '/api/v1/transform/detect-zone', { easting, northing });
    },
  };

  /**
   * Survey plan digitization API functions
   */
  const digitizeApi = {
    // Upload and digitize survey plan
    digitizePlan: async (file, settings) => {
      const formData = new FormData();
      formData.append('file', file);
      if (settings) {
        Object.entries(settings).forEach(([key, value]) => {
          formData.append(key, String(value));
        });
      }
      return apiRequest('post', '/api/v1/digitize/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },

    // Get digitization results
    getResult: async (jobId) => {
      return apiRequest('get', `/api/v1/digitize/result/${jobId}`);
    },

    // Export digitized data
    exportData: async (jobId, format) => {
      return apiRequest('get', `/api/v1/digitize/export/${jobId}?format=${format}`, null, {
        responseType: 'blob',
      });
    },
  };

  /**
   * GPS-related API functions
   */
  const gpsApi = {
    // Upload and parse GPX file
    uploadGpx: async (file) => {
      const formData = new FormData();
      formData.append('file', file);
      
      return apiRequest('post', '/api/v1/gps/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
    },

    // Correct elevation in GPX data
    correctElevation: async (gpxData, demSource = 'srtm') => {
      return apiRequest('post', '/api/v1/gps/correct-elevation', {
        gpx_data: gpxData,
        dem_source: demSource,
      });
    },

    // Convert GPX to other formats
    convertGpx: async (gpxData, targetFormat) => {
      return apiRequest('post', '/api/v1/gps/convert', {
        gpx_data: gpxData,
        format: targetFormat,
      });
    },

    // Get elevation profile
    getElevationProfile: async (coordinates) => {
      return apiRequest('post', '/api/v1/gps/elevation-profile', {
        coordinates,
      });
    },

    // Batch process multiple GPX files
    batchProcessGpx: async (files) => {
      const formData = new FormData();
      files.forEach((file, index) => {
        formData.append(`files`, file);
      });
      
      return apiRequest('post', '/api/v1/gps/batch-process', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
    },
  };

  /**
   * Marine chart API functions
   */
  const marineApi = {
    // Upload and parse marine chart
    uploadChart: async (file) => {
      const formData = new FormData();
      formData.append('file', file);
      
      return apiRequest('post', '/api/v1/marine/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
    },

    // Process KAP file
    processKapFile: async (filePath) => {
      return apiRequest('post', '/api/v1/marine/process-kap', {
        file_path: filePath,
      });
    },

    // Process DWG/DXF file
    processCadFile: async (filePath) => {
      return apiRequest('post', '/api/v1/marine/process-cad', {
        file_path: filePath,
      });
    },

    // Get chart tiles
    getChartTiles: async (chartId, zoom, x, y) => {
      return apiRequest('get', `/api/v1/marine/tiles/${chartId}/${zoom}/${x}/${y}`);
    },

    // Merge multiple charts
    mergeCharts: async (chartPaths, outputFormat = 'geotiff') => {
      return apiRequest('post', '/api/v1/marine/merge', {
        chart_paths: chartPaths,
        output_format: outputFormat,
      });
    },

    // Extract soundings from chart
    extractSoundings: async (chartData, depthRange = [0, 100]) => {
      return apiRequest('post', '/api/v1/marine/extract-soundings', {
        chart_data: chartData,
        depth_range: depthRange,
      });
    },
  };

  /**
   * Watershed analysis API functions
   */
  const watershedApi = {
    // Upload DEM file
    uploadDem: async (file) => {
      const formData = new FormData();
      formData.append('file', file);
      
      return apiRequest('post', '/api/v1/watershed/upload-dem', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
    },

    // Delineate watershed
    delineateWatershed: async (demId, pourPoint) => {
      return apiRequest('post', '/api/v1/watershed/delineate', {
        dem_id: demId,
        pour_point: pourPoint,
      });
    },

    // Extract stream network
    extractStreams: async (demId, threshold = 1000) => {
      return apiRequest('post', '/api/v1/watershed/extract-streams', {
        dem_id: demId,
        threshold,
      });
    },

    // Calculate flow path
    calculateFlowPath: async (demId, startPoint) => {
      return apiRequest('post', '/api/v1/watershed/flow-path', {
        dem_id: demId,
        start_point: startPoint,
      });
    },

    // Calculate flow accumulation
    calculateFlowAccumulation: async (demId) => {
      return apiRequest('post', '/api/v1/watershed/flow-accumulation', {
        dem_id: demId,
      });
    },

    // Batch watershed analysis
    batchWatershedAnalysis: async (demFiles, pourPoints) => {
      return apiRequest('post', '/api/v1/watershed/batch-analysis', {
        dem_files: demFiles,
        pour_points: pourPoints,
      });
    },
  };

  /**
   * File conversion API functions
   */
  const fileApi = {
    // Convert file format
    convertFile: async (file, targetFormat) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('output_format', targetFormat);
      
      return apiRequest('post', '/api/v1/files/convert', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        responseType: 'blob',
      });
    },

    // Get supported formats
    getSupportedFormats: async () => {
      return apiRequest('get', '/api/v1/files/formats');
    },

    // Batch convert files
    batchConvert: async (files, targetFormat, outputZip = true) => {
      const formData = new FormData();
      files.forEach((file, index) => {
        formData.append(`files`, file);
      });
      formData.append('output_format', targetFormat);
      formData.append('output_zip', outputZip.toString());
      
      return apiRequest('post', '/api/v1/files/batch-convert', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        responseType: outputZip ? 'blob' : 'json',
      });
    },

    // Download converted file
    downloadFile: async (fileUrl, fileName) => {
      const response = await apiRequest('get', fileUrl, null, {
        responseType: 'blob',
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', fileName);
      document.body.appendChild(link);
      link.click();
      link.remove();
    },
  };

  /**
   * Task management API functions
   */
  const taskApi = {
    // Start async task
    startTask: async (taskType, taskData) => {
      return apiRequest('post', '/api/v1/tasks/start', {
        task_type: taskType,
        task_data: taskData,
      });
    },

    // Check task status
    checkTaskStatus: async (taskId) => {
      return apiRequest('get', `/api/v1/tasks/status/${taskId}`);
    },

    // Get task result
    getTaskResult: async (taskId) => {
      return apiRequest('get', `/api/v1/tasks/result/${taskId}`);
    },

    // Cancel task
    cancelTask: async (taskId) => {
      return apiRequest('post', `/api/v1/tasks/cancel/${taskId}`);
    },

    // List user tasks
    listTasks: async (limit = 50, offset = 0) => {
      return apiRequest('get', `/api/v1/tasks?limit=${limit}&offset=${offset}`);
    },
  };

  /**
   * Authentication API functions
   */
  const authApi = {
    // Login
    login: async (email, password) => {
      // Backend /login uses OAuth2PasswordRequestForm (form-urlencoded, "username" field)
      const body = new URLSearchParams();
      body.append('username', email);
      body.append('password', password);

      const response = await apiRequest('post', '/api/v1/auth/login', body, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });

      if (response.access_token) {
        localStorage.setItem('auth_token', response.access_token);
        localStorage.setItem('user', JSON.stringify(response.user));
      }

      return response;
    },

    // Register
    register: async (userData) => {
      return apiRequest('post', '/api/v1/auth/register', userData);
    },

    // Logout
    logout: () => {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user');
    },

    // Get current user
    getCurrentUser: async () => {
      return apiRequest('get', '/api/v1/auth/me');
    },

    // Update user profile
    updateProfile: async (userData) => {
      return apiRequest('put', '/api/v1/auth/profile', userData);
    },

    // Change password
    changePassword: async (currentPassword, newPassword) => {
      return apiRequest('post', '/api/v1/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      });
    },
  };

  // Context value
  const contextValue = {
    // State
    loading,
    error,
    setError,
    
    // API modules
    gps: gpsApi,
    marine: marineApi,
    watershed: watershedApi,
    files: fileApi,
    tasks: taskApi,
    auth: authApi,
    drone: droneApi,
    transform: transformApi,
    digitize: digitizeApi,
    
    // Generic request
    request: apiRequest,
    
    // Helper functions
    clearError: () => setError(null),
    isAuthenticated: () => !!localStorage.getItem('auth_token'),
  };

  return (
    <ApiContext.Provider value={contextValue}>
      {children}
    </ApiContext.Provider>
  );
};

/**
 * Custom hook to use the API context
 */
export const useApi = () => {
  const context = useContext(ApiContext);
  if (!context) {
    throw new Error('useApi must be used within an ApiProvider');
  }
  return context;
};

/**
 * Hook for GPS-specific API functions
 */
export const useGps = () => {
  const { gps } = useApi();
  return gps;
};

/**
 * Hook for marine chart API functions
 */
export const useMarine = () => {
  const { marine } = useApi();
  return marine;
};

/**
 * Hook for watershed analysis API functions
 */
export const useWatershed = () => {
  const { watershed } = useApi();
  return watershed;
};

/**
 * Hook for file conversion API functions
 */
export const useFileConverter = () => {
  const { files } = useApi();
  return files;
};

/**
 * Hook for task management API functions
 */
export const useTasks = () => {
  const { tasks } = useApi();
  return tasks;
};

/**
 * Hook for authentication API functions
 */
export const useAuth = () => {
  const { auth } = useApi();
  return auth;
};

/**
 * Hook for drone survey API functions
 */
export const useDrone = () => {
  const { drone } = useApi();
  return drone;
};

/**
 * Hook for coordinate transformation API functions
 */
export const useTransform = () => {
  const { transform } = useApi();
  return transform;
};

/**
 * Hook for survey plan digitization API functions
 */
export const useDigitize = () => {
  const { digitize } = useApi();
  return digitize;
};