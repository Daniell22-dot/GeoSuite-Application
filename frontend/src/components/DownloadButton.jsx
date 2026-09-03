// Add to your GPS page component
import DownloadButton from '../components/DownloadButton';
import ExportDialog from '../components/ExportDialog';

// In your component render:
{processedData && (
  <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
    <DownloadButton 
      data={processedData}
      dataType="gps"
      buttonVariant="outlined"
      availableFormats={['gpx', 'kml', 'geojson', 'csv', 'shp']}
      onExportComplete={(format) => {
        console.log(`Exported as ${format}`);
      }}
    />
    
    <Button
      variant="contained"
      startIcon={<ArchiveIcon />}
      onClick={() => {
        // Export elevation profile data
        exportElevationProfile();
      }}
    >
      Export Elevation Profile
    </Button>
  </Box>
)}