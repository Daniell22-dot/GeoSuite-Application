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
  LinearProgress,
  IconButton,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  Alert,
  Stepper,
  Step,
  StepLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Tooltip,
  Divider,
  Badge,
} from '@mui/material';
import {
  Flight as DroneIcon,
  CloudUpload as UploadIcon,
  Delete as DeleteIcon,
  CheckCircle as CheckIcon,
  RadioButtonUnchecked as PendingIcon,
  HourglassBottom as ProcessingIcon,
  Download as DownloadIcon,
  Visibility as ViewIcon,
  Folder as FolderIcon,
  Image as ImageIcon,
  Map as MapIcon,
  Add as AddIcon,
  Info as InfoIcon,
} from '@mui/icons-material';

const STATUS_COLORS = {
  draft: 'default',
  uploaded: 'info',
  processing: 'warning',
  completed: 'success',
  failed: 'error',
};

const DroneProcessingPage = () => {
  const [surveys, setSurveys] = useState([]);
  const [activeSurvey, setActiveSurvey] = useState(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newSurveyName, setNewSurveyName] = useState('');
  const [newSurveyDesc, setNewSurveyDesc] = useState('');
  const [uploadProgress, setUploadProgress] = useState({});

  const onDrop = useCallback((acceptedFiles) => {
    if (!activeSurvey) return;
    acceptedFiles.forEach(file => {
      const fakeId = `upload-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      setUploadProgress(prev => ({ ...prev, [fakeId]: 0 }));
      let progress = 0;
      const interval = setInterval(() => {
        progress += Math.random() * 30;
        if (progress >= 100) {
          progress = 100;
          clearInterval(interval);
          setTimeout(() => {
            setUploadProgress(prev => {
              const next = { ...prev };
              delete next[fakeId];
              return next;
            });
            setSurveys(prev => prev.map(s => {
              if (s.id === activeSurvey.id) {
                return {
                  ...s,
                  images: [...s.images, { name: file.name, size: file.size, status: 'uploaded' }],
                  status: 'uploaded',
                };
              }
              return s;
            }));
            setActiveSurvey(prev => {
              if (prev && prev.id === activeSurvey.id) {
                return {
                  ...prev,
                  images: [...prev.images, { name: file.name, size: file.size, status: 'uploaded' }],
                  status: 'uploaded',
                };
              }
              return prev;
            });
          }, 500);
        }
        setUploadProgress(prev => ({ ...prev, [fakeId]: progress }));
      }, 200);
    });
  }, [activeSurvey]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpg', '.jpeg', '.tif', '.tiff', '.png'] },
    multiple: true,
  });

  const handleCreateSurvey = () => {
    if (!newSurveyName.trim()) return;
    const newSurvey = {
      id: `survey-${Date.now()}`,
      name: newSurveyName,
      description: newSurveyDesc,
      status: 'draft',
      images: [],
      createdAt: new Date().toISOString(),
    };
    setSurveys(prev => [...prev, newSurvey]);
    setActiveSurvey(newSurvey);
    setCreateDialogOpen(false);
    setNewSurveyName('');
    setNewSurveyDesc('');
  };

  const handleDeleteSurvey = (surveyId) => {
    setSurveys(prev => prev.filter(s => s.id !== surveyId));
    if (activeSurvey && activeSurvey.id === surveyId) setActiveSurvey(null);
  };

  const handleProcessSurvey = (surveyId) => {
    setSurveys(prev => prev.map(s =>
      s.id === surveyId ? { ...s, status: 'processing' } : s
    ));
    setTimeout(() => {
      setSurveys(prev => prev.map(s =>
        s.id === surveyId ? { ...s, status: 'completed' } : s
      ));
    }, 3000);
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <Box className="animate-fade-in">
      <Container maxWidth="xl" sx={{ py: 4 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 700, fontFamily: 'Outfit', display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <DroneIcon sx={{ color: 'primary.main', fontSize: 36 }} />
              Drone Survey Processing
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Upload drone imagery, process with OpenDroneMap, generate COGs and PMTiles
            </Typography>
          </Box>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCreateDialogOpen(true)}
            sx={{ borderRadius: '100px', px: 4 }}
          >
            New Survey
          </Button>
        </Box>

        <Grid container spacing={3}>
          {/* Survey List */}
          <Grid item xs={12} md={4}>
            <Card className="glass-card">
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                  Surveys ({surveys.length})
                </Typography>
                {surveys.length === 0 ? (
                  <Box sx={{ textAlign: 'center', py: 6, color: 'text.secondary' }}>
                    <FolderIcon sx={{ fontSize: 48, opacity: 0.3, mb: 1 }} />
                    <Typography variant="body2">No surveys yet</Typography>
                    <Typography variant="caption">Create a survey to get started</Typography>
                  </Box>
                ) : (
                  <List dense>
                    {surveys.map(survey => (
                      <ListItem
                        key={survey.id}
                        button
                        selected={activeSurvey?.id === survey.id}
                        onClick={() => setActiveSurvey(survey)}
                        sx={{
                          borderRadius: 2,
                          mb: 0.5,
                          '&.Mui-selected': { bgcolor: 'rgba(10, 132, 255, 0.15)' },
                        }}
                      >
                        <ListItemIcon sx={{ minWidth: 36 }}>
                          <Badge
                            badgeContent={survey.images.length}
                            color="primary"
                            sx={{ '& .MuiBadge-badge': { fontSize: '0.65rem' } }}
                          >
                            <DroneIcon fontSize="small" />
                          </Badge>
                        </ListItemIcon>
                        <ListItemText
                          primary={survey.name}
                          secondary={survey.status}
                          primaryTypographyProps={{ fontSize: '0.9rem', fontWeight: 500 }}
                          secondaryTypographyProps={{ fontSize: '0.75rem' }}
                        />
                        <ListItemSecondaryAction>
                          <Chip
                            label={survey.status}
                            size="small"
                            color={STATUS_COLORS[survey.status]}
                            sx={{ fontSize: '0.65rem', height: 22 }}
                          />
                        </ListItemSecondaryAction>
                      </ListItem>
                    ))}
                  </List>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* Main Workspace */}
          <Grid item xs={12} md={8}>
            {activeSurvey ? (
              <Card className="glass-card">
                <CardContent>
                  {/* Survey Header */}
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                    <Box>
                      <Typography variant="h5" sx={{ fontWeight: 700 }}>{activeSurvey.name}</Typography>
                      <Typography variant="body2" color="text.secondary">{activeSurvey.description || 'No description'}</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <Tooltip title="Process Survey">
                        <IconButton
                          color="primary"
                          onClick={() => handleProcessSurvey(activeSurvey.id)}
                          disabled={activeSurvey.images.length === 0 || activeSurvey.status === 'processing'}
                        >
                          <ProcessingIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete Survey">
                        <IconButton color="error" onClick={() => handleDeleteSurvey(activeSurvey.id)}>
                          <DeleteIcon />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </Box>

                  {/* Processing Pipeline Steps */}
                  <Box sx={{ mb: 4 }}>
                    <Stepper activeStep={
                      activeSurvey.status === 'draft' ? 0 :
                      activeSurvey.status === 'uploaded' ? 1 :
                      activeSurvey.status === 'processing' ? 2 :
                      activeSurvey.status === 'completed' ? 4 : 0
                    } alternativeLabel>
                      <Step><StepLabel>Create</StepLabel></Step>
                      <Step><StepLabel>Upload Images</StepLabel></Step>
                      <Step><StepLabel>ODM Processing</StepLabel></Step>
                      <Step><StepLabel>COG Conversion</StepLabel></Step>
                      <Step><StepLabel>Tile Generation</StepLabel></Step>
                    </Stepper>
                  </Box>

                  {/* Upload Zone */}
                  <Box
                    {...getRootProps()}
                    sx={{
                      border: '2px dashed',
                      borderColor: isDragActive ? 'primary.main' : 'rgba(255,255,255,0.1)',
                      borderRadius: 3,
                      p: 4,
                      textAlign: 'center',
                      cursor: 'pointer',
                      bgcolor: isDragActive ? 'rgba(10, 132, 255, 0.05)' : 'transparent',
                      transition: 'all 0.2s',
                      '&:hover': { borderColor: 'primary.light', bgcolor: 'rgba(10, 132, 255, 0.03)' },
                    }}
                  >
                    <input {...getInputProps()} />
                    <UploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
                    <Typography variant="body1" color="text.secondary">
                      {isDragActive ? 'Drop images here...' : 'Drag & drop drone images, or click to browse'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Supports: JPG, TIFF, PNG — up to 500MB per file
                    </Typography>
                  </Box>

                  {/* Upload Progress */}
                  {Object.entries(uploadProgress).map(([id, progress]) => (
                    <Box key={id} sx={{ mt: 2 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                        <Typography variant="caption">Uploading...</Typography>
                        <Typography variant="caption">{Math.round(progress)}%</Typography>
                      </Box>
                      <LinearProgress variant="determinate" value={progress} sx={{ height: 6, borderRadius: 3 }} />
                    </Box>
                  ))}

                  {/* Image List */}
                  {activeSurvey.images.length > 0 && (
                    <Box sx={{ mt: 3 }}>
                      <Typography variant="subtitle2" sx={{ mb: 1 }}>
                        <ImageIcon sx={{ fontSize: 16, mr: 0.5, verticalAlign: 'middle' }} />
                        Images ({activeSurvey.images.length})
                      </Typography>
                      <List dense sx={{ maxHeight: 300, overflow: 'auto' }}>
                        {activeSurvey.images.map((img, idx) => (
                          <ListItem key={idx} sx={{ borderRadius: 1 }}>
                            <ListItemIcon sx={{ minWidth: 32 }}>
                              <ImageIcon fontSize="small" sx={{ color: 'text.secondary' }} />
                            </ListItemIcon>
                            <ListItemText
                              primary={img.name}
                              secondary={formatBytes(img.size)}
                              primaryTypographyProps={{ fontSize: '0.85rem' }}
                              secondaryTypographyProps={{ fontSize: '0.7rem' }}
                            />
                            <Chip
                              label={img.status}
                              size="small"
                              color={img.status === 'uploaded' ? 'success' : 'default'}
                              sx={{ fontSize: '0.65rem', height: 20 }}
                            />
                          </ListItem>
                        ))}
                      </List>
                    </Box>
                  )}

                  {/* Processing Status */}
                  {activeSurvey.status === 'processing' && (
                    <Alert severity="info" sx={{ mt: 3 }}>
                      Processing survey with OpenDroneMap... This may take several minutes depending on image count.
                    </Alert>
                  )}
                  {activeSurvey.status === 'completed' && (
                    <Alert severity="success" sx={{ mt: 3 }}>
                      Survey processed successfully. COG and tiles are ready for viewing.
                      <Button size="small" startIcon={<ViewIcon />} sx={{ ml: 2 }}>
                        View Results
                      </Button>
                      <Button size="small" startIcon={<DownloadIcon />} sx={{ ml: 1 }}>
                        Download
                      </Button>
                    </Alert>
                  )}
                </CardContent>
              </Card>
            ) : (
              <Card className="glass-card">
                <CardContent>
                  <Box sx={{ textAlign: 'center', py: 12, color: 'text.secondary' }}>
                    <DroneIcon sx={{ fontSize: 72, opacity: 0.2, mb: 2 }} />
                    <Typography variant="h5" sx={{ fontWeight: 600, mb: 1 }}>No Survey Selected</Typography>
                    <Typography variant="body1" sx={{ mb: 3 }}>
                      Create a new survey or select one from the list
                    </Typography>
                    <Button variant="contained" startIcon={<AddIcon />} onClick={() => setCreateDialogOpen(true)}>
                      Create Survey
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            )}
          </Grid>
        </Grid>
      </Container>

      {/* Create Survey Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Drone Survey</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            label="Survey Name"
            value={newSurveyName}
            onChange={(e) => setNewSurveyName(e.target.value)}
            placeholder="e.g., Nairobi Subdivision - Block A"
            sx={{ mt: 1, mb: 2 }}
          />
          <TextField
            fullWidth
            label="Description (optional)"
            value={newSurveyDesc}
            onChange={(e) => setNewSurveyDesc(e.target.value)}
            multiline
            rows={3}
            placeholder="Describe the survey area, purpose, etc."
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreateSurvey} disabled={!newSurveyName.trim()}>
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DroneProcessingPage;
