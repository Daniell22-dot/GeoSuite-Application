import React, { useState, useEffect } from 'react';
import {
  Container,
  Grid,
  Typography,
  Box,
  Button,
  Tabs,
  Tab,
  Slider,
  FormControlLabel,
  Switch,
  Chip,
  Alert,
  CircularProgress,
  IconButton,
  Tooltip,
  MenuItem,
  Select,
  FormControl,
  Stack,
  Fade,
} from '@mui/material';
import {
  Upload as UploadIcon,
  Map as MapIcon,
  Waves as WavesIcon,
  Depth as DepthIcon,
  Download as DownloadIcon,
  Merge as MergeIcon,
  Settings as SettingsIcon,
  Visibility as VisibilityIcon,
} from '@mui/icons-material';

import MarineChartViewer from '../components/MarineChartViewer';
import { useMarine, useApi } from '../services/ApiContext';

const MarinePage = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [chartFiles, setChartFiles] = useState([]);
  const [activeChart, setActiveChart] = useState(null);
  const [layers, setLayers] = useState({ chart: true, soundings: true, contours: true, navigation: true, depth: true });
  const [depthRange, setDepthRange] = useState([0, 100]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const { marine } = useMarine();
  const { request } = useApi();

  const handleFileUpload = async (event) => {
    const files = Array.from(event.target.files);
    if (files.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const uploadedCharts = [];
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        const response = await request('post', '/api/v1/marine/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
        uploadedCharts.push({ ...response, originalFile: file });
      }
      setChartFiles(prev => [...prev, ...uploadedCharts]);
      if (!activeChart && uploadedCharts.length > 0) setActiveChart(uploadedCharts[0]);
    } catch (err) {
      setError(err.message || 'Failed to upload chart files');
    } finally {
      setLoading(false);
    }
  };

  const mergeCharts = async () => {
    if (chartFiles.length < 2) { setError('Need at least 2 charts to merge'); return; }
    setLoading(true);
    setError(null);
    try {
      const chartPaths = chartFiles.map(chart => chart.file_path);
      const response = await marine.mergeCharts(chartPaths, 'geotiff');
      const mergedChart = { id: `merged_${Date.now()}`, name: 'Merged Chart', file_path: response.output_path, metadata: { source: 'merged', charts_merged: chartFiles.length }, success: true };
      setChartFiles(prev => [...prev, mergedChart]);
      setActiveChart(mergedChart);
    } catch (err) {
      setError(err.message || 'Merge failed');
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
            MARINE CHARTING
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 600 }}>
             Advanced hydrographic analysis workbench. Process nautical charts, extract bathymetric soundings, and perform seamless multi-source merges.
          </Typography>
        </Box>
        <Stack direction="row" spacing={2}>
           <Button variant="contained" component="label" startIcon={<UploadIcon />} sx={{ px: 3, fontWeight: 600 }}>
              IMPORT CHARTS
              <input type="file" hidden accept=".kap,.bsb,.dwg,.dxf" multiple onChange={handleFileUpload} />
           </Button>
        </Stack>
      </Box>

      <Grid container spacing={4}>
        {/* Sidebar Controls */}
        <Grid item xs={12} md={3.5}>
          <Stack spacing={3}>
            {/* Chart Inventory */}
            <Box className="glass-panel" sx={{ p: 3 }}>
              <Typography variant="subtitle2" sx={{ fontFamily: 'Outfit', fontWeight: 600, mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                <VisibilityIcon fontSize="small" color="primary"/> LOADED CHARTS
              </Typography>
              
              <Stack spacing={1} sx={{ maxHeight: 300, overflowY: 'auto', pr: 1 }}>
                {chartFiles.length === 0 ? (
                  <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>No charts loaded.</Typography>
                ) : (
                  chartFiles.map((chart) => (
                    <Box key={chart.id} onClick={() => setActiveChart(chart)}
                      sx={{ p: 1.5, borderRadius: '8px', cursor: 'pointer', border: '1px solid', borderColor: activeChart?.id === chart.id ? 'primary.main' : 'rgba(255,255,255,0.05)', bgcolor: activeChart?.id === chart.id ? 'rgba(10, 132, 255, 0.1)' : 'transparent', transition: 'all 0.2s' }}>
                      <Typography variant="caption" sx={{ fontWeight: 600, display: 'block' }}>{chart.name || chart.original_filename}</Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.6rem' }}>{chart.file_type?.toUpperCase()} • {chart.metadata?.scale ? `1:${chart.metadata.scale}` : 'Scale N/A'}</Typography>
                    </Box>
                  ))
                )}
              </Stack>
            </Box>

            {/* Analysis Workspace */}
            {activeChart && (
              <Box className="glass-panel" sx={{ p: 3 }}>
                <Typography variant="subtitle2" sx={{ fontFamily: 'Outfit', fontWeight: 600, mb: 2 }}>ANALYSIS TOOLS</Typography>
                <Stack spacing={2}>
                  <Box>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>Active Layers</Typography>
                    <Grid container spacing={1}>
                      {Object.keys(layers).map(k => (
                        <Grid item xs={6} key={k}>
                          <FormControlLabel
                            control={<Switch size="small" checked={layers[k]} onChange={() => setLayers(p => ({ ...p, [k]: !p[k] }))} />}
                            label={<Typography variant="caption" sx={{ textTransform: 'capitalize' }}>{k}</Typography>}
                          />
                        </Grid>
                      ))}
                    </Grid>
                  </Box>
                  
                  <Box>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5 }}>Depth Filter ({depthRange[0]}m - {depthRange[1]}m)</Typography>
                    <Slider value={depthRange} onChange={(e, v) => setDepthRange(v)} min={0} max={200} size="small" />
                  </Box>

                  <Stack spacing={1} sx={{ pt: 2 }}>
                    <Button variant="outlined" startIcon={<DepthIcon />} fullWidth disabled={loading}>EXTRACT SOUNDINGS</Button>
                    <Button variant="outlined" startIcon={<MergeIcon />} fullWidth onClick={mergeCharts} disabled={chartFiles.length < 2 || loading}>MERGE ACTIVE SET</Button>
                    <Button variant="outlined" startIcon={<DownloadIcon />} fullWidth>EXPORT GEOTIFF</Button>
                  </Stack>
                </Stack>
              </Box>
            )}

            {error && <Alert severity="error" className="glass-panel" sx={{ border: 'none', bgcolor: 'rgba(244, 67, 54, 0.1)' }}>{error}</Alert>}
          </Stack>
        </Grid>

        {/* Main Viewer */}
        <Grid item xs={12} md={8.5}>
          <Box className="glass-panel" sx={{ height: '75vh', position: 'relative', overflow: 'hidden' }}>
            {activeChart ? (
              <MarineChartViewer chartData={activeChart} layers={layers} depthRange={depthRange} />
            ) : (
              <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', opacity: 0.5 }}>
                <WavesIcon sx={{ fontSize: 80, color: 'primary.main', mb: 2, opacity: 0.3 }} />
                <Typography variant="h6" sx={{ fontFamily: 'Outfit' }}>Select or Import Chart</Typography>
                <Typography variant="body2">Awaiting nautical data for vertical profile analysis.</Typography>
              </Box>
            )}
            
            {loading && (
              <Box sx={{ position: 'absolute', inset: 0, zIndex: 10, bgcolor: 'rgba(15,23,42,0.6)', backdropFilter: 'blur(4px)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                <CircularProgress size={40} thickness={4} />
                <Typography variant="caption" sx={{ mt: 2, letterSpacing: 1, fontWeight: 600 }}>PROCESSING CHART DATA...</Typography>
              </Box>
            )}
          </Box>
        </Grid>
      </Grid>
    </Container>
  );
};

export default MarinePage;