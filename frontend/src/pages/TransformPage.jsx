import React, { useState, useEffect } from 'react';
import {
  Container,
  Grid,
  Typography,
  Box,
  Button,
  Card,
  CardContent,
  TextField,
  MenuItem,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Tooltip,
  Tabs,
  Tab,
  Divider,
  CircularProgress,
  Snackbar,
  Select,
  FormControl,
  InputLabel,
} from '@mui/material';
import {
  Transform as TransformIcon,
  SwapHoriz as SwapIcon,
  ContentCopy as CopyIcon,
  Download as DownloadIcon,
  Upload as UploadIcon,
  CheckCircle as CheckIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';

import { useTransform, useApi } from '../services/ApiContext';

const TransformPage = () => {
  const [zones, setZones] = useState([]);
  const [methods, setMethods] = useState(['geodetic', 'polynomial', 'helmert']);
  const [tab, setTab] = useState(0);
  const [direction, setDirection] = useState('cassini_to_utm');
  const [zone, setZone] = useState('zone_3');
  const [method, setMethod] = useState('geodetic');
  const [loading, setLoading] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '' });

  const { transformSingle, transformBulk, detectZone } = useTransform();
  const { request } = useApi();

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const data = await request('get', '/api/v1/config');
      if (data) {
        setZones(data.transformZones || []);
        setMethods(data.transformMethods || ['geodetic', 'polynomial', 'helmert']);
      }
    } catch (err) {
      console.error('Failed to load transform config:', err);
    }
  };

  const handleSingleTransform = async () => {
    const e = parseFloat(singleInput.easting);
    const n = parseFloat(singleInput.northing);
    if (!e || !n) return;
    setLoading(true);
    try {
      const result = await transformSingle(e, n, direction, zone, method);
      setSingleResult({
        input: { easting: e, northing: n },
        output: { easting: result.output.easting, northing: result.output.northing },
        zone: result.geographic ? `Zone based on lat ${result.geographic.latitude?.toFixed(4)}` : zone,
        method: result.method,
      });
    } catch (err) {
      setSnackbar({ open: true, message: err.message || 'Transform failed' });
    } finally {
      setLoading(false);
    }
  };

  const handleBulkTransform = async () => {
    if (!bulkInput.trim()) return;
    setLoading(true);
    try {
      const lines = bulkInput.trim().split('\n');
      const coordinates = lines.map(line => {
        const parts = line.split(/[,\t]+/).map(s => s.trim());
        return { easting: parseFloat(parts[0]), northing: parseFloat(parts[1]) };
      }).filter(c => !isNaN(c.easting) && !isNaN(c.northing));

      const result = await transformBulk(coordinates, direction, zone, method);
      setBulkResults((result.results || []).map((r, idx) => ({
        id: idx + 1,
        inputE: r.input.easting,
        inputN: r.input.northing,
        outputE: r.output.easting,
        outputN: r.output.northing,
      })));
    } catch (err) {
      setSnackbar({ open: true, message: err.message || 'Bulk transform failed' });
    } finally {
      setLoading(false);
    }
  };

  const handleCopyResult = (text) => {
    navigator.clipboard.writeText(text);
    setSnackbar({ open: true, message: 'Copied to clipboard' });
  };

  const methodDescription = {
    geodetic: 'Full geodetic computation through Clarke 1880 ellipsoid. Most accurate.',
    polynomial: 'Uses survey polynomial formulae from Excel coefficient files.',
    helmert: '7-parameter similarity transformation. Good for localized areas.',
  };

  return (
    <Box className="animate-fade-in">
      <Container maxWidth="xl" sx={{ py: 4 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 700, fontFamily: 'Outfit', display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <TransformIcon sx={{ color: 'primary.main', fontSize: 36 }} />
              Coordinate Transformation
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Cassini-Soldner ↔ UTM Zone 37S — Geodetic, Polynomial & Helmert methods
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Chip
              label={`Direction: ${direction === 'cassini_to_utm' ? 'Cassini → UTM' : 'UTM → Cassini'}`}
              color="primary"
              variant="outlined"
            />
            <Tooltip title="Swap direction">
              <IconButton
                onClick={() => setDirection(d => d === 'cassini_to_utm' ? 'utm_to_cassini' : 'cassini_to_utm')}
                color="primary"
              >
                <SwapIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        <Grid container spacing={3}>
          {/* Controls */}
          <Grid item xs={12} md={4}>
            <Card className="glass-card">
              <CardContent>
                <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>Settings</Typography>

                <FormControl fullWidth sx={{ mb: 2 }}>
                  <InputLabel>Cassini Zone</InputLabel>
                  <Select
                    value={zone}
                    label="Cassini Zone"
                    onChange={(e) => setZone(e.target.value)}
                  >
                    {zones.map(z => (
                      <MenuItem key={z.value} value={z.value}>{z.label}</MenuItem>
                    ))}
                  </Select>
                </FormControl>

                <FormControl fullWidth sx={{ mb: 3 }}>
                  <InputLabel>Method</InputLabel>
                  <Select
                    value={method}
                    label="Method"
                    onChange={(e) => setMethod(e.target.value)}
                  >
                    {methods.map(m => (
                      <MenuItem key={m} value={m}>{m.charAt(0).toUpperCase() + m.slice(1)}</MenuItem>
                    ))}
                  </Select>
                </FormControl>

                <Divider sx={{ my: 2 }} />

                <Alert severity="info" sx={{ fontSize: '0.8rem' }}>
                  {methodDescription[method] || 'Select a transformation method.'}
                </Alert>

                <Box sx={{ mt: 3, p: 2, bgcolor: 'rgba(255,255,255,0.03)', borderRadius: 2 }}>
                  <Typography variant="caption" color="text.secondary">
                    Datum: Arc 1960 / Clarke 1880<br />
                    Ellipsoid: Clarke 1880 (R)<br />
                    UTM Zone: 37S (Kenya)<br />
                    Method: {method.charAt(0).toUpperCase() + method.slice(1)}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Main Area */}
          <Grid item xs={12} md={8}>
            <Card className="glass-card">
              <CardContent>
                <Tabs
                  value={tab}
                  onChange={(_, v) => setTab(v)}
                  sx={{ mb: 3, borderBottom: '1px solid rgba(255,255,255,0.08)' }}
                >
                  <Tab label="Single Coordinate" />
                  <Tab label="Bulk Transform" />
                  <Tab label="Excel Upload" />
                </Tabs>

                {/* Single Coordinate Tab */}
                {tab === 0 && (
                  <Box>
                    <Grid container spacing={2} sx={{ mb: 3 }}>
                      <Grid item xs={6}>
                        <TextField
                          fullWidth
                          label={direction === 'cassini_to_utm' ? 'Cassini Easting' : 'UTM Easting'}
                          type="number"
                          value={singleInput.easting}
                          onChange={(e) => setSingleInput(p => ({ ...p, easting: e.target.value }))}
                          placeholder="e.g., 285000.000"
                        />
                      </Grid>
                      <Grid item xs={6}>
                        <TextField
                          fullWidth
                          label={direction === 'cassini_to_utm' ? 'Cassini Northing' : 'UTM Northing'}
                          type="number"
                          value={singleInput.northing}
                          onChange={(e) => setSingleInput(p => ({ ...p, northing: e.target.value }))}
                          placeholder="e.g., 9892000.000"
                        />
                      </Grid>
                    </Grid>
                    <Button
                      variant="contained"
                      onClick={handleSingleTransform}
                      disabled={loading || !singleInput.easting || !singleInput.northing}
                      sx={{ mb: 3 }}
                    >
                      {loading ? <CircularProgress size={20} sx={{ mr: 1 }} /> : <TransformIcon sx={{ mr: 1 }} />}
                      Transform
                    </Button>

                    {singleResult && (
                      <Alert severity="success" sx={{ mb: 2 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Box>
                            <Typography variant="body2" sx={{ fontWeight: 600 }}>
                              {direction === 'cassini_to_utm' ? 'UTM' : 'Cassini'} Result
                            </Typography>
                            <Typography variant="h6" sx={{ fontFamily: 'monospace', mt: 0.5 }}>
                              E: {singleResult.output.easting.toLocaleString()} &nbsp; N: {singleResult.output.northing.toLocaleString()}
                            </Typography>
                            <Typography variant="caption">Zone: {singleResult.zone} | Method: {singleResult.method}</Typography>
                          </Box>
                          <Tooltip title="Copy">
                            <IconButton onClick={() => handleCopyResult(`${singleResult.output.easting},${singleResult.output.northing}`)}>
                              <CopyIcon />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </Alert>
                    )}
                  </Box>
                )}

                {/* Bulk Transform Tab */}
                {tab === 1 && (
                  <Box>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      Enter coordinates one per line (easting,northing or easting northing)
                    </Typography>
                    <TextField
                      fullWidth
                      multiline
                      rows={8}
                      value={bulkInput}
                      onChange={(e) => setBulkInput(e.target.value)}
                      placeholder={`285000.000,9892000.000\n285100.000,9892100.000\n285200.000,9892200.000`}
                      sx={{ mb: 2, fontFamily: 'monospace' }}
                    />
                    <Button
                      variant="contained"
                      onClick={handleBulkTransform}
                      disabled={loading || !bulkInput.trim()}
                    >
                      {loading ? <CircularProgress size={20} sx={{ mr: 1 }} /> : <TransformIcon sx={{ mr: 1 }} />}
                      Transform All
                    </Button>

                    {bulkResults.length > 0 && (
                      <Box sx={{ mt: 3 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                          <Typography variant="subtitle2">Results ({bulkResults.length} points)</Typography>
                          <Tooltip title="Download CSV">
                            <IconButton size="small">
                              <DownloadIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </Box>
                        <TableContainer component={Paper} sx={{ maxHeight: 400 }}>
                          <Table size="small" stickyHeader>
                            <TableHead>
                              <TableRow>
                                <TableCell>#</TableCell>
                                <TableCell>Input E</TableCell>
                                <TableCell>Input N</TableCell>
                                <TableCell>Output E</TableCell>
                                <TableCell>Output N</TableCell>
                                <TableCell></TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {bulkResults.map(row => (
                                <TableRow key={row.id} hover>
                                  <TableCell>{row.id}</TableCell>
                                  <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{row.inputE.toLocaleString()}</TableCell>
                                  <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{row.inputN.toLocaleString()}</TableCell>
                                  <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.8rem', color: 'primary.light' }}>{row.outputE.toLocaleString()}</TableCell>
                                  <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.8rem', color: 'primary.light' }}>{row.outputN.toLocaleString()}</TableCell>
                                  <TableCell>
                                    <Tooltip title="Copy">
                                      <IconButton size="small" onClick={() => handleCopyResult(`${row.outputE},${row.outputN}`)}>
                                        <CopyIcon fontSize="small" />
                                      </IconButton>
                                    </Tooltip>
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </TableContainer>
                      </Box>
                    )}
                  </Box>
                )}

                {/* Excel Upload Tab */}
                {tab === 2 && (
                  <Box>
                    <Alert severity="info" sx={{ mb: 3 }}>
                      Upload an Excel file with coordinate columns. The system will auto-detect columns containing easting/northing values.
                    </Alert>
                    <Box
                      sx={{
                        border: '2px dashed rgba(255,255,255,0.1)',
                        borderRadius: 3,
                        p: 6,
                        textAlign: 'center',
                        cursor: 'pointer',
                        '&:hover': { borderColor: 'primary.light' },
                      }}
                    >
                      <UploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
                      <Typography color="text.secondary">
                        Drop Excel file here or click to browse
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Accepts .xlsx, .xls files
                      </Typography>
                    </Box>
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Container>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={2000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        message={snackbar.message}
      />
    </Box>
  );
};

export default TransformPage;
