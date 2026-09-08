import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';

// Components
import Dashboard from './components/Dashboard';
import Navigation from './components/Navigation';
import HomePage from './pages/HomePage';
import GpsPage from './pages/GpsPage';
import MarinePage from './pages/MarinePage';
import WatershedPage from './pages/WatershedPage';
import TerminalPage from './pages/TerminalPage';
import DroneProcessingPage from './pages/DroneProcessingPage';
import TransformPage from './pages/TransformPage';
import DigitizePage from './pages/DigitizePage';

// Services
import { ApiProvider } from './services/ApiContext';
import { useAppConfig } from './services/gisUtils';

// Icons
import { Terrain as TerrainIcon } from '@mui/icons-material';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#0a84ff',
      light: '#409fff',
      dark: '#0060df',
    },
    secondary: {
      main: '#5e5ce6',
      light: '#7d7aff',
      dark: '#4845d2',
    },
    background: {
      default: '#0f172a',
      paper: 'rgba(30, 41, 59, 0.7)',
    },
    divider: 'rgba(255, 255, 255, 0.08)',
    text: {
      primary: '#f8fafc',
      secondary: '#94a3b8',
    },
  },
  typography: {
    fontFamily: '"Droid Sans", "Ubuntu", "Segoe UI", "Roboto", sans-serif',
    h1: { fontWeight: 700, fontSize: '2rem', lineHeight: 1.2 },
    h2: { fontWeight: 700, fontSize: '1.6rem', lineHeight: 1.25 },
    h3: { fontWeight: 700, fontSize: '1.4rem', lineHeight: 1.3 },
    h4: { fontWeight: 600, fontSize: '1.15rem', lineHeight: 1.35 },
    h5: { fontWeight: 600, fontSize: '1rem', lineHeight: 1.4 },
    h6: { fontWeight: 600, fontSize: '0.9rem', lineHeight: 1.45 },
    subtitle1: { fontSize: '0.85rem' },
    subtitle2: { fontSize: '0.78rem' },
    body1: { fontSize: '0.825rem' },
    body2: { fontSize: '0.75rem' },
    button: { textTransform: 'none', fontWeight: 500, fontSize: '0.8rem' },
    caption: { fontSize: '0.7rem' },
    overline: { fontSize: '0.65rem' },
  },
  shape: {
    borderRadius: 3,
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          scrollbarColor: "rgba(255,255,255,0.1) transparent",
          "&::-webkit-scrollbar, & *::-webkit-scrollbar": {
            width: 8,
          },
          "&::-webkit-scrollbar-thumb, & *::-webkit-scrollbar-thumb": {
            borderRadius: 8,
            backgroundColor: "rgba(255,255,255,0.1)",
          },
          "&::-webkit-scrollbar-thumb:focus, & *::-webkit-scrollbar-thumb:focus": {
            backgroundColor: "rgba(255,255,255,0.2)",
          },
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 3,
          boxShadow: 'none',
          minHeight: 32,
          '&:hover': { boxShadow: 'none' },
        },
        containedPrimary: {
          background: '#0a84ff',
        },
        sizeLarge: {
          minHeight: 38,
          padding: '0.5rem 1.5rem',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          backgroundColor: 'rgba(30, 41, 59, 0.72)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          boxShadow: '0 1px 2px rgba(0, 0, 0, 0.25)',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 3,
          border: '1px solid rgba(255, 255, 255, 0.08)',
          background: 'rgba(30, 41, 59, 0.72)',
        },
      },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          borderRadius: 3,
          minHeight: 32,
        },
      },
    },
    MuiMenuItem: {
      styleOverrides: {
        root: {
          fontSize: '0.8rem',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          height: 24,
          fontSize: '0.7rem',
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          fontSize: '0.75rem',
          borderColor: 'rgba(255, 255, 255, 0.08)',
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          fontSize: '0.8rem',
          minHeight: 40,
        },
      },
    },
  },
});

const AppInner = () => {
  const [activeView, setActiveView] = useState('home');
  const { config } = useAppConfig();

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', minHeight: '100vh', background: 'transparent' }}>
        <Navigation activeView={activeView} setActiveView={setActiveView} />
        
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            height: '100vh',
            overflow: 'auto',
            display: 'flex',
            flexDirection: 'column',
            position: 'relative',
            zIndex: 1,
          }}
        >
          <Container maxWidth="xl" sx={{ mt: 4, mb: 4, flex: 1 }}>
            <Routes>
              <Route path="/" element={<Navigate to="/home" replace />} />
              <Route path="/home" element={<HomePage />} />
              <Route path="/drone" element={<DroneProcessingPage />} />
              <Route path="/digitize" element={<DigitizePage />} />
              <Route path="/transform" element={<TransformPage />} />
              <Route path="/gps" element={<GpsPage />} />
              <Route path="/marine" element={<MarinePage />} />
              <Route path="/watershed" element={<WatershedPage />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/terminal" element={<TerminalPage />} />
            </Routes>
          </Container>
          
          <Box component="footer" className="qgis-statusbar">
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, minWidth: 0, overflow: 'hidden' }}>
              <Box className="sb-item">
                <TerrainIcon sx={{ color: 'primary.main', fontSize: 16 }} />
                <Box component="span" sx={{ fontWeight: 600, color: 'text.primary' }}>
                  {config?.appName || 'GeoSuite'} v{config?.appVersion || '2.0'}
                </Box>
              </Box>
              <Box className="sb-sep" />
              <Box className="sb-item">
                <Box component="span">CRS</Box>
                <Box component="span" sx={{ color: 'primary.light' }}>EPSG:21037</Box>
                <Box component="span" sx={{ opacity: 0.7 }}>Arc 1960 / UTM zone 37S</Box>
              </Box>
              <Box className="sb-sep" />
              <Box className="sb-item sb-coord">X 285 000.000</Box>
              <Box className="sb-item sb-coord">Y 9 892 000.000</Box>
              <Box className="sb-item sb-coord">Lat 0.000000°</Box>
              <Box className="sb-item sb-coord">Lon 36.000000°</Box>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Box className="sb-item">Scale 1:2 500</Box>
              <Box className="sb-sep" />
              <Box className="sb-item">100%</Box>
              <Box className="sb-sep" />
              <Box className="sb-item"></Box>
              <Box className="sb-item">© {new Date().getFullYear()}</Box>
            </Box>
          </Box>
        </Box>
      </Box>
    </ThemeProvider>
  );
};

function App() {
  return (
    <ApiProvider>
      <Router>
        <AppInner />
      </Router>
    </ApiProvider>
  );
}

export default App;