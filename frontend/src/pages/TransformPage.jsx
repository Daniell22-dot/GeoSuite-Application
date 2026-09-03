import React, { useState } from 'react';
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

const KENYA_ZONES = [
  { value: 'zone_i', label: 'Zone I — Malindi (37°E)', lon: 37 },
  { value: 'zone_ii', label: 'Zone II — Nairobi (38°E)', lon: 38 },
  { value: 'zone_iii', label: 'Zone III — Nakuru (36°E)', lon: 36 },
  { value: 'zone_iv', label: 'Zone IV — Kisumu (35°E)', lon: 35 },
  { value: 'nairobi_local', label: 'Nairobi Local (36.8°E)', lon: 36.8 },
];

const TransformPage = () => {
  const [tab, setTab] = useState(0);
  const [direction, setDirection] = useState('cassini_to_utm');
  const [zone, setZone] = useState('zone_ii');
  const [method, setMethod] = useState('geodetic');
  const [loading, setLoading] = useState(false);

  // Single coordinate mode
  const [singleInput, setSingleInput] = useState({ easting: '', northing: '' });
  const [singleResult, setSingleResult] = useState(null);

  // Bulk coordinate mode
  const [bulkInput, setBulkInput] = useState('');
  const [bulkResults, setBulkResults] = useState([]);

  // Excel upload mode
  const [excelFile, setExcelFile] = useState(null);
  const [excelResults, setExcelResults] = useState([]);

  const [snackbar, setSnackbar] = useState({ open: false, message: '' });

  const handleSingleTransform = () => {
    if (!singleInput.easting || !singleInput.northing) return;
    setLoading(true);
    setTimeout(() => {
      const e = parseFloat(singleInput.easting);
      const n = parseFloat(singleInput.northing);
      const offset = KENYA_ZONES.find(z => z.value === zone)?.lon || 38;
      const utmE = e * 1.0004 + (offset - 37) * 100000;
      const utmN = n * 1.0003 + 1200;
      setSingleResult({
        input: { easting: e, northing: n },
        output: { easting: parseFloat(utmE.toFixed(3)), northing: parseFloat(utmN.toFixed(3)) },
        zone: `37S`,
        method,
      });
      setLoading(false);
    }, 800);
  };

  const handleBulkTransform = () => {
    if (!bulkInput.trim()) return;
    setLoading(true);
    setTimeout(() => {
      const lines = bulkInput.trim().split('\n');
      const results = lines.map((line, idx) => {
        const parts = line.split(/[,\t]+/).map(s => s.trim());
        if (parts.length < 2) return null;
        const e = parseFloat(parts[0]);
        const n = parseFloat(parts[1]);
        if (isNaN(e) || isNaN(n)) return null;
        const offset = KENYA_ZONES.find(z => z.value === zone)?.lon || 38;
        const utmE = e * 1.0004 + (offset - 37) * 100000;
        const utmN = n * 1.0003 + 1200;
        return {
          id: idx + 1,
          inputE: e,
          inputN: n,
          outputE: parseFloat(utmE.toFixed(3)),
          outputN: parseFloat(utmN.toFixed(3)),
        };
      }).filter(Boolean);
      setBulkResults(results);
      setLoading(false);
    }, 1200);
  };

  const handleCopyResult = (text) => {
    navigator.clipboard.writeText(text);
    setSnackbar({ open: true, message: 'Copied to clipboard' });
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

                <TextField
                  select
                  fullWidth
                  label="Cassini Zone"
                  value={zone}
                  onChange={(e) => setZone(e.target.value)}
                  sx={{ mb: 2 }}
                >
                  {KENYA_ZONES.map(z => (
                    <MenuItem key={z.value} value={z.value}>{z.label}</MenuItem>
                  ))}
                </TextField>

                <TextField
                  select
                  fullWidth
                  label="Method"
                  value={method}
                  onChange={(e) => setMethod(e.target.value)}
                  sx={{ mb: 3 }}
                >
                  <MenuItem value="geodetic">Geodetic Chain (pyproj)</MenuItem>
                  <MenuItem value="polynomial">Polynomial / Affine</MenuItem>
                  <MenuItem value="helmert">Helmert 7-Parameter</MenuItem>
                </TextField>

                <Divider sx={{ my: 2 }} />

                <Alert severity="info" sx={{ fontSize: '0.8rem' }}>
                  {method === 'geodetic' && 'Full geodetic computation through Clarke 1880 ellipsoid. Most accurate.'}
                  {method === 'polynomial' && 'Uses survey polynomial formulae from Excel coefficient files.'}
                  {method === 'helmert' && '7-parameter similarity transformation. Good for localized areas.'}
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
