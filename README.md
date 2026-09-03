# GeoSuite: Professional Geospatial Analytical Toolkit

GeoSuite is a state-of-the-art, high-performance geospatial suite designed for lead engineers and analytical researchers. It provides a comprehensive workbench for GPS track processing, marine chart analysis, watershed modeling, and interactive command-line operations.

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

*   **Integrated Geo-Terminal**: A low-latency, browser-based terminal powered by `ptyprocess` and `Xterm.js` for running GDAL/Whitebox CLI tools.
*   **GPS Analytics Workbench**: Advanced track visualization with elevation profiling and speed analysis.
*   **Marine & Watershed Engines**: Specialized modules for nautical charts and topographical water-flow modeling.
*   **Real-time Weather Intelligence**: A secure, proxied weather engine providing local forecasts via OpenWeather integration.
*   **Premium "Dark Tech" UI**: A cohesive design system utilizing glassmorphism and high-density layouts for maximum productivity.

---

## 🛠️ Architecture

### Frontend (React & Material UI)
- **Framework**: React 18+
- **Styling**: Vanilla CSS + Material UI (MUI)
- **Mapping**: Leaflet.js with custom "Dark Tech" basemap providers.

### Backend (FastAPI & C++)
- **Core API**: FastAPI (Python 3.11)
- **Persistence**: PostgreSQL with PostGIS extensions.
- **Compute Engine**: Custom C++ extensions located in `backend/cpp_extensions`, compiled via CMake.
- **WebSocket Bridge**: PTY-to-WebSocket bridge for interactive terminal sessions.

### Security & DevOps
- **Containerization**: Fully Dockerized environment (Postgres, Redis, FastAPI, React).
- **Hardened Secrets**: Environment-controlled API keys and credential rotation.
- **Proxy Services**: Backend-side weather proxy to eliminate client-side key exposure.

---

## 🚦 Getting Started

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for local frontend development)
- Python 3.11 (for local backend development)

### Deployment
1.  **Configure Environment**:
    Create a `backend/.env` file and add your `OPENWEATHER_API_KEY`.
2.  **Start Services**:
    ```bash
    docker-compose up --build
    ```
3.  **Access the Suite**:
    - **App**: `http://localhost:3000`
    - **API Docs**: `http://localhost:8000/docs`
    - **Preview Page**: `http://localhost:3000/GeoSuite.html`

---

## 🛡️ License
Proprietary Geospatial Suite - Confidential & Professional Use Only.
Developed by **Daniel Manyasa (Lead Geospatial Engineer)**.
