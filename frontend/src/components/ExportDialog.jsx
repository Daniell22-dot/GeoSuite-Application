import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  FormControlLabel,
  Switch,
  TextField,
  Slider,
  Alert,
  CircularProgress,
  Chip,
  IconButton,
  Tooltip,
  Tabs,
  Tab,
  Divider,
} from '@mui/material';
import {
  Download as DownloadIcon,
  Close as CloseIcon,
  CloudDownload as CloudDownloadIcon,
  PictureAsPdf as PdfIcon,
  Map as MapIcon,
  TableChart as TableIcon,
  Image as ImageIcon,
  Archive as ArchiveIcon,
  Settings as SettingsIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { useApi } from '../services/ApiContext';

const ExportDialog = ({ open, onClose, data, dataType, title = "Export Data" }) => {
  const [activeTab, setActiveTab] = useState(0);
  const [selectedFormat, setSelectedFormat] = useState('geojson');
  const [exportOptions, setExportOptions] = useState({
    includeElevation: true,
    simplifyTolerance: 0,
    projection: 'EPSG:4326',
    resolution: 'medium',
    includeMetadata: true,
    compress: false,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [formats, setFormats] = useState([]);
  
  const { request } = useApi();

  useEffect(() => {
    if (open) {
      fetchExportFormats();
    }
  }, [open, dataType]);

  const fetchExportFormats = async () => {
    try {
      const response = await request('get', '/api/v1/export/formats');
      if (response[dataType]) {
        setFormats(response[dataType]);
        setSelectedFormat(response[dataType][0]?.format || 'geojson');
      }
    } catch (err) {
      console.error('Failed to fetch export formats:', err);
    }
  };

  const getFormatIcon = (format) => {
    switch (format) {
      case 'geojson':
      case 'gpx':
      case 'kml':
      case 'shp':
        return <MapIcon />;
      case 'csv':
      case 'xlsx':
        return <TableIcon />;
      case 'pdf':
        return <PdfIcon />;
      case 'png':
      case 'geotiff':
        return <ImageIcon />;
      case 'zip':
        return <ArchiveIcon />;
      default:
        return <DownloadIcon />;
    }
  };

  const getFormatDescription = (format) => {
    const formatObj = formats.find(f => f.format === format);
    return formatObj?.description || format.toUpperCase();
  };

  const handleExport = async () => {
    if (!data) {
      setError('No data to export');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      let endpoint = '';
      let payload = {};

      switch (dataType) {
        case 'gps':
          endpoint = '/api/v1/export/gps';
          payload = {
            gpx_data: data,
            format: selectedFormat,
            include_elevation: exportOptions.includeElevation,
          };
          break;
        
        case 'marine':
          endpoint = '/api/v1/export/marine';
          payload = {
            chart_data: data,
            format: selectedFormat,
          };
          break;
        
        case 'watershed':
          endpoint = '/api/v1/export/watershed';
          payload = {
            analysis_data: data,
            format: selectedFormat,
          };
          break;
        
        case 'hecras':
          endpoint = '/api/v1/export/hecras';
          payload = {
            results_data: data,
            format: selectedFormat,
          };
          break;
        
        default:
          throw new Error(`Unsupported data type: ${dataType}`);
      }

      const response = await request('post', endpoint, payload, {
        responseType: 'blob',
      });

      // Create download link
      const blob = new Blob([response], { 
        type: response.type || 'application/octet-stream' 
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      
      // Extract filename from response headers or generate one
      const filename = `export_${dataType}_${new Date().getTime()}.${selectedFormat}`;
      link.download = filename;
      
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      onClose();
      
    } catch (err) {
      setError(err.message || 'Export failed');
    } finally {
      setLoading(false);
    }
  };

  const handleCustomExport = async () => {
    if (!data) {
      setError('No data to export');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const exportConfig = {
        data_type: dataType,
        data: data,
        format: selectedFormat,
        options: exportOptions,
      };

      const response = await request('post', '/api/v1/export/custom', exportConfig, {
        responseType: 'blob',
      });

      // Create download link
      const blob = new Blob([response], { 
        type: response.type || 'application/octet-stream' 
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `custom_export_${new Date().getTime()}.${selectedFormat}`;
      
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      onClose();
      
    } catch (err) {
      setError(err.message || 'Custom export failed');
    } finally {
      setLoading(false);
    }
  };

  const renderFormatOptions = () => {
    switch (selectedFormat) {
      case 'shp':
        return (
          <Alert severity="info" sx={{ mt: 2 }}>
            Shapefile export includes multiple files compressed in a ZIP archive.
          </Alert>
        );
      
      case 'pdf':
        return (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              PDF Options
            </Typography>
            <FormControlLabel
              control={
                <Switch
                  checked={exportOptions.includeMetadata}
                  onChange={(e) => setExportOptions({
                    ...exportOptions,
                    includeMetadata: e.target.checked,
                  })}
                />
              }
              label="Include Metadata"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={exportOptions.compress}
                  onChange={(e) => setExportOptions({
                    ...exportOptions,
                    compress: e.target.checked,
                  })}
                />
              }
              label="Compress PDF"
            />
          </Box>
        );
      
      case 'png':
      case 'geotiff':
        return (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Image Resolution
            </Typography>
            <FormControl fullWidth>
              <Select
                value={exportOptions.resolution}
                onChange={(e) => setExportOptions({
                  ...exportOptions,
                  resolution: e.target.value,
                })}
              >
                <MenuItem value="low">Low (72 DPI)</MenuItem>
                <MenuItem value="medium">Medium (150 DPI)</MenuItem>
                <MenuItem value="high">High (300 DPI)</MenuItem>
                <MenuItem value="ultra">Ultra (600 DPI)</MenuItem>
              </Select>
            </FormControl>
          </Box>
        );
      
      default:
        return null;
    }
  };

  const renderDataPreview = () => {
    if (!data) return null;

    let previewText = '';
    let itemCount = 0;

    switch (dataType) {
      case 'gps':
        if (data.points) {
          itemCount = data.points.length;
          previewText = `${itemCount} track points`;
        } else if (data.tracks) {
          itemCount = data.tracks.length;
          previewText = `${itemCount} tracks`;
        }
        break;
      
      case 'marine':
        if (data.soundings) {
          itemCount = data.soundings.length;
          previewText = `${itemCount} soundings`;
        }
        break;
      
      case 'watershed':
        if (data.watershed) {
          previewText = `Area: ${data.watershed.area_km2?.toFixed(2)} km²`;
        }
        break;
      
      case 'hecras':
        if (data.water_surface_elevations) {
          itemCount = Object.keys(data.water_surface_elevations).length;
          previewText = `${itemCount} measurement points`;
        }
        break;
    }

    return (
      <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
        <Typography variant="subtitle2" gutterBottom>
          Data Preview
        </Typography>
        <Typography variant="body2">
          {previewText}
        </Typography>
        {data.metadata?.name && (
          <Typography variant="body2">
            Name: {data.metadata.name}
          </Typography>
        )}
      </Box>
    );
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">
            {title}
          </Typography>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)} sx={{ mb: 2 }}>
          <Tab label="Quick Export" />
          <Tab label="Advanced Options" />
          <Tab label="Bulk Export" />
        </Tabs>

        {activeTab === 0 && (
          <Box>
            <Typography variant="subtitle1" gutterBottom>
              Select Export Format
            </Typography>
            
            <Grid container spacing={2}>
              {formats.map((format) => (
                <Grid item xs={6} sm={4} key={format.format}>
                  <Card
                    sx={{
                      cursor: 'pointer',
                      border: selectedFormat === format.format ? '2px solid #1976d2' : '1px solid #e0e0e0',
                      transition: 'all 0.2s',
                      '&:hover': {
                        borderColor: '#1976d2',
                        boxShadow: 2,
                      },
                    }}
                    onClick={() => setSelectedFormat(format.format)}
                  >
                    <CardContent sx={{ textAlign: 'center', p: 2 }}>
                      <Box sx={{ color: selectedFormat === format.format ? '#1976d2' : 'text.secondary', mb: 1 }}>
                        {getFormatIcon(format.format)}
                      </Box>
                      <Typography variant="body2" fontWeight={selectedFormat === format.format ? 'bold' : 'normal'}>
                        {format.format.toUpperCase()}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {format.description}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>

            {renderFormatOptions()}
            {renderDataPreview()}
          </Box>
        )}

        {activeTab === 1 && (
          <Box>
            <Typography variant="subtitle1" gutterBottom>
              Advanced Export Settings
            </Typography>
            
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth sx={{ mb: 2 }}>
                  <InputLabel>Projection</InputLabel>
                  <Select
                    value={exportOptions.projection}
                    label="Projection"
                    onChange={(e) => setExportOptions({
                      ...exportOptions,
                      projection: e.target.value,
                    })}
                  >
                    <MenuItem value="EPSG:4326">WGS84 (EPSG:4326)</MenuItem>
                    <MenuItem value="EPSG:3857">Web Mercator (EPSG:3857)</MenuItem>
                    <MenuItem value="EPSG:32633">UTM Zone 33N (EPSG:32633)</MenuItem>
                    <MenuItem value="custom">Custom Projection</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} sm={6}>
                <FormControl fullWidth sx={{ mb: 2 }}>
                  <InputLabel>Coordinate Precision</InputLabel>
                  <Select
                    value={exportOptions.simplifyTolerance}
                    label="Coordinate Precision"
                    onChange={(e) => setExportOptions({
                      ...exportOptions,
                      simplifyTolerance: e.target.value,
                    })}
                  >
                    <MenuItem value={0}>Full Precision</MenuItem>
                    <MenuItem value={0.0001}>High (6 decimals)</MenuItem>
                    <MenuItem value={0.001}>Medium (5 decimals)</MenuItem>
                    <MenuItem value={0.01}>Low (4 decimals)</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            </Grid>

            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                Data Options
              </Typography>
              <FormControlLabel
                control={
                  <Switch
                    checked={exportOptions.includeElevation}
                    onChange={(e) => setExportOptions({
                      ...exportOptions,
                      includeElevation: e.target.checked,
                    })}
                  />
                }
                label="Include Elevation Data"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={exportOptions.includeMetadata}
                    onChange={(e) => setExportOptions({
                      ...exportOptions,
                      includeMetadata: e.target.checked,
                    })}
                  />
                }
                label="Include Metadata"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={exportOptions.compress}
                    onChange={(e) => setExportOptions({
                      ...exportOptions,
                      compress: e.target.checked,
                    })}
                  />
                }
                label="Compress Output"
              />
            </Box>

            <Box sx={{ mt: 3 }}>
              <Typography variant="subtitle2" gutterBottom>
                File Naming
              </Typography>
              <TextField
                fullWidth
                label="Filename"
                defaultValue={`${dataType}_export_${new Date().toISOString().split('T')[0]}`}
                variant="outlined"
                size="small"
              />
            </Box>
          </Box>
        )}

        {activeTab === 2 && (
          <Box>
            <Typography variant="subtitle1" gutterBottom>
              Bulk Export Multiple Files
            </Typography>
            
            <Alert severity="info" sx={{ mb: 2 }}>
              Bulk export creates a ZIP archive containing multiple files. 
              Select the formats you want to include:
            </Alert>

            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" gutterBottom>
                Included Formats
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {formats.slice(0, 5).map((format) => (
                  <Chip
                    key={format.format}
                    label={format.format.toUpperCase()}
                    icon={getFormatIcon(format.format)}
                    variant="outlined"
                    onClick={() => setSelectedFormat(format.format)}
                    color={selectedFormat === format.format ? 'primary' : 'default'}
                  />
                ))}
              </Box>
            </Box>

            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                Export Structure
              </Typography>
              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>Folder Organization</InputLabel>
                <Select defaultValue="by_format" label="Folder Organization">
                  <MenuItem value="by_format">Organize by Format</MenuItem>
                  <MenuItem value="by_dataset">Organize by Dataset</MenuItem>
                  <MenuItem value="flat">All Files in Root</MenuItem>
                </Select>
              </FormControl>
            </Box>
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        
        {activeTab === 2 ? (
          <Button
            variant="contained"
            startIcon={loading ? <CircularProgress size={20} /> : <ArchiveIcon />}
            onClick={handleCustomExport}
            disabled={loading || !data}
          >
            {loading ? 'Creating Archive...' : 'Create Bulk Export'}
          </Button>
        ) : (
          <Button
            variant="contained"
            startIcon={loading ? <CircularProgress size={20} /> : <DownloadIcon />}
            onClick={handleExport}
            disabled={loading || !data}
          >
            {loading ? 'Exporting...' : 'Export'}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default ExportDialog;