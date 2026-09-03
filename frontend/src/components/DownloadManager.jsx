import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Stepper,
  Step,
  StepLabel,
  CircularProgress,
  Alert,
  Paper,
  Grid,
  Card,
  CardContent,
  CardActions,
  IconButton,
  Tooltip,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Checkbox,
  FormControlLabel,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  Tabs,
  Tab,
  Snackbar,
  LinearProgress,
  Badge,
} from '@mui/material';
import {
  Download as DownloadIcon,
  Close as CloseIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  InsertDriveFile as FileIcon,
  FolderZip as ZipIcon,
  PictureAsPdf as PdfIcon,
  Image as ImageIcon,
  TableChart as TableIcon,
  Map as MapIcon,
  History as HistoryIcon,
  Delete as DeleteIcon,
  GetApp as GetAppIcon,
  CloudDownload as CloudDownloadIcon,
  Speed as SpeedIcon,
  Storage as StorageIcon,
  Schedule as ScheduleIcon,
  Share as ShareIcon,
  Email as EmailIcon,
} from '@mui/icons-material';
import { useApi } from '../services/ApiContext';

const DownloadManager = ({ open, onClose, data, dataType, onExportComplete }) => {
  const [step, setStep] = useState(0);
  const [selectedFormat, setSelectedFormat] = useState('');
  const [options, setOptions] = useState({
    includeMetadata: true,
    includeCharts: true,
    compress: false,
    highQuality: true,
    watermark: false,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [downloadHistory, setDownloadHistory] = useState([]);
  const [filename, setFilename] = useState('');
  const [activeTab, setActiveTab] = useState(0);
  const [exportStats, setExportStats] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [batchExports, setBatchExports] = useState([]);
  
  const { request } = useApi();

  const steps = ['Select Format', 'Configure Options', 'Process & Download'];

  // Available formats based on data type
  const formatOptions = {
    gps: [
      { value: 'gpx', label: 'GPX', icon: <MapIcon />, description: 'GPS Exchange Format - Compatible with most GPS devices', color: '#1976d2' },
      { value: 'kml', label: 'KML', icon: <MapIcon />, description: 'Keyhole Markup Language - For Google Earth', color: '#1976d2' },
      { value: 'geojson', label: 'GeoJSON', icon: <MapIcon />, description: 'Geographic JSON - Web mapping standard', color: '#2e7d32' },
      { value: 'csv', label: 'CSV', icon: <TableIcon />, description: 'Comma Separated Values - Spreadsheet compatible', color: '#ed6c02' },
      { value: 'shp', label: 'Shapefile', icon: <MapIcon />, description: 'ESRI Shapefile - GIS industry standard', color: '#9c27b0' },
      { value: 'pdf', label: 'PDF Report', icon: <PdfIcon />, description: 'Printable report with maps and statistics', color: '#d32f2f' },
    ],
    watershed: [
      { value: 'geojson', label: 'GeoJSON', icon: <MapIcon />, description: 'Watershed boundaries and stream network', color: '#2e7d32' },
      { value: 'shp', label: 'Shapefile', icon: <MapIcon />, description: 'GIS-compatible watershed data', color: '#9c27b0' },
      { value: 'pdf', label: 'PDF Report', icon: <PdfIcon />, description: 'Comprehensive analysis report', color: '#d32f2f' },
      { value: 'png', label: 'PNG Map', icon: <ImageIcon />, description: 'High-resolution watershed map', color: '#9c27b0' },
      { value: 'tiff', label: 'GeoTIFF', icon: <ImageIcon />, description: 'Georeferenced elevation data', color: '#1976d2' },
      { value: 'csv', label: 'CSV Data', icon: <TableIcon />, description: 'Tabular statistics and metrics', color: '#ed6c02' },
    ],
    marine: [
      { value: 'geotiff', label: 'GeoTIFF', icon: <ImageIcon />, description: 'Georeferenced chart image', color: '#1976d2' },
      { value: 'png', label: 'PNG', icon: <ImageIcon />, description: 'High-quality chart image', color: '#9c27b0' },
      { value: 'jpg', label: 'JPG', icon: <ImageIcon />, description: 'Compressed chart image', color: '#ff9800' },
      { value: 'pdf', label: 'PDF Chart', icon: <PdfIcon />, description: 'Printable nautical chart', color: '#d32f2f' },
      { value: 'csv', label: 'Soundings CSV', icon: <TableIcon />, description: 'Depth soundings data', color: '#ed6c02' },
      { value: 'geojson', label: 'GeoJSON', icon: <MapIcon />, description: 'Chart features and soundings', color: '#2e7d32' },
    ],
    hecras: [
      { value: 'geojson', label: 'GeoJSON', icon: <MapIcon />, description: 'Water surface elevations and cross-sections', color: '#2e7d32' },
      { value: 'csv', label: 'CSV Results', icon: <TableIcon />, description: 'Tabular simulation results', color: '#ed6c02' },
      { value: 'pdf', label: 'PDF Report', icon: <PdfIcon />, description: 'Detailed analysis report', color: '#d32f2f' },
      { value: 'xlsx', label: 'Excel', icon: <TableIcon />, description: 'Interactive spreadsheet', color: '#2e7d32' },
      { value: 'shp', label: 'Shapefile', icon: <MapIcon />, description: 'GIS-compatible flood data', color: '#9c27b0' },
      { value: 'tiff', label: 'Inundation Map', icon: <ImageIcon />, description: 'Flood extent visualization', color: '#1976d2' },
    ],
  };

  useEffect(() => {
    if (open && dataType) {
      // Set default format
      const defaultFormat = formatOptions[dataType]?.[0]?.value || '';
      setSelectedFormat(defaultFormat);
      
      // Generate smart filename
      generateSmartFilename();
      
      // Load download history
      loadDownloadHistory();
      
      // Estimate export size
      estimateExportSize();
    }
  }, [open, dataType, data]);

  useEffect(() => {
    if (data && selectedFormat) {
      estimateExportSize();
    }
  }, [data, selectedFormat, options]);

  const generateSmartFilename = () => {
    const now = new Date();
    const timestamp = now.toISOString().split('T')[0]; // YYYY-MM-DD
    
    let baseName = 'geosuite_export';
    
    if (data?.metadata?.name) {
      baseName = data.metadata.name.replace(/[^a-z0-9]/gi, '_').toLowerCase();
    }
    
    if (dataType) {
      baseName = `${dataType}_${baseName}`;
    }
    
    setFilename(`${baseName}_${timestamp}`);
  };

  const loadDownloadHistory = async () => {
    try {
      const response = await request('get', '/api/v1/export/history?limit=10');
      setDownloadHistory(response.exports || []);
    } catch (err) {
      console.error('Error loading download history:', err);
    }
  };

  const estimateExportSize = () => {
    if (!data || !selectedFormat) return;

    let estimatedSize = 0;
    
    // Calculate based on data type and format
    if (dataType === 'gps') {
      const pointCount = data.tracks?.reduce((sum, track) => 
        sum + track.segments?.reduce((segSum, segment) => 
          segSum + (segment.points?.length || 0), 0), 0) || 0;
      
      estimatedSize = pointCount * 100; // ~100 bytes per point
    } 
    else if (dataType === 'watershed') {
      estimatedSize = data.watershed?.area_km2 * 1000 || 100000; // ~1KB per km²
    }
    else if (dataType === 'marine') {
      estimatedSize = data.soundings?.length * 200 || 50000; // ~200 bytes per sounding
    }
    else if (dataType === 'hecras') {
      estimatedSize = Object.keys(data.water_surface_elevations || {}).length * 500 || 30000;
    }

    // Adjust for format
    const formatMultipliers = {
      gpx: 1.5,
      kml: 1.8,
      geojson: 1.2,
      csv: 0.9,
      shp: 2.5,
      pdf: 3.0,
      png: 2.0,
      jpg: 1.5,
      geotiff: 4.0,
      tiff: 4.0,
      xlsx: 1.3,
    };

    estimatedSize *= formatMultipliers[selectedFormat] || 1;
    
    // Adjust for options
    if (options.highQuality) estimatedSize *= 1.5;
    if (options.includeCharts) estimatedSize *= 1.2;
    if (options.compress) estimatedSize *= 0.7;

    setExportStats({
      estimatedSize,
      estimatedTime: Math.max(1, Math.ceil(estimatedSize / 100000)), // seconds
      format: selectedFormat,
      compatibility: getFormatCompatibility(selectedFormat),
    });
  };

  const getFormatCompatibility = (format) => {
    const compatibility = {
      gpx: ['Garmin', 'Strava', 'Google Earth', 'QGIS', 'ArcGIS'],
      kml: ['Google Earth', 'Google Maps', 'ArcGIS'],
      geojson: ['Web Maps', 'QGIS', 'ArcGIS Online', 'Mapbox'],
      csv: ['Excel', 'Google Sheets', 'R', 'Python'],
      shp: ['ArcGIS', 'QGIS', 'GRASS GIS'],
      pdf: ['Adobe Reader', 'Preview', 'Web Browsers'],
      png: ['Image Viewers', 'Web', 'Presentations'],
      geotiff: ['QGIS', 'ArcGIS', 'ERDAS Imagine'],
      xlsx: ['Excel', 'Google Sheets', 'LibreOffice'],
    };
    
    return compatibility[format] || ['Most Applications'];
  };

  const handleNext = () => {
    if (step === 0 && !selectedFormat) {
      setError('Please select a format');
      return;
    }
    
    if (step === 1 && !filename.trim()) {
      setError('Please enter a filename');
      return;
    }
    
    setStep(step + 1);
    setError(null);
    
    if (step === 1) {
      handleDownload();
    }
  };

  const handleBack = () => {
    setStep(step - 1);
    setError(null);
  };

  const handleDownload = async () => {
    setLoading(true);
    setError(null);

    try {
      const exportData = {
        [`${dataType}_data`]: data,
        format: selectedFormat,
        filename: filename,
        ...options,
      };

      const endpoint = `/api/v1/export/${dataType}`;
      const response = await request('post', endpoint, exportData, {
        responseType: 'blob',
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response]));
      const link = document.createElement('a');
      link.href = url;
      
      // Extract filename from response headers or use default
      const contentDisposition = response.headers.get('content-disposition');
      let downloadFilename = filename;
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
        if (filenameMatch && filenameMatch[1]) {
          downloadFilename = filenameMatch[1];
        }
      }
      
      // Add extension if not present
      if (!downloadFilename.includes('.')) {
        downloadFilename += `.${selectedFormat}`;
      }
      
      link.setAttribute('download', downloadFilename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      // Record in history
      const historyItem = {
        id: Date.now().toString(),
        type: dataType,
        format: selectedFormat,
        filename: downloadFilename,
        date: new Date().toISOString(),
        size: response.size || 0,
        options: options,
      };
      
      // Save to localStorage for persistence
      const existingHistory = JSON.parse(localStorage.getItem('geosuite_download_history') || '[]');
      const updatedHistory = [historyItem, ...existingHistory.slice(0, 49)]; // Keep last 50
      localStorage.setItem('geosuite_download_history', JSON.stringify(updatedHistory));
      
      setDownloadHistory(updatedHistory);

      // Show success message
      setSnackbar({
        open: true,
        message: `Downloaded ${downloadFilename} (${formatFileSize(response.size)})`,
        severity: 'success',
      });

      // Callback if provided
      if (onExportComplete) {
        onExportComplete({
          filename: downloadFilename,
          format: selectedFormat,
          size: response.size,
          dataType: dataType,
        });
      }

      // Move to completion step
      setStep(2);

    } catch (err) {
      const errorMessage = err.message || 'Download failed. Please try again.';
      setError(errorMessage);
      setSnackbar({
        open: true,
        message: errorMessage,
        severity: 'error',
      });
      setStep(1); // Go back to configuration step
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePackage = async () => {
    setLoading(true);
    setError(null);

    try {
      // Create export package with multiple formats
      const packageData = {
        exports: [
          {
            type: dataType,
            data: data,
            format: selectedFormat,
          },
          // Add additional formats
          {
            type: dataType,
            data: data,
            format: formatOptions[dataType]?.[1]?.value || 'pdf',
          },
        ],
        package_name: filename.replace(/\.[^/.]+$/, "") || 'geosuite_package',
        include_manifest: true,
        compress_level: 9,
      };

      const response = await request('post', '/api/v1/export/package', packageData, {
        responseType: 'blob',
      });

      // Download package
      const url = window.URL.createObjectURL(new Blob([response]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${packageData.package_name}.zip`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      // Record package download
      const historyItem = {
        id: `package_${Date.now()}`,
        type: 'package',
        format: 'zip',
        filename: `${packageData.package_name}.zip`,
        date: new Date().toISOString(),
        size: response.size,
        contains: packageData.exports.map(e => e.format),
      };

      const existingHistory = JSON.parse(localStorage.getItem('geosuite_download_history') || '[]');
      const updatedHistory = [historyItem, ...existingHistory.slice(0, 49)];
      localStorage.setItem('geosuite_download_history', JSON.stringify(updatedHistory));
      
      setDownloadHistory(updatedHistory);

      setSnackbar({
        open: true,
        message: `Package downloaded (${formatFileSize(response.size)})`,
        severity: 'success',
      });

    } catch (err) {
      setError(err.message || 'Package creation failed');
      setSnackbar({
        open: true,
        message: 'Package creation failed',
        severity: 'error',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleShareExport = async () => {
    try {
      // Create a shareable link (in production, this would generate a secure link)
      const shareData = {
        dataType: dataType,
        format: selectedFormat,
        filename: filename,
        timestamp: new Date().toISOString(),
      };
      
      const shareToken = btoa(JSON.stringify(shareData));
      const shareUrl = `${window.location.origin}/share/${shareToken}`;
      
      // Copy to clipboard
      await navigator.clipboard.writeText(shareUrl);
      
      setSnackbar({
        open: true,
        message: 'Shareable link copied to clipboard',
        severity: 'success',
      });
      
    } catch (err) {
      setSnackbar({
        open: true,
        message: 'Failed to create share link',
        severity: 'error',
      });
    }
  };

  const handleEmailExport = () => {
    // In production, this would call an API to email the export
    setSnackbar({
      open: true,
      message: 'Email feature requires backend setup',
      severity: 'info',
    });
  };

  const handleDeleteHistory = (itemId) => {
    const updatedHistory = downloadHistory.filter(item => item.id !== itemId);
    setDownloadHistory(updatedHistory);
    localStorage.setItem('geosuite_download_history', JSON.stringify(updatedHistory));
    
    setSnackbar({
      open: true,
      message: 'Removed from history',
      severity: 'info',
    });
  };

  const handleRedownload = async (historyItem) => {
    setLoading(true);
    
    try {
      // In production, you would fetch the file from server
      // For now, we'll simulate re-download
      const blob = new Blob([JSON.stringify({ message: 'Previously exported file' })], {
        type: 'application/json'
      });
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', historyItem.filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      setSnackbar({
        open: true,
        message: `Downloaded ${historyItem.filename}`,
        severity: 'success',
      });
      
    } catch (err) {
      setSnackbar({
        open: true,
        message: 'Redownload failed',
        severity: 'error',
      });
    } finally {
      setLoading(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes || bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFormatIcon = (format) => {
    switch (format) {
      case 'pdf':
        return <PdfIcon />;
      case 'png':
      case 'jpg':
      case 'jpeg':
      case 'geotiff':
      case 'tif':
      case 'tiff':
        return <ImageIcon />;
      case 'csv':
      case 'xlsx':
        return <TableIcon />;
      case 'zip':
      case 'shp':
        return <ZipIcon />;
      case 'gpx':
      case 'kml':
      case 'geojson':
        return <MapIcon />;
      default:
        return <FileIcon />;
    }
  };

  const getFormatColor = (format) => {
    const formatColors = {
      gpx: '#1976d2',
      kml: '#1976d2',
      geojson: '#2e7d32',
      csv: '#ed6c02',
      shp: '#9c27b0',
      pdf: '#d32f2f',
      png: '#9c27b0',
      jpg: '#ff9800',
      geotiff: '#1976d2',
      tiff: '#1976d2',
      xlsx: '#2e7d32',
      zip: '#757575',
    };
    
    return formatColors[format] || '#666';
  };

  const renderStepContent = () => {
    switch (step) {
      case 0:
        return (
          <Box>
            <Typography variant="subtitle1" gutterBottom>
              Select export format for {dataType} data:
            </Typography>
            
            <Tabs 
              value={activeTab} 
              onChange={(e, newValue) => setActiveTab(newValue)}
              sx={{ mb: 2 }}
            >
              <Tab label="Recommended" />
              <Tab label="All Formats" />
              <Tab label="GIS Formats" />
            </Tabs>
            
            <Grid container spacing={2}>
              {(formatOptions[dataType] || []).slice(0, activeTab === 0 ? 3 : 6).map((format) => (
                <Grid item xs={12} md={6} key={format.value}>
                  <Card 
                    sx={{ 
                      cursor: 'pointer',
                      border: selectedFormat === format.value ? `2px solid ${format.color}` : '1px solid #e0e0e0',
                      transition: 'all 0.2s',
                      '&:hover': {
                        transform: 'translateY(-2px)',
                        boxShadow: 3,
                        borderColor: format.color,
                      },
                    }}
                    onClick={() => {
                      setSelectedFormat(format.value);
                      generateSmartFilename();
                    }}
                  >
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                        <Box sx={{ color: format.color, mr: 2 }}>
                          {format.icon}
                        </Box>
                        <Box sx={{ flexGrow: 1 }}>
                          <Typography variant="subtitle1">
                            {format.label}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            .{format.value}
                          </Typography>
                        </Box>
                        {selectedFormat === format.value && (
                          <CheckCircleIcon color="success" />
                        )}
                      </Box>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        {format.description}
                      </Typography>
                      
                      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                        {getFormatCompatibility(format.value).slice(0, 2).map(app => (
                          <Chip 
                            key={app}
                            label={app}
                            size="small"
                            variant="outlined"
                          />
                        ))}
                        {getFormatCompatibility(format.value).length > 2 && (
                          <Chip 
                            label={`+${getFormatCompatibility(format.value).length - 2}`}
                            size="small"
                            variant="outlined"
                          />
                        )}
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
            
            {exportStats && (
              <Paper variant="outlined" sx={{ p: 2, mt: 3, bgcolor: 'grey.50' }}>
                <Typography variant="subtitle2" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                  <SpeedIcon sx={{ mr: 1, fontSize: 18 }} />
                  Export Details
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={4}>
                    <Typography variant="caption" color="text.secondary">Estimated Size</Typography>
                    <Typography variant="body2" fontWeight="medium">
                      {formatFileSize(exportStats.estimatedSize)}
                    </Typography>
                  </Grid>
                  <Grid item xs={4}>
                    <Typography variant="caption" color="text.secondary">Estimated Time</Typography>
                    <Typography variant="body2" fontWeight="medium">
                      {exportStats.estimatedTime}s
                    </Typography>
                  </Grid>
                  <Grid item xs={4}>
                    <Typography variant="caption" color="text.secondary">Format</Typography>
                    <Typography variant="body2" fontWeight="medium">
                      {exportStats.format.toUpperCase()}
                    </Typography>
                  </Grid>
                </Grid>
              </Paper>
            )}
          </Box>
        );

      case 1:
        return (
          <Box>
            <Typography variant="subtitle1" gutterBottom>
              Configure export options:
            </Typography>
            
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <TextField
                  label="Filename"
                  value={filename}
                  onChange={(e) => setFilename(e.target.value)}
                  fullWidth
                  helperText="Name for the exported file"
                  InputProps={{
                    endAdornment: (
                      <Chip 
                        label={`.${selectedFormat}`}
                        size="small"
                        sx={{ ml: 1 }}
                      />
                    ),
                  }}
                />
              </Grid>
              
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>File Version</InputLabel>
                  <Select
                    value={options.version || 'v1'}
                    onChange={(e) => setOptions(prev => ({ ...prev, version: e.target.value }))}
                    label="File Version"
                  >
                    <MenuItem value="v1">Version 1 (Compatible)</MenuItem>
                    <MenuItem value="latest">Latest Format</MenuItem>
                    <MenuItem value="legacy">Legacy Support</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Coordinate System</InputLabel>
                  <Select
                    value={options.coordinateSystem || 'wgs84'}
                    onChange={(e) => setOptions(prev => ({ ...prev, coordinateSystem: e.target.value }))}
                    label="Coordinate System"
                  >
                    <MenuItem value="wgs84">WGS84 (GPS)</MenuItem>
                    <MenuItem value="utm">UTM</MenuItem>
                    <MenuItem value="stateplane">State Plane</MenuItem>
                    <MenuItem value="webmercator">Web Mercator</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12}>
                <Typography variant="subtitle2" gutterBottom>
                  Export Options
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={options.includeMetadata !== false}
                          onChange={(e) => setOptions(prev => ({ ...prev, includeMetadata: e.target.checked }))}
                        />
                      }
                      label="Include metadata"
                    />
                    <Typography variant="caption" color="text.secondary" display="block">
                      Author, description, timestamps
                    </Typography>
                  </Grid>
                  
                  <Grid item xs={12} md={6}>
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={options.includeCharts === true}
                          onChange={(e) => setOptions(prev => ({ ...prev, includeCharts: e.target.checked }))}
                        />
                      }
                      label="Include charts"
                    />
                    <Typography variant="caption" color="text.secondary" display="block">
                      Visualizations and graphs
                    </Typography>
                  </Grid>
                  
                  <Grid item xs={12} md={6}>
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={options.highQuality === true}
                          onChange={(e) => setOptions(prev => ({ ...prev, highQuality: e.target.checked }))}
                        />
                      }
                      label="High quality"
                    />
                    <Typography variant="caption" color="text.secondary" display="block">
                      Better resolution, larger file
                    </Typography>
                  </Grid>
                  
                  <Grid item xs={12} md={6}>
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={options.compress === true}
                          onChange={(e) => setOptions(prev => ({ ...prev, compress: e.target.checked }))}
                        />
                      }
                      label="Compress file"
                    />
                    <Typography variant="caption" color="text.secondary" display="block">
                      Smaller file size
                    </Typography>
                  </Grid>
                  
                  <Grid item xs={12} md={6}>
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={options.watermark === false}
                          onChange={(e) => setOptions(prev => ({ ...prev, watermark: !e.target.checked }))}
                        />
                      }
                      label="Add watermark"
                    />
                    <Typography variant="caption" color="text.secondary" display="block">
                      "Exported from GeoSuite"
                    </Typography>
                  </Grid>
                </Grid>
              </Grid>
              
              <Grid item xs={12}>
                <Divider sx={{ my: 2 }} />
                
                <Typography variant="subtitle2" gutterBottom>
                  Preview
                </Typography>
                <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.50' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    {getFormatIcon(selectedFormat)}
                    <Typography variant="body1" sx={{ ml: 1, flexGrow: 1 }}>
                      {filename}.{selectedFormat}
                    </Typography>
                    <Chip 
                      label={formatFileSize(exportStats?.estimatedSize || 0)}
                      size="small"
                      color="primary"
                    />
                  </Box>
                  
                  <Typography variant="body2" color="text.secondary">
                    Format: {selectedFormat.toUpperCase()}
                    <br />
                    Type: {dataType.toUpperCase()}
                    <br />
                    Generated: {new Date().toLocaleString()}
                    <br />
                    Options: {Object.entries(options).filter(([k, v]) => v).map(([k]) => k).join(', ')}
                  </Typography>
                </Paper>
              </Grid>
            </Grid>
          </Box>
        );

      case 2:
        return (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            {loading ? (
              <>
                <CircularProgress size={60} sx={{ mb: 3 }} />
                <Typography variant="h6" gutterBottom>
                  Processing Export...
                </Typography>
                <LinearProgress sx={{ width: '80%', mx: 'auto', my: 2 }} />
                <Typography variant="body2" color="text.secondary">
                  Preparing {filename}.{selectedFormat}
                  <br />
                  Estimated time: {exportStats?.estimatedTime || 5} seconds
                </Typography>
              </>
            ) : error ? (
              <>
                <ErrorIcon color="error" sx={{ fontSize: 60, mb: 3 }} />
                <Typography variant="h6" color="error" gutterBottom>
                  Export Failed
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                  {error}
                </Typography>
                <Button
                  variant="outlined"
                  startIcon={<GetAppIcon />}
                  onClick={handleDownload}
                >
                  Try Again
                </Button>
              </>
            ) : (
              <>
                <CheckCircleIcon color="success" sx={{ fontSize: 60, mb: 3 }} />
                <Typography variant="h6" gutterBottom>
                  Export Complete!
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  Your {selectedFormat.toUpperCase()} file has been downloaded.
                </Typography>
                
                <Paper variant="outlined" sx={{ p: 3, my: 3, maxWidth: 400, mx: 'auto' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <Box sx={{ 
                      bgcolor: getFormatColor(selectedFormat), 
                      color: 'white',
                      p: 1,
                      borderRadius: 1,
                      mr: 2,
                    }}>
                      {getFormatIcon(selectedFormat)}
                    </Box>
                    <Box sx={{ flexGrow: 1 }}>
                      <Typography variant="subtitle1">
                        {filename}.{selectedFormat}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {formatFileSize(exportStats?.estimatedSize || 0)} • {new Date().toLocaleDateString()}
                      </Typography>
                    </Box>
                  </Box>
                  
                  <Divider sx={{ my: 2 }} />
                  
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Button
                        variant="outlined"
                        fullWidth
                        startIcon={<GetAppIcon />}
                        onClick={handleDownload}
                      >
                        Download Again
                      </Button>
                    </Grid>
                    <Grid item xs={6}>
                      <Button
                        variant="outlined"
                        fullWidth
                        startIcon={<ZipIcon />}
                        onClick={handleCreatePackage}
                      >
                        Create Package
                      </Button>
                    </Grid>
                    <Grid item xs={6}>
                      <Button
                        variant="outlined"
                        fullWidth
                        startIcon={<ShareIcon />}
                        onClick={handleShareExport}
                      >
                        Share Link
                      </Button>
                    </Grid>
                    <Grid item xs={6}>
                      <Button
                        variant="outlined"
                        fullWidth
                        startIcon={<EmailIcon />}
                        onClick={handleEmailExport}
                      >
                        Email Export
                      </Button>
                    </Grid>
                  </Grid>
                </Paper>
              </>
            )}
          </Box>
        );

      default:
        return null;
    }
  };

  const handleClose = () => {
    setStep(0);
    setSelectedFormat('');
    setOptions({
      includeMetadata: true,
      includeCharts: true,
      compress: false,
      highQuality: true,
      watermark: false,
    });
    setError(null);
    setLoading(false);
    onClose();
  };

  const closeSnackbar = () => {
    setSnackbar(prev => ({ ...prev, open: false }));
  };

  return (
    <>
      <Dialog 
        open={open} 
        onClose={loading ? undefined : handleClose}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: { minHeight: 500 }
        }}
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <DownloadIcon sx={{ mr: 1 }} />
              <Typography variant="h6">
                Export {dataType ? dataType.toUpperCase() : 'Data'}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              {step < 2 && (
                <Chip 
                  label={`Step ${step + 1} of 3`}
                  size="small"
                  color="primary"
                  variant="outlined"
                  sx={{ mr: 1 }}
                />
              )}
              <IconButton onClick={handleClose} size="small" disabled={loading}>
                <CloseIcon />
              </IconButton>
            </Box>
          </Box>
        </DialogTitle>
        
        <DialogContent dividers sx={{ minHeight: 400 }}>
          {step < 2 && (
            <Stepper activeStep={step} sx={{ mb: 4 }}>
              {steps.map((label) => (
                <Step key={label}>
                  <StepLabel>{label}</StepLabel>
                </Step>
              ))}
            </Stepper>
          )}
          
          {error && (
            <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}
          
          {renderStepContent()}
          
          {/* Download History */}
          {step === 0 && downloadHistory.length > 0 && (
            <Box sx={{ mt: 4 }}>
              <Typography variant="subtitle2" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                <HistoryIcon sx={{ mr: 1, fontSize: 20 }} />
                Recent Exports ({downloadHistory.length})
              </Typography>
              <Paper variant="outlined" sx={{ maxHeight: 200, overflow: 'auto' }}>
                <List dense>
                  {downloadHistory.slice(0, 5).map((item) => (
                    <ListItem 
                      key={item.id}
                      sx={{ 
                        '&:hover': { bgcolor: 'action.hover' },
                        cursor: 'pointer',
                      }}
                      onClick={() => handleRedownload(item)}
                    >
                      <ListItemIcon sx={{ color: getFormatColor(item.format) }}>
                        {getFormatIcon(item.format)}
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <Typography variant="body2" noWrap sx={{ flexGrow: 1 }}>
                              {item.filename}
                            </Typography>
                            <Chip 
                              label={formatFileSize(item.size)}
                              size="small"
                              sx={{ ml: 1 }}
                            />
                          </Box>
                        }
                        secondary={`${new Date(item.date).toLocaleDateString()} • ${item.format.toUpperCase()}`}
                      />
                      <ListItemSecondaryAction>
                        <Tooltip title="Remove from history">
                          <IconButton
                            edge="end"
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteHistory(item.id);
                            }}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </ListItemSecondaryAction>
                    </ListItem>
                  ))}
                </List>
              </Paper>
            </Box>
          )}
        </DialogContent>
        
        <DialogActions sx={{ px: 3, py: 2 }}>
          {step > 0 && step < 2 && (
            <Button onClick={handleBack} disabled={loading}>
              Back
            </Button>
          )}
          
          <Box sx={{ flexGrow: 1 }} />
          
          {step < 2 && (
            <Button
              variant="contained"
              onClick={handleNext}
              disabled={loading || (step === 0 && !selectedFormat)}
              startIcon={step === 1 ? <CloudDownloadIcon /> : null}
              sx={{ minWidth: 120 }}
            >
              {step === 0 ? 'Next' : loading ? 'Processing...' : 'Export'}
            </Button>
          )}
          
          {step === 2 && !loading && (
            <Button 
              variant="contained" 
              onClick={handleClose}
              startIcon={<CheckCircleIcon />}
            >
              Done
            </Button>
          )}
        </DialogActions>
      </Dialog>
      
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={closeSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert onClose={closeSnackbar} severity={snackbar.severity} sx={{ width: '100%' }}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </>
  );
};

export default DownloadManager;