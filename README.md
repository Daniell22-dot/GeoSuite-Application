# GeoSuite: Professional Geospatial Analytical Toolkit

GeoSuite is a state-of-the-art, high-performance geospatial suite designed for lead engineers and analytical researchers. It provides a comprehensive workbench for GPS track processing, marine chart analysis, watershed modeling, computer vision-based survey plan digitization, IFC-to-PostGIS conversion, and interactive command-line operations.

---

## 🏛️ Evolution of GeoSuite

### The Initial Phase
GeoSuite began as a single-page, HTML-based monitoring tool. It focused on providing a unified dashboard for Kenya-specific geospatial data. While functional, it relied on hardcoded API keys and client-side processing, which limited its scalability and security in enterprise environments.

### The Decisive Shift: Why C++?
As the complexity of our geospatial models grew—especially in marine sounding extraction and high-resolution watershed delineation—Python's interpreted nature became a bottleneck. We decided to bridge **C++ with GDAL (Geospatial Data Abstraction Library)** for several critical reasons:

1.  **Computational Efficiency**: C++ allows us to manipulate massive raster datasets and point clouds with near-zero overhead.
2.  **Low-Level Memory Control**: Vital for processing large GeoTIFFs and bathymetric grids without memory leaks.
3.  **True Parallelism**: C++ enables multithreaded processing for heavy simulations that were previously blocked by Python's Global Interpreter Lock (GIL).
4.  **GDAL Native Bindings**: Direct access to GDAL's C/C++ API provides more granular control over coordinate transformations and data translation than higher-level wrappers.

---

## 🚀 Key Features

### Core GeoSuite Platform
*   **Integrated Geo-Terminal**: A low-latency, browser-based terminal powered by `ptyprocess` and `Xterm.js` for running GDAL/Whitebox CLI tools.
*   **GPS Analytics Workbench**: Advanced track visualization with elevation profiling and speed analysis.
*   **Marine & Watershed Engines**: Specialized modules for nautical charts and topographical water-flow modeling.
*   **Real-time Weather Intelligence**: A secure, proxied weather engine providing local forecasts via OpenWeather integration.
*   **Premium "Dark Tech" UI**: A cohesive design system utilizing glassmorphism and high-density layouts for maximum productivity.

### 🔬 Computer Vision Engine (CV Engine)
*   **Survey Plan Digitization**: Automated digitization of scanned survey plans using deep learning models (beacon detection, boundary segmentation, feature extraction, text reading, sounding extraction, land-use classification).
*   **Multi-Head Architecture**: Modular CNN heads for beacon detection, boundary segmentation, feature extraction, text recognition, symbol classification, and land-use classification.
*   **Real & Synthetic Training**: Training pipelines supporting both synthetic data generation and real Kenya survey plan datasets.
*   **Fast & Accurate Modes**: Optimized inference paths for rapid processing or high-precision digitization.

### 📐 Print Layout & Export
*   **Layout Presets**: A4/A3 Portrait/Landscape with configurable margins.
*   **Map Elements**: Scale bar, north arrow, legend, scale line, coordinate display.
*   **Metadata Support**: Title, author, keywords, comments.
*   **Export Formats**: PDF, PNG, SVG, high-resolution raster.
*   **Live Preview**: Real-time layout preview with element positioning.

### 🔌 Plugin System
*   **Extensible Architecture**: Dynamic plugin loading from `extensions/` directory.
*   **Plugin Metadata**: Name, description, version, author, CRS compatibility.
*   **Built-in Extensions**: IFC2PostGIS, sample raster/vector loaders, attribute exporters.
*   **Plugin API**: Python scripts with `@pyqtSlot` decorated functions for UI integration.
*   **CRS Compatibility Checking**: Automatic CRS mismatch detection between plugins and layers.

### 🏗️ IFC2PostGIS Plugin
*   **IFC Import**: Supports `.ifc`, `.ifcxml`, `.ifczip` formats via `ifcopenshell`.
*   **Element Extraction**: Walls, slabs, doors, windows, beams, columns, stairs, ramps, footings.
*   **Attribute Extraction**: Name, description, dimensions, materials, global IDs.
*   **Geometry Processing**: Bounding boxes, centroids, geometry conversion to WKT/WKB.
*   **PostGIS Export**: Direct export to PostGIS/GeoPackage with CRS transformation.
*   **CRS Handling**: Automatic CRS detection and transformation (EPSG:4326, 3857, UTM zones).
*   **deKUT-3D-Campus-Digital-Twin Integration**: Native support for 6 IFC files (14MB-35MB) from the deKUT campus digital twin project (DANSI, DEDO, SOE, SOEdan, SOE_NEW, SOE models).

### 📊 Advanced GIS Capabilities
*   **Layer Management**: Add/remove raster (GeoTIFF, ASC, NetCDF), vector (Shapefile, GeoPackage, GPX, DXF), and tabular (CSV, XLSX) layers.
*   **Attribute Table**: View, filter, search, edit, copy, delete features; field type validation; add/delete features.
*   **Layer Catalogue**: Hierarchical tree view with base/overlay grouping, visibility toggles, lock buttons, drag-and-drop reordering, CRS compatibility warnings.
*   **Styling & Symbology**: Single symbol, categorized, graduated, rule-based, palette renderers; color ramps (Viridis, Plasma, Inferno, Magma, Turbo); opacity/transparency controls.
*   **Navigation**: Zoom in/out, pan, full extent, layer extent, scale selector (1:100 to 1:50000), coordinate display, overview map.
*   **Layer Import**: GeoTIFF, ASC, NetCDF, Shapefile, GeoPackage, GPX, DXF, CSV, XLSX with auto CRS detection.
*   **Spatial Analysis**: Buffer, intersect, union, difference, centroids; save results to GeoPackage/GeoJSON/CSV.

### 🖥️ Desktop Application (PyQt6 + QGIS)
*   **Native Desktop**: PyQt6 with QGIS integration for professional GIS workflows.
*   **CRS Picker**: EPSG code selector (4326, 3857, 27700, UTM zones) with live canvas reprojection.
*   **Attribute Table**: Sortable, filterable, editable table with copy/select/delete actions.
*   **Map Canvas**: QgsMapCanvas with zoom/pan/extent controls, coordinate display, scale display.
*   **Splash Screen**: Branded startup screen with initialization progress.
*   **Settings Dialog**: CRS, output format, auto-save interval, decimal places, dark/light theme.
*   **About Dialog**: Version info, QGIS/Python versions, committed model files, license.
- **Splash Screen**: Branded startup screen with initialization progress.

### 🐍 Backend (FastAPI + C++)
*   **Core API**: FastAPI (Python 3.11) with SQLAlchemy ORM.
*   **Persistence**: PostgreSQL with PostGIS extensions.
- **Compute Engine**: Custom C++ extensions in `backend/cpp_extensions`, compiled via CMake.
*   **WebSocket Bridge**: PTY-to-WebSocket bridge for interactive terminal sessions.
*   **CV Engine API**: REST endpoints for survey plan digitization.
- **Marine Chart API**: KAP/BSB, CAD, GeoTIFF processing with soundings/contours extraction.

### 🐳 Security & DevOps
*   **Containerization**: Fully Dockerized (Postgres, Redis, FastAPI, React).
*   **Hardened Secrets**: Environment-controlled API keys and credential rotation.
- **Proxy Services**: Backend-side weather proxy to eliminate client-side key exposure.
*   **Git Hygiene**: Comprehensive `.gitignore` for Python cache, virtual envs, C extensions, build artifacts, RAW DATA, DATASETS, Parcels, developer utilities.

---

## 🛠️ Architecture

### Frontend (React & Material UI)
- **Framework**: React 18+
- **Styling**: Vanilla CSS + Material UI (MUI)
- **Mapping**: Leaflet.js with custom "Dark Tech" basemap providers.

### Backend (FastAPI & C++)
- **Core API**: FastAPI (Python 3.11)
- **Persistence**: PostgreSQL with PostGIS extensions.
- **Compute Engine**: Custom C++ extensions in `backend/cpp_extensions`, compiled via CMake.
- **WebSocket Bridge**: PTY-to-WebSocket bridge for interactive terminal sessions.

### Desktop (PyQt6 + QGIS)
- **Framework**: PyQt6 with QGIS Python bindings (pyqgis).
- **Map Canvas**: QgsMapCanvas with zoom/pan/extent/CRS controls.
- **Layer Registry**: QgsLayerTreeRegistry with drag-drop reordering.
- **Print Layout**: QgsLayout-based composition with PDF/PNG/SVG export.

### Security & DevOps
- **Containerization**: Fully Dockerized (Postgres, Redis, FastAPI, React).
- **Hardened Secrets**: Environment-controlled API keys and credential rotation.
- **Proxy Services**: Backend-side weather proxy to eliminate client-side key exposure.
- **Git Hygiene**: Comprehensive `.gitignore` for Python cache, virtual envs, C extensions, build artifacts, RAW DATA, DATASETS, Parcels, developer utilities.

---

## 🚀 Key Datasets

### Kenya Survey Plans (CV Training)
- **27 training patches** with boundary masks, feature masks, beacon targets.
- **Real-world survey plans** from Kenya with GPS coordinates.
- **Synthetic generator** for unlimited training data augmentation.

### deKUT-3D-Campus-Digital-Twin
- **6 IFC files** (14MB - 35MB): DANSI, DEDO, SOE, SOEdan, SOE_NEW, SOE models.
- **1,100+ building elements**: 267 walls, 21 slabs, 153 doors, 191 windows, 190 beams, 282 columns.
- **Full BIM data**: Global IDs, names, descriptions, dimensions, materials, spatial relationships.
- **Ready for IFC2PostGIS**: Direct import to PostGIS/GeoPackage for 3D campus visualization.

### GEBCO Bathymetric Data
- **Global bathymetry**: 1/12° resolution (4km), -5,424m to +2,326m depth range.
- **Formats**: NetCDF (.nc), ASCII Grid (.asc), GeoTIFF (.tif).
- **Coverage**: 4471x3122 grid (13.9M pixels) covering Indian Ocean region.

---

## 🚦 Getting Started

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for local frontend development)
- Python 3.11 (for local backend development)
- QGIS 3.34+ with Python bindings (for desktop app)

### Deployment
1.  **Configure Environment**:
    Create a `backend/.env` file and add your `OPENWEATHER_API_KEY`.
    Optionally set `QGIS_PREFIX_PATH` if QGIS is in non-standard location.
2.  **Start Services**:
    ```bash
    docker-compose up --build
    ```
3.  **Access the Suite**:
    - **Web App**: `http://localhost:3000`
    - **API Docs**: `http://localhost:8000/docs`
    - **Preview Page**: `http://localhost:3000/GeoSuite.html`
    - **Desktop App**: `python GeoSuiteDesktop.py` (requires PyQt6 + QGIS)

### Desktop App Development
```bash
cd D:\Geospatial_suite
pip install -r requirements_desktop.txt
python GeoSuiteDesktop.py
```

---

## 📁 Project Structure

```
GeoSuite/
├── GeoSuiteDesktop.py          # PyQt6 desktop application entry point
├── requirements_desktop.txt    # Python desktop dependencies
├── .gitignore                  # Comprehensive ignore rules
├── README.md                   # This file
├── backend/
│   ├── app/
│   │   ├── routes/             # API endpoints (CV, marine, GPS, watershed, etc.)
│   │   ├── services/           # Business logic (CV, marine, watershed, export)
│   │   ├── cv_engine/          # Computer Vision engine
│   │   │   ├── heads/          # CNN heads (beacon, boundary, feature, text, etc.)
│   │   │   ├── training/       # Training pipelines (real/synthetic)
│   │   │   └── pipeline.py     # CV pipeline orchestration
│   │   └── models/             # SQLAlchemy models
│   ├── cpp_extensions/         # C++ extensions (GDAL utils, Python bindings)
│   └── run_dev.py              # Development server launcher
├── frontend/
│   ├── src/
│   │   ├── components/         # React components (Dashboard, MapViewer, etc.)
│   │   ├── pages/              # Page components (Marine, GPS, Watershed, etc.)
│   │   ├── services/           # API clients, GIS utilities
│   │   └── App.jsx             # Main app with routing
│   └── package.json
├── extensions/
│   ├── __init__.py             # Plugin loader/registry
│   └── ifc2postgis.py          # IFC to PostGIS converter plugin
├── RAW DATA/                   # Raw geospatial data (ignored by git)
│   └── Bathymetric_Data/       # GEBCO bathymetric data
├── DATASETS/                   # Training datasets (ignored by git)
│   └── kenya_training/         # Kenya survey plan patches
├── Parcels/                    # Parcel data (ignored by git)
├── backend/app/cv_models/      # Trained CV models (6 .npz files)
├── GeoSuiteDesktop.py          # PyQt6 desktop app entry point
├── requirements_desktop.txt    # Desktop Python dependencies
├── GeoSuite.html               # Standalone HTML demo
└── docker-compose.yml
```

---

## 🛡️ License
Proprietary Geospatial Suite - Confidential & Professional Use Only.
Developed by **Daniel Manyasa (Lead Geospatial Engineer)**.

---

## 📚 Additional Resources

### API Documentation
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Model Files
Pre-trained CV models in `backend/app/cv_models/`:
- `beacon_detector_backbone.npz` / `head.npz`
- `boundary_segmenter_backbone.npz` / `decoder.npz`
- `feature_extractor_backbone.npz` / `decoder.npz`

### Docker Commands
```bash
# Build and start all services
docker-compose up --build

# Run backend only
docker-compose up backend

# View logs
docker-compose logs -f backend

# Run database migrations
docker-compose exec backend alembic upgrade head
```

---

## 🤝 Contributing
This is a proprietary geospatial suite. For collaboration inquiries, contact **Daniel Manyasa (Lead Geospatial Engineer)**.