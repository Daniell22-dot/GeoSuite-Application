import React, { useState, useEffect } from 'react';
import { Container, Grid, Typography, Box, Paper } from '@mui/material';
import Terminal from '../components/Terminal';
import { Terminal as TerminalIcon, Info as InfoIcon } from '@mui/icons-material';
import { useAppConfig } from '../services/gisUtils';

const TerminalPage = () => {
  const [socketUrl, setSocketUrl] = useState('');
  const { config } = useAppConfig();

  useEffect(() => {
    const apiBase = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    const wsPath = config?.terminalWsPath || '/api/v1/terminal/ws';
    const token = localStorage.getItem('auth_token');
    const url = new URL(apiBase.replace(/^http/, 'ws') + wsPath);
    if (token) url.searchParams.set('token', token);
    setSocketUrl(url.toString());
  }, [config]);

  return (
    <Container maxWidth={false} sx={{ py: 4, px: { xs: 2, md: 4 } }}>
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <Box>
          <Typography variant="h4" sx={{ fontFamily: 'Outfit', fontWeight: 700, letterSpacing: -0.5, mb: 1 }}>
            INTEGRATED TERMINAL
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 600 }}>
             Direct console access to the GeoSuite engine. Execute GDAL, Whitebox, and custom C++ analytical tools.
          </Typography>
        </Box>
        <Box sx={{ p: 1.5, borderRadius: '12px', bgcolor: 'rgba(10, 132, 255, 0.05)', border: '1px solid rgba(10, 132, 255, 0.1)', display: 'flex', alignItems: 'center', gap: 1.5 }}>
           <TerminalIcon color="primary" />
           <Typography variant="overline" sx={{ fontWeight: 600, color: 'primary.main', letterSpacing: 1.5 }}>SESSION ACTIVE</Typography>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* Terminal Area */}
        <Grid item xs={12} lg={9}>
          <Box className="glass-panel" sx={{ height: '70vh', p: 1, position: 'relative', overflow: 'hidden', bgcolor: 'rgba(15, 23, 42, 0.4)' }}>
            <Terminal socketUrl={socketUrl} />
          </Box>
        </Grid>

        {/* Info Column */}
        <Grid item xs={12} lg={3}>
          <Box className="glass-panel" sx={{ p: 3, height: '100%' }}>
            <Typography variant="subtitle2" sx={{ fontFamily: 'Outfit', fontWeight: 600, mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
              <InfoIcon fontSize="small" color="primary"/> COMMAND GUIDE
            </Typography>
            
            <Box sx={{ mb: 3 }}>
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5, letterSpacing: 0.5 }}>GEOSPATIAL CORE</Typography>
              <Box className="code-snippet-small" sx={{ p: 1.5, mb: 1, bgcolor: 'rgba(255,255,255,0.03)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                <Typography variant="caption" component="pre" sx={{ fontStyle: 'italic', m: 0 }}>gdalinfo --version</Typography>
              </Box>
              <Box className="code-snippet-small" sx={{ p: 1.5, mb: 1, bgcolor: 'rgba(255,255,255,0.03)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                <Typography variant="caption" component="pre" sx={{ fontStyle: 'italic', m: 0 }}>ogr2ogr --formats</Typography>
              </Box>
            </Box>

            <Box sx={{ mb: 3 }}>
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5, letterSpacing: 0.5 }}>WATERSHED UTILS</Typography>
              <Box className="code-snippet-small" sx={{ p: 1.5, mb: 1, bgcolor: 'rgba(255,255,255,0.03)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                <Typography variant="caption" component="pre" sx={{ fontStyle: 'italic', m: 0 }}>whitebox_tools --help</Typography>
              </Box>
            </Box>

            <Box sx={{ mt: 'auto', pt: 2 }}>
              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.3)', lineHeight: 1.4 }}>
                * All commands execute within the /app/data shared volume. Use this console to perform manual script execution or data debugging.
              </Typography>
            </Box>
          </Box>
        </Grid>
      </Grid>
    </Container>
  );
};

export default TerminalPage;
