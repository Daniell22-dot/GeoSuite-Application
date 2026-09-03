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
    fontFamily: '"Inter", "Outfit", "Roboto", sans-serif',
    h1: { fontWeight: 700, fontFamily: 'Outfit' },
    h2: { fontWeight: 700, fontFamily: 'Outfit' },
    h3: { fontWeight: 700, fontFamily: 'Outfit' },
    h4: { fontWeight: 600, fontFamily: 'Outfit' },
    h5: { fontWeight: 600, fontFamily: 'Outfit' },
    h6: { fontWeight: 600, fontFamily: 'Outfit' },
    button: { textTransform: 'none', fontWeight: 500 },
  },
  shape: {
    borderRadius: 12,
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
          borderRadius: 8,
          boxShadow: 'none',
          '&:hover': { boxShadow: '0 4px 12px rgba(10, 132, 255, 0.3)' },
        },
        containedPrimary: {
          background: 'linear-gradient(135deg, #0a84ff 0%, #0060df 100%)',
        }
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          backgroundColor: 'rgba(30, 41, 59, 0.7)',
          backdropFilter: 'blur(12px)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          border: '1px solid rgba(255, 255, 255, 0.08)',
          background: 'rgba(255, 255, 255, 0.03)',
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
          
          <Box
            component="footer"
            sx={{
              py: 3,
              px: 4,
              mt: 'auto',
              borderTop: '1px solid rgba(255, 255, 255, 0.05)',
              background: 'rgba(15, 23, 42, 0.4)',
              backdropFilter: 'blur(10px)',
            }}
          >
            <Container maxWidth="xl">
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <TerrainIcon sx={{ color: 'primary.main', fontSize: 20 }} />
                  <Typography variant="body2" sx={{ fontWeight: 600, fontFamily: 'Outfit', color: 'text.secondary' }}>
                    {config?.appName || 'GeoSuite'} v{config?.appVersion || '2.0'}
                  </Typography>
                </Box>
                <Box sx={{ fontSize: '0.75rem', color: 'text.secondary', opacity: 0.7 }}>
                  SURVEY • DRONE • TRANSFORM • GPS • MARINE • WATERSHED • {new Date().getFullYear()}
                </Box>
              </Box>
            </Container>
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