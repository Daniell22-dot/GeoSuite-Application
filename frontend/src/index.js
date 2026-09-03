/**
 * Main entry point for GeoSuite frontend.
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';

// Initialize monitoring
if (process.env.NODE_ENV === 'production') {
  // Initialize Sentry or other monitoring tools
  console.log('Initializing production monitoring...');
}

// Create root and render app
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// Performance monitoring
reportWebVitals(console.log); // Can send to analytics service