import React, { useState, useEffect } from 'react';
import {
  Container,
  Grid,
  Typography,
  Box,
  Button,
  FormControl,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  IconButton,
  Tooltip,
  Chip,
  Stack,
  Fade,
} from '@mui/material';
import {
  Upload as UploadIcon,
  Terrain as TerrainIcon,
  Water as WaterIcon,
  Timeline as TimelineIcon,
  Science as ScienceIcon,
  Download as DownloadIcon,
  PlayArrow as PlayArrowIcon,
} from '@mui/icons-material';

import MapViewer from '../components/MapViewer';
import WatershedTools from '../components/WatershedTools';
import { useWatershed, useApi } from '../services/ApiContext';
import { calculateBounds, formatArea, formatDistance } from '../services/gisUtils';

const WatershedPage = () => {
  const [demFile, setDemFile] = useState(null);
  const [pourPoint, setPourPoint] = useState(null);
  const [analysisResults, setAnalysisResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const { request } = useApi();

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const response = await request('post', '/api/v1/watershed/upload-dem', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      setDemFile(response);
    } catch (err) {
      setError(err.message || 'Failed to upload DEM');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth={false} sx={{ py: 4, px: { xs: 2, md: 4 } }}>
      {/* Header Area */}
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <Box>
          <Typography variant="h4" sx={{ fontFamily: 'Outfit', fontWeight: 700, letterSpacing: -0.5, mb: 1 }}>
            WATERSHED ANALYSIS
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 600 }}>
             Delineate watersheds, extract stream networks, and perform hydrological modeling using advanced terrain processing.
          </Typography>
        </Box>
        <Stack direction="row" spacing={2}>
           <Button variant="contained" component="label" startIcon={<UploadIcon />} sx={{ px: 3, fontWeight: 600 }}>
              UPLOAD DEM
              <input type="file" hidden accept=".tif,.tiff,.hgt,.asc,.dem" onChange={handleFileUpload} />
           </Button>
        </Stack>
      </Box>

      <Grid container spacing={4}>
        {/* Workspace Column */}
        <Grid item xs={12}>
          <Box className="glass-panel" sx={{ height: '75vh', position: 'relative', overflow: 'hidden', p: 0 }}>
             {demFile ? (
                <WatershedTools demData={demFile} onAnalysisComplete={setAnalysisResults} />
             ) : (
                <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', opacity: 0.5 }}>
                  <TerrainIcon sx={{ fontSize: 80, color: 'primary.main', mb: 2, opacity: 0.3 }} />
                  <Typography variant="h6" sx={{ fontFamily: 'Outfit' }}>Awaiting Elevation Data</Typography>
                  <Typography variant="body2">Upload a Digital Elevation Model (DEM) to start hydrological delineation.</Typography>
                </Box>
             )}

             {loading && (
               <Box sx={{ position: 'absolute', inset: 0, zIndex: 10, bgcolor: 'rgba(15,23,42,0.6)', backdropFilter: 'blur(4px)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                 <CircularProgress size={40} thickness={4} />
                 <Typography variant="caption" sx={{ mt: 2, letterSpacing: 1, fontWeight: 600 }}>PROCESSING ELEVATION MODEL...</Typography>
               </Box>
             )}
          </Box>
        </Grid>

        {/* Results / Details Overview */}
        {analysisResults && (
           <Grid item xs={12}>
              <Box className="glass-panel" sx={{ p: 4 }}>
                 <Typography variant="subtitle1" sx={{ fontFamily: 'Outfit', fontWeight: 600, mb: 3 }}>SESSION SUMMARY</Typography>
                 <Grid container spacing={4}>
                    <AnalysisMetric label="Watershed Area" value={`${analysisResults.watershed?.area_km2?.toFixed(2)} km²`} />
                    <AnalysisMetric label="Stream Length" value={`${analysisResults.streams?.total_length_km?.toFixed(2)} km`} />
                    <AnalysisMetric label="Peak Elevation" value={`${analysisResults.watershed?.elevation_stats?.max?.toFixed(0)} m`} />
                    <AnalysisMetric label="Relief Ratio" value={(analysisResults.watershed?.elevation_stats?.relief / (analysisResults.watershed?.area_km2 * 1000)).toFixed(4)} />
                 </Grid>
              </Box>
           </Grid>
        )}
      </Grid>
    </Container>
  );
};

const AnalysisMetric = ({ label, value }) => (
  <Grid item xs={12} sm={6} md={3}>
    <Box sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
      <Typography variant="h5" sx={{ fontFamily: 'Outfit', fontWeight: 700 }}>{value}</Typography>
      <Typography variant="caption" color="text.secondary" sx={{ letterSpacing: 1 }}>{label.toUpperCase()}</Typography>
    </Box>
  </Grid>
);

export default WatershedPage;