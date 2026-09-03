import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  Typography,
  Box,
  Button,
  LinearProgress,
  Alert,
  Chip,
  IconButton,
  Tooltip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Fade,
} from '@mui/material';
import {
  CloudUpload as CloudUploadIcon,
  Delete as DeleteIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  InsertDriveFile as FileIcon,
  GpsFixed as GpsIcon,
  Waves as MarineIcon,
  Terrain as DemIcon,
} from '@mui/icons-material';
import { useApi } from '../services/ApiContext';
import { useAppConfig } from '../services/gisUtils';

const FileUploader = ({ onFileProcessed, maxFiles = 10, acceptMultiple = true }) => {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState({});
  const [error, setError] = useState(null);
  const { gps, marine, watershed } = useApi();
  const { config } = useAppConfig();
  const maxSize = (config?.maxUploadSizeMB || 100) * 1024 * 1024;

  const getFileIcon = (fileType) => {
    switch (fileType?.toLowerCase()) {
      case 'gps': return <GpsIcon fontSize="small" />;
      case 'marine': return <MarineIcon fontSize="small" />;
      case 'dem': return <DemIcon fontSize="small" />;
      default: return <FileIcon fontSize="small" />;
    }
  };

  const getFileColor = (fileType) => {
    switch (fileType?.toLowerCase()) {
      case 'gps': return 'primary';
      case 'marine': return 'secondary';
      case 'dem': return 'success';
      default: return 'default';
    }
  };

  const onDrop = useCallback(async (acceptedFiles) => {
    if (acceptedFiles.length === 0) return;
    
    setUploading(true);
    setError(null);
    
    const newFiles = [];
    
    for (const file of acceptedFiles) {
      try {
        const fileId = `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const fileExt = file.name.split('.').pop().toLowerCase();
        let fileType = 'unknown';
        let apiHandler = null;
        
        if (['gpx', 'kml', 'geojson', 'csv'].includes(fileExt)) {
          fileType = 'gps';
          apiHandler = gps.uploadGpx;
        } else if (['kap', 'bsb', 'dwg', 'dxf'].includes(fileExt)) {
          fileType = 'marine';
          apiHandler = marine.uploadChart;
        } else if (['tif', 'tiff', 'hgt', 'asc', 'dem'].includes(fileExt)) {
          fileType = 'dem';
          apiHandler = watershed.uploadDem;
        } else {
          throw new Error(`Unsupported file type: .${fileExt}`);
        }
        
        setProgress(prev => ({
          ...prev,
          [fileId]: { loaded: 0, total: file.size, percentage: 0 }
        }));
        
        const response = await apiHandler(file);
        
        const processedFile = {
          id: fileId,
          name: file.name,
          size: file.size,
          type: fileType,
          status: 'success',
          data: response,
          uploadedAt: new Date().toISOString(),
        };
        
        newFiles.push(processedFile);
        if (onFileProcessed) onFileProcessed(processedFile);
        
      } catch (err) {
        newFiles.push({
          id: `err_${Date.now()}`,
          name: file.name,
          size: file.size,
          type: 'error',
          status: 'error',
          error: err.message,
          uploadedAt: new Date().toISOString(),
        });
        setError(err.message);
      }
    }
    
    setFiles(prev => [...newFiles, ...prev]);
    setUploading(false);
  }, [gps, marine, watershed, onFileProcessed]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/gpx+xml': ['.gpx'],
      'application/vnd.google-earth.kml+xml': ['.kml'],
      'application/json': ['.geojson'],
      'text/csv': ['.csv'],
      'image/x-bsb': ['.kap', '.bsb'],
      'application/acad': ['.dwg'],
      'application/dxf': ['.dxf'],
      'image/tiff': ['.tif', '.tiff'],
      'application/octet-stream': ['.hgt', '.asc', '.dem'],
    },
    maxFiles: maxFiles,
    multiple: acceptMultiple,
    maxSize: maxSize,
  });

  const removeFile = (fileId) => setFiles(prev => prev.filter(file => file.id !== fileId));
  const clearAllFiles = () => { setFiles([]); setError(null); };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <Box>
      <Box 
        {...getRootProps()}
        sx={{
          border: '2px dashed',
          borderColor: isDragActive ? 'primary.main' : 'rgba(255,255,255,0.1)',
          borderRadius: '16px',
          p: 4,
          textAlign: 'center',
          cursor: 'pointer',
          bgcolor: isDragActive ? 'rgba(10, 132, 255, 0.05)' : 'rgba(255,255,255,0.02)',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          '&:hover': {
            borderColor: 'primary.light',
            bgcolor: 'rgba(255,255,255,0.05)',
            transform: 'scale(1.01)',
          },
        }}
      >
        <input {...getInputProps()} />
        <CloudUploadIcon sx={{ fontSize: 42, color: 'primary.main', mb: 1, opacity: 0.8 }} />
        <Typography variant="body2" sx={{ fontWeight: 500 }}>
          {isDragActive
            ? 'Drop to upload...'
            : 'Select or drag files here'}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          GPX, KML, GeoJSON, CSV, TIFF, HGT, ASC
        </Typography>
      </Box>

      {uploading && (
        <Box sx={{ mt: 2 }}>
          <LinearProgress sx={{ borderRadius: 2, height: 4 }} />
        </Box>
      )}

      {error && (
        <Fade in>
          <Alert severity="error" sx={{ mt: 2, borderRadius: 2, bgcolor: 'rgba(211, 47, 47, 0.1)', color: '#ff8a80', border: '1px solid rgba(211, 47, 47, 0.2)' }}>
            {error}
          </Alert>
        </Fade>
      )}

      {files.length > 0 && (
        <Box sx={{ mt: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
            <Typography variant="caption" sx={{ fontWeight: 600, letterSpacing: 0.5, color: 'text.secondary', textTransform: 'uppercase' }}>
              Pending Uploads
            </Typography>
            <Button size="small" onClick={clearAllFiles} sx={{ color: 'text.secondary', fontSize: '0.7rem' }}>
              Clear
            </Button>
          </Box>

          <List dense sx={{ p: 0 }}>
            {files.map((file) => (
              <ListItem
                key={file.id}
                sx={{
                  bgcolor: 'rgba(255,255,255,0.03)',
                  borderRadius: '12px',
                  mb: 1,
                  border: '1px solid rgba(255,255,255,0.05)',
                }}
                secondaryAction={
                  <IconButton edge="end" size="small" onClick={() => removeFile(file.id)}>
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                }
              >
                <ListItemIcon sx={{ minWidth: 40, color: file.status === 'error' ? 'error.main' : 'primary.light' }}>
                   {file.status === 'success' ? <CheckCircleIcon fontSize="small" /> : getFileIcon(file.type)}
                </ListItemIcon>
                <ListItemText
                  primary={file.name}
                  secondary={formatFileSize(file.size)}
                  primaryTypographyProps={{ variant: 'body2', noWrap: true, sx: { fontWeight: 500 } }}
                  secondaryTypographyProps={{ variant: 'caption', color: 'text.secondary' }}
                />
              </ListItem>
            ))}
          </List>
        </Box>
      )}
    </Box>
  );
};

export default FileUploader;