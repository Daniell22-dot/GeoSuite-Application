import React, { useState } from 'react';
import {
  Container,
  Grid,
  Paper,
  Typography,
  Box,
  Button,
  Card,
  CardContent,
  CardActions,
  Chip,
  IconButton,
  Tooltip,
  Stack,
  Divider,
} from '@mui/material';
import {
  Map as MapIcon,
  Terrain as TerrainIcon,
  Timeline as TimelineIcon,
  Download as DownloadIcon,
  Share as ShareIcon,
  Delete as DeleteIcon,
  History as HistoryIcon,
} from '@mui/icons-material';

import FileUploader from '../components/FileUploader';
import MapViewer from '../components/MapViewer';
import ElevationProfile from '../components/ElevationProfile';
import { useApi } from '../services/ApiContext';

const GpsPage = () => {
  const [activeFile, setActiveFile] = useState(null);
  const [processedData, setProcessedData] = useState(null);
  const [recentFiles, setRecentFiles] = useState([]);
  const { gps } = useApi();

  const handleFileProcessed = (data) => {
    setProcessedData(data);
    setActiveFile(data);
    
    // Add to recent files
    setRecentFiles(prev => {
      const newFiles = [data, ...prev.filter(f => f.id !== data.id)];
      return newFiles.slice(0, 5); // Keep only 5 most recent
    });
  };

  const handleDeleteFile = (fileId) => {
    setRecentFiles(prev => prev.filter(f => f.id !== fileId));
    if (activeFile?.id === fileId) {
      setActiveFile(null);
      setProcessedData(null);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDistance = (meters) => {
    if (meters < 1000) return `${Math.round(meters)} m`;
    return `${(meters / 1000).toFixed(2)} km`;
  };

  return (
    <Container maxWidth="xl" className="animate-fade-in">
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <Box>
          <Typography variant="h3" sx={{ fontWeight: 700, fontFamily: 'Outfit', mb: 1 }}>
            GPS Analysis
          </Typography>
          <Typography variant="h6" color="text.secondary" sx={{ fontWeight: 400 }}>
            Analyze professional track data with C++ powered elevation correction.
          </Typography>
        </Box>
        <Stack direction="row" spacing={2}>
           {/* Actions could go here */}
        </Stack>
      </Box>

      <Grid container spacing={3}>
        {/* Left Column - Workspace Controls */}
        <Grid item xs={12} md={4} lg={3}>
          <Box className="glass-panel" sx={{ p: 3, mb: 3 }}>
            <Typography variant="subtitle2" sx={{ mb: 2, textTransform: 'uppercase', letterSpacing: 1, color: 'primary.light' }}>
               Data Source
            </Typography>
            <FileUploader onFileProcessed={handleFileProcessed} />
          </Box>

          <Box className="glass-panel" sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
                <HistoryIcon sx={{ color: 'text.secondary' }} />
                <Typography variant="h6" sx={{ fontFamily: 'Outfit' }}>Recent Tracks</Typography>
            </Box>
            
            {recentFiles.length === 0 ? (
              <Box sx={{ py: 4, textAlign: 'center', bgcolor: 'rgba(255,255,255,0.02)', borderRadius: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  No tracks uploaded yet
                </Typography>
              </Box>
            ) : (
              <Stack spacing={2}>
                {recentFiles.map((file) => (
                  <Card key={file.id} 
                    sx={{ 
                      bgcolor: activeFile?.id === file.id ? 'rgba(10, 132, 255, 0.1)' : 'rgba(255,255,255,0.03)',
                      border: activeFile?.id === file.id ? '1px solid rgba(10, 132, 255, 0.3)' : '1px solid rgba(255,255,255,0.05)',
                    }}
                  >
                    <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                        <Box sx={{ overflow: 'hidden' }}>
                          <Typography variant="subtitle2" noWrap sx={{ fontWeight: 600 }}>
                            {file.original_filename}
                          </Typography>
                          <Typography variant="caption" color="text.secondary" display="block">
                            {file.file_type.toUpperCase()} • {formatFileSize(file.file_size)}
                          </Typography>
                        </Box>
                        <IconButton size="small" onClick={() => handleDeleteFile(file.id)}>
                          <DeleteIcon fontSize="inherit" />
                        </IconButton>
                      </Box>
                      
                      <Stack direction="row" spacing={1} sx={{ mt: 1.5 }}>
                         <Chip size="small" label={formatDistance(file.statistics?.total_distance_2d || 0)} />
                         <Button 
                            size="small" 
                            variant={activeFile?.id === file.id ? "contained" : "text"}
                            onClick={() => { setActiveFile(file); setProcessedData(file); }}
                            sx={{ ml: 'auto', minWidth: 60, height: 24, fontSize: '0.7rem' }}
                         >
                           {activeFile?.id === file.id ? 'Active' : 'Load'}
                         </Button>
                      </Stack>
                    </CardContent>
                  </Card>
                ))}
              </Stack>
            )}
          </Box>
        </Grid>

        {/* Right Column - Map & Analysis */}
        <Grid item xs={12} md={8} lg={9}>
          <Box className="glass-panel" sx={{ p: 1, height: '600px', mb: 3, overflow: 'hidden' }}>
            <MapViewer trackData={activeFile} elevationData={activeFile?.elevation} />
          </Box>

          <Grid container spacing={3}>
            <Grid item xs={12} lg={8}>
              <Box className="glass-panel" sx={{ p: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                  <Typography variant="h6" sx={{ fontFamily: 'Outfit' }}>Elevation Profile</Typography>
                  {processedData && (
                    <Stack direction="row" spacing={1}>
                      <Button size="small" startIcon={<DownloadIcon />} variant="outlined">CSV</Button>
                      <Button size="small" startIcon={<DownloadIcon />} variant="outlined">GeoJSON</Button>
                    </Stack>
                  )}
                </Box>
                <ElevationProfile elevationData={processedData?.elevation} />
              </Box>
            </Grid>
            
            <Grid item xs={12} lg={4}>
              <Box className="glass-panel" sx={{ p: 3, height: '100%' }}>
                <Typography variant="h6" sx={{ mb: 3, fontFamily: 'Outfit' }}>Track Stats</Typography>
                {processedData ? (
                  <Stack spacing={2.5}>
                    <StatItem 
                        label="Distance" 
                        value={formatDistance(processedData.statistics?.total_distance_2d || 0)} 
                        icon={<TimelineIcon sx={{ color: 'primary.main' }} />} 
                    />
                    <StatItem 
                        label="Elevation Gain" 
                        value={`${Math.round(processedData.statistics?.total_elevation_gain || 0)} m`} 
                        icon={<TerrainIcon sx={{ color: 'success.main' }} />} 
                    />
                    <StatItem 
                        label="Points Count" 
                        value={processedData.statistics?.total_points || 0} 
                        icon={<MapIcon sx={{ color: 'secondary.main' }} />} 
                    />
                  </Stack>
                ) : (
                  <Box sx={{ py: 6, textAlign: 'center', opacity: 0.5 }}>
                    <Typography variant="body2">No data active</Typography>
                  </Box>
                )}
              </Box>
            </Grid>
          </Grid>
        </Grid>
      </Grid>
    </Container>
  );
};

const StatItem = ({ label, value, icon }) => (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 2, borderRadius: 2, bgcolor: 'rgba(255,255,255,0.02)' }}>
        {icon}
        <Box>
            <Typography variant="caption" color="text.secondary" display="block">{label}</Typography>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>{value}</Typography>
        </Box>
    </Box>
);

export default GpsPage;
