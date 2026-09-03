import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  Container,
  Grid,
  Typography,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Alert,
  Stepper,
  Step,
  StepLabel,
  CircularProgress,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  IconButton,
  Tooltip,
  LinearProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import {
  Scanner as DigitizeIcon,
  CloudUpload as UploadIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Download as DownloadIcon,
  Visibility as ViewIcon,
  Settings as SettingsIcon,
  Map as MapIcon,
  MyLocation as BeaconIcon,
  Timeline as BoundaryIcon,
  ContentCopy as CopyIcon,
  PictureAsPdf as PdfIcon,
  Image as ImageIcon,
} from '@mui/icons-material';
import { useAppConfig } from '../services/gisUtils';

const DigitizePage = () => {
  const [uploadFile, setUploadFile] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [settings, setSettings] = useState({
    coordinateSystem: 'cassini',
    zone: 'zone_ii',
    confidenceThreshold: 0.7,
    detectBeacons: true,
    detectBoundaries: true,
    detectLabels: true,
    ocrEnabled: true,
  });
  const [previewOpen, setPreviewOpen] = useState(false);
  const { config } = useAppConfig();
  const zones = config?.transformZones || [];
  const maxUploadMB = config?.maxUploadSizeMB || 100;

  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      setUploadFile(acceptedFiles[0]);
      setResult(null);
    }
  }, []);

  const supportedTypes = config?.supportedFileTypes || {
    pdf: ['.pdf'],
    image: ['.jpg', '.jpeg', '.tif', '.tiff', '.png'],
    dxf: ['.dxf'],
    dwg: ['.dwg'],
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': supportedTypes.pdf || ['.pdf'],
      'image/*': supportedTypes.image || ['.jpg', '.jpeg', '.tif', '.tiff', '.png'],
      'application/dxf': supportedTypes.dxf || ['.dxf'],
      'application/acad': supportedTypes.dwg || ['.dwg'],
    },
    multiple: false,
    maxSize: maxUploadMB * 1024 * 1024,
  });

  const handleProcess = () => {
    if (!uploadFile) return;
    setProcessing(true);
    setProgress(0);
    const interval = setInterval(() => {
      setProgress(p => {
        if (p >= 100) {
          clearInterval(interval);
          setTimeout(() => {
            setProcessing(false);
            setResult({
              beacons: 24,
              boundaries: 12,
              labels: 18,
              area: 0.487,
              confidence: 0.92,
              beaconsDetected: [
                { id: 'B1', easting: 285000.123, northing: 9892000.456, type: 'iron_pin' },
                { id: 'B2', easting: 285050.789, northing: 9892000.123, type: 'concrete' },
                { id: 'B3', easting: 285050.456, northing: 9892050.789, type: 'iron_pin' },
                { id: 'B4', easting: 285000.789, northing: 9892050.123, type: 'concrete' },
              ],
              boundarySegments: [
                { from: 'B1', to: 'B2', distance: 50.0, bearing: 90 },
                { from: 'B2', to: 'B3', distance: 50.0, bearing: 0 },
                { from: 'B3', to: 'B4', distance: 50.0, bearing: 270 },
                { from: 'B4', to: 'B1', distance: 50.0, bearing: 180 },
              ],
              extractedLabels: [
                { text: 'L.R. 20946', type: 'title_reference', confidence: 0.95 },
                { text: 'P/REF/S/4782', type: 'plan_number', confidence: 0.88 },
                { text: 'SCALE 1:500', type: 'scale', confidence: 0.91 },
                { text: 'N', type: 'north_arrow', confidence: 0.97 },
              ],
            });
          }, 500);
          return 100;
        }
        return p + Math.random() * 15;
      });
    }, 300);
  };

  const handleExport = (format) => {
    // Placeholder for export functionality
    console.log(`Exporting as ${format}`);
  };

  return (
    <Box className="animate-fade-in">
      <Container maxWidth="xl" sx={{ py: 4 }}>
        {/* Header */}
        <Box sx={{ mb: 4 }}>
          <Typography variant="h4" sx={{ fontWeight: 700, fontFamily: 'Outfit', display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <DigitizeIcon sx={{ color: 'primary.main', fontSize: 36 }} />
            Survey Plan Digitizer
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Auto-extract beacons, boundaries & labels from scanned survey plans
          </Typography>
        </Box>

        {/* Processing Pipeline */}
        <Box sx={{ mb: 4 }}>
          <Stepper activeStep={processing ? 1 : result ? 3 : 0} alternativeLabel>
            <Step><StepLabel>Upload Plan</StepLabel></Step>
            <Step><StepLabel>CV Detection</StepLabel></Step>
            <Step><StepLabel>OCR & Parsing</StepLabel></Step>
            <Step><StepLabel>Vector Output</StepLabel></Step>
          </Stepper>
        </Box>

        <Grid container spacing={3}>
          {/* Upload + Settings */}
          <Grid item xs={12} md={4}>
            {/* Upload Zone */}
            <Card className="glass-card" sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>Upload Survey Plan</Typography>
                <Box
                  {...getRootProps()}
                  sx={{
                    border: '2px dashed',
                    borderColor: isDragActive ? 'primary.main' : uploadFile ? 'success.main' : 'rgba(255,255,255,0.1)',
                    borderRadius: 3,
                    p: 4,
                    textAlign: 'center',
                    cursor: 'pointer',
                    bgcolor: isDragActive ? 'rgba(10, 132, 255, 0.05)' : uploadFile ? 'rgba(76, 175, 80, 0.05)' : 'transparent',
                    transition: 'all 0.2s',
                    '&:hover': { borderColor: 'primary.light' },
                  }}
                >
                  <input {...getInputProps()} />
                  {uploadFile ? (
                    <>
                      <CheckIcon sx={{ fontSize: 40, color: 'success.main', mb: 1 }} />
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>{uploadFile.name}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {(uploadFile.size / 1024 / 1024).toFixed(2)} MB
                      </Typography>
                    </>
                  ) : (
                    <>
                      <UploadIcon sx={{ fontSize: 40, color: 'text.secondary', mb: 1 }} />
                      <Typography variant="body2" color="text.secondary">
                        Drop survey plan or click to browse
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        PDF, JPG, TIFF, DXF
                      </Typography>
                    </>
                  )}
                </Box>
              </CardContent>
            </Card>

            {/* Detection Settings */}
            <Card className="glass-card" sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 1 }}>
                  <SettingsIcon fontSize="small" /> Detection Settings
                </Typography>
                <TextField
                  select
                  fullWidth
                  label="Coordinate System"
                  value={settings.coordinateSystem}
                  onChange={(e) => setSettings(s => ({ ...s, coordinateSystem: e.target.value }))}
                  sx={{ mb: 2 }}
                >
                  <MenuItem value="cassini">Cassini-Soldner</MenuItem>
                  <MenuItem value="utm">UTM Zone 37S</MenuItem>
                  <MenuItem value="latlon">Latitude / Longitude</MenuItem>
                </TextField>
                <TextField
                  select
                  fullWidth
                  label="Cassini Zone"
                  value={settings.zone}
                  onChange={(e) => setSettings(s => ({ ...s, zone: e.target.value }))}
                  sx={{ mb: 2 }}
                >
                  {zones.map(z => (
                    <MenuItem key={z.value} value={z.value}>{z.label}</MenuItem>
                  ))}
                </TextField>
                <TextField
                  fullWidth
                  label="Confidence Threshold"
                  type="number"
                  value={settings.confidenceThreshold}
                  onChange={(e) => setSettings(s => ({ ...s, confidenceThreshold: parseFloat(e.target.value) }))}
                  inputProps={{ min: 0.1, max: 1, step: 0.1 }}
                  sx={{ mb: 2 }}
                />
              </CardContent>
            </Card>

            {/* Process Button */}
            <Button
              fullWidth
              variant="contained"
              size="large"
              onClick={handleProcess}
              disabled={!uploadFile || processing}
              sx={{ py: 1.5, borderRadius: 2 }}
            >
              {processing ? (
                <>
                  <CircularProgress size={20} sx={{ mr: 1 }} />
                  Processing... {Math.round(progress)}%
                </>
              ) : (
                <>
                  <DigitizeIcon sx={{ mr: 1 }} />
                  Digitize Plan
                </>
              )}
            </Button>
            {processing && (
              <LinearProgress variant="determinate" value={progress} sx={{ mt: 2, height: 6, borderRadius: 3 }} />
            )}
          </Grid>

          {/* Results */}
          <Grid item xs={12} md={8}>
            {result ? (
              <>
                {/* Summary Cards */}
                <Grid container spacing={2} sx={{ mb: 3 }}>
                  {[
                    { label: 'Beacons', value: result.beacons, icon: <BeaconIcon />, color: '#0a84ff' },
                    { label: 'Boundaries', value: result.boundaries, icon: <BoundaryIcon />, color: '#5e5ce6' },
                    { label: 'Labels', value: result.labels, icon: <DigitizeIcon />, color: '#ed6c02' },
                    { label: 'Area', value: `${result.area} ha`, icon: <MapIcon />, color: '#4caf50' },
                  ].map((stat, idx) => (
                    <Grid item xs={6} md={3} key={idx}>
                      <Card className="glass-card">
                        <CardContent sx={{ textAlign: 'center', py: 3 }}>
                          <Box sx={{ color: stat.color, mb: 1 }}>{stat.icon}</Box>
                          <Typography variant="h4" sx={{ fontWeight: 700 }}>{stat.value}</Typography>
                          <Typography variant="caption" color="text.secondary">{stat.label}</Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>

                {/* Confidence Alert */}
                <Alert
                  severity={result.confidence >= 0.85 ? 'success' : 'warning'}
                  sx={{ mb: 3 }}
                  action={
                    <Button color="inherit" size="small" onClick={() => setPreviewOpen(true)}>
                      View Details
                    </Button>
                  }
                >
                  Detection confidence: {(result.confidence * 100).toFixed(1)}% — {result.confidence >= 0.85 ? 'High quality extraction' : 'Review recommended'}
                </Alert>

                {/* Extracted Beacons */}
                <Card className="glass-card" sx={{ mb: 3 }}>
                  <CardContent>
                    <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                      <BeaconIcon sx={{ fontSize: 20, mr: 0.5, verticalAlign: 'middle', color: '#0a84ff' }} />
                      Detected Beacons ({result.beaconsDetected.length})
                    </Typography>
                    <TableContainer component={Paper} sx={{ maxHeight: 250 }}>
                      <Table size="small" stickyHeader>
                        <TableHead>
                          <TableRow>
                            <TableCell>Beacon</TableCell>
                            <TableCell>Easting</TableCell>
                            <TableCell>Northing</TableCell>
                            <TableCell>Type</TableCell>
                            <TableCell></TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {result.beaconsDetected.map((b, idx) => (
                            <TableRow key={idx} hover>
                              <TableCell sx={{ fontWeight: 600 }}>{b.id}</TableCell>
                              <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{b.easting.toLocaleString(undefined, { minimumFractionDigits: 3 })}</TableCell>
                              <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{b.northing.toLocaleString(undefined, { minimumFractionDigits: 3 })}</TableCell>
                              <TableCell>
                                <Chip label={b.type} size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} />
                              </TableCell>
                              <TableCell>
                                <Tooltip title="Copy coordinates">
                                  <IconButton size="small" onClick={() => navigator.clipboard.writeText(`${b.easting},${b.northing}`)}>
                                    <CopyIcon fontSize="small" />
                                  </IconButton>
                                </Tooltip>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </CardContent>
                </Card>

                {/* Boundary Segments */}
                <Card className="glass-card" sx={{ mb: 3 }}>
                  <CardContent>
                    <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                      <BoundaryIcon sx={{ fontSize: 20, mr: 0.5, verticalAlign: 'middle', color: '#5e5ce6' }} />
                      Boundary Segments ({result.boundarySegments.length})
                    </Typography>
                    <TableContainer component={Paper} sx={{ maxHeight: 250 }}>
                      <Table size="small" stickyHeader>
                        <TableHead>
                          <TableRow>
                            <TableCell>From</TableCell>
                            <TableCell>To</TableCell>
                            <TableCell>Distance (m)</TableCell>
                            <TableCell>Bearing</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {result.boundarySegments.map((seg, idx) => (
                            <TableRow key={idx} hover>
                              <TableCell>{seg.from}</TableCell>
                              <TableCell>{seg.to}</TableCell>
                              <TableCell sx={{ fontFamily: 'monospace' }}>{seg.distance.toFixed(2)}</TableCell>
                              <TableCell sx={{ fontFamily: 'monospace' }}>{seg.bearing.toFixed(1)}°</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </CardContent>
                </Card>

                {/* Extracted Labels */}
                <Card className="glass-card" sx={{ mb: 3 }}>
                  <CardContent>
                    <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                      OCR Extracted Labels
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                      {result.extractedLabels.map((label, idx) => (
                        <Chip
                          key={idx}
                          label={`${label.text} (${(label.confidence * 100).toFixed(0)}%)`}
                          color={label.confidence >= 0.9 ? 'success' : 'default'}
                          variant="outlined"
                        />
                      ))}
                    </Box>
                  </CardContent>
                </Card>

                {/* Export Buttons */}
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Button variant="contained" startIcon={<DownloadIcon />} onClick={() => handleExport('geojson')}>
                    Export GeoJSON
                  </Button>
                  <Button variant="outlined" startIcon={<DownloadIcon />} onClick={() => handleExport('shapefile')}>
                    Shapefile
                  </Button>
                  <Button variant="outlined" startIcon={<DownloadIcon />} onClick={() => handleExport('dxf')}>
                    DXF
                  </Button>
                  <Button variant="outlined" startIcon={<DownloadIcon />} onClick={() => handleExport('csv')}>
                    CSV Table
                  </Button>
                </Box>
              </>
            ) : (
              <Card className="glass-card">
                <CardContent>
                  <Box sx={{ textAlign: 'center', py: 12, color: 'text.secondary' }}>
                    <DigitizeIcon sx={{ fontSize: 72, opacity: 0.2, mb: 2 }} />
                    <Typography variant="h5" sx={{ fontWeight: 600, mb: 1 }}>No Results Yet</Typography>
                    <Typography variant="body1">
                      Upload a survey plan and click "Digitize Plan" to extract features
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            )}
          </Grid>
        </Grid>
      </Container>

      {/* Details Dialog */}
      <Dialog open={previewOpen} onClose={() => setPreviewOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Detection Details</DialogTitle>
        <DialogContent>
          {result && (
            <Box>
              <Typography variant="body2" sx={{ mb: 2 }}>
                The computer vision pipeline detected {result.beacons} beacons, {result.boundaries} boundary segments,
                and {result.labels} text labels with an overall confidence of {(result.confidence * 100).toFixed(1)}%.
              </Typography>
              <Alert severity="info">
                Review the extracted coordinates against the original plan before exporting.
                Confidence scores indicate the certainty of each detection.
              </Alert>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DigitizePage;
