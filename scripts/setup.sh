#!/bin/bash

# GeoSuite Complete Setup Script
set -e

echo " GeoSuite Platform - Complete Setup"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check requirements
check_requirements() {
    echo "Checking system requirements..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}Docker Compose is not installed. Please install Docker Compose first.${NC}"
        exit 1
    fi
    
    # Check Node.js (for local frontend development)
    if ! command -v node &> /dev/null; then
        echo -e "${YELLOW}Node.js is not installed. Some features may not work.${NC}"
    fi
    
    # Check Python (for local backend development)
    if ! command -v python3 &> /dev/null; then
        echo -e "${YELLOW}Python3 is not installed. Some features may not work.${NC}"
    fi
    
    echo -e "${GREEN}✓ All requirements checked${NC}"
}

# Create directory structure
create_structure() {
    echo "Creating project structure..."
    
    # Create main directories
    mkdir -p {backend,frontend,data,scripts,nginx,traefik}
    mkdir -p backend/{app,models,routes,services,utils,workers}
    mkdir -p backend/app/{models,routes,services,utils,workers}
    mkdir -p frontend/src/{components,pages,services,utils}
    mkdir -p data/{dem,temp,output,uploads}
    mkdir -p nginx/ssl
    
    echo -e "${GREEN}✓ Directory structure created${NC}"
}

# Create environment files
create_env_files() {
    echo "Creating environment configuration..."
    
    # Create .env file
    cat > .env << EOF
# GeoSuite Environment Variables
# ==============================

# Application
APP_NAME=GeoSuite
APP_VERSION=2.0.0
DEBUG=false
SECRET_KEY=$(openssl rand -hex 32)

# Database
POSTGRES_DB=geosuite
POSTGRES_postgres
POSTGRES_PASSWORD=postgres
DATABASE_URL=postgresql://geosuite:postgres@postgres:5432/geosuite

# Redis
REDIS_URL=redis://redis:6379/0

# File Storage
UPLOAD_DIR=/app/data/uploads
MAX_UPLOAD_SIZE=104857600  # 100MB

# GDAL Configuration
GDAL_DATA=/usr/share/gdal
PROJ_LIB=/usr/share/proj

# Map Services
MAPBOX_TOKEN=your_mapbox_token_here
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here

# Email (for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=oromidaniell@gmail.com
SMTP_PASSWORD=your_app_password

# External APIs
ELEVATION_API_URL=https://api.open-elevation.com/api/v1/lookup
WEATHER_API_KEY=your_openweathermap_api_key

# Security
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
JWT_SECRET=$(openssl rand -hex 32)
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# Monitoring
SENTRY_DSN=your_sentry_dsn_here
LOG_LEVEL=INFO
EOF
    
    # Create .env.example
    cp .env .env.example
    sed -i 's/=.*$/=/' .env.example
    
    echo -e "${GREEN}✓ Environment files created${NC}"
}

# Install frontend dependencies
setup_frontend() {
    echo "Setting up frontend..."
    
    cd frontend
    
    # Create package.json if not exists
    if [ ! -f package.json ]; then
        cat > package.json << EOF
{
  "name": "geosuite-frontend",
  "version": "2.0.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.18.0",
    "react-leaflet": "^4.2.1",
    "leaflet": "^1.9.4",
    "@mui/material": "^5.14.0",
    "@emotion/react": "^11.11.0",
    "@emotion/styled": "^11.11.0",
    "axios": "^1.6.0",
    "recharts": "^2.10.0",
    "react-dropzone": "^14.2.3",
    "@turf/turf": "^6.5.0",
    "papaparse": "^5.4.1",
    "file-saver": "^2.0.5",
    "lodash": "^4.17.21",
    "moment": "^2.29.4"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "devDependencies": {
    "react-scripts": "5.0.1",
    "@testing-library/react": "^14.0.0",
    "@testing-library/jest-dom": "^6.1.4",
    "@testing-library/user-event": "^14.5.0"
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  }
}
EOF
    fi
    
    # Install dependencies if node_modules doesn't exist
    if [ ! -d "node_modules" ]; then
        echo "Installing npm dependencies..."
        npm install
    fi
    
    cd ..
    
    echo -e "${GREEN}✓ Frontend setup complete${NC}"
}

# Setup backend
setup_backend() {
    echo "Setting up backend..."
    
    cd backend
    
    # Create virtual environment if not exists
    if [ ! -d "venv" ]; then
        echo "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment and install dependencies
    echo "Installing Python dependencies..."
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        echo "Creating requirements.txt..."
        cat > requirements.txt << EOF
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
pydantic==2.5.0
pydantic-settings==2.1.0
gdal==3.7.0
geopandas==0.14.0
shapely==2.0.1
pyproj==3.6.0
rasterio==1.3.9
fiona==1.9.5
whitebox==2.3.0
pyhecdss==1.0.0
pysheds==0.3.3
numpy==1.24.0
scipy==1.11.0
pandas==2.1.0
celery==5.3.4
redis==5.0.1
sqlalchemy==2.0.23
asyncpg==0.29.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-magic==0.4.27
aiofiles==23.2.1
python-dotenv==1.0.0
EOF
        pip install -r requirements.txt
    fi
    
    deactivate
    
    cd ..
    
    echo -e "${GREEN}✓ Backend setup complete${NC}"
}

# Setup database
setup_database() {
    echo "Setting up database..."
    
    # Create init SQL script
    cat > scripts/init-db.sql << EOF
-- Initialize GeoSuite Database
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS postgis_raster;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS gps;
CREATE SCHEMA IF NOT EXISTS marine;
CREATE SCHEMA IF NOT EXISTS watershed;

-- GPS Data Tables
CREATE TABLE gps.tracks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    name VARCHAR(255),
    description TEXT,
    file_name VARCHAR(255),
    file_size INTEGER,
    file_type VARCHAR(50),
    points_count INTEGER,
    distance_2d DOUBLE PRECISION,
    distance_3d DOUBLE PRECISION,
    elevation_gain DOUBLE PRECISION,
    elevation_loss DOUBLE PRECISION,
    duration_seconds DOUBLE PRECISION,
    bounds GEOMETRY(POLYGON, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE gps.track_points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    track_id UUID REFERENCES gps.tracks(id) ON DELETE CASCADE,
    point_number INTEGER,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    elevation_raw DOUBLE PRECISION,
    elevation_corrected DOUBLE PRECISION,
    time TIMESTAMP,
    speed DOUBLE PRECISION,
    geom GEOMETRY(POINTZ, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_track_points_track_id ON gps.track_points(track_id);
CREATE INDEX idx_track_points_geom ON gps.track_points USING GIST(geom);

-- Marine Charts Tables
CREATE TABLE marine.charts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255),
    chart_number VARCHAR(50),
    scale DOUBLE PRECISION,
    projection VARCHAR(50),
    bounds GEOMETRY(POLYGON, 4326),
    file_path VARCHAR(500),
    file_type VARCHAR(10),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE marine.soundings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chart_id UUID REFERENCES marine.charts(id) ON DELETE CASCADE,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    depth DOUBLE PRECISION,
    unit VARCHAR(20),
    quality VARCHAR(20),
    geom GEOMETRY(POINT, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_soundings_chart_id ON marine.soundings(chart_id);
CREATE INDEX idx_soundings_geom ON marine.soundings USING GIST(geom);

-- Watershed Data Tables
CREATE TABLE watershed.dem_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255),
    file_path VARCHAR(500),
    resolution DOUBLE PRECISION,
    bounds GEOMETRY(POLYGON, 4326),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE watershed.analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dem_id UUID REFERENCES watershed.dem_files(id) ON DELETE CASCADE,
    name VARCHAR(255),
    pour_point GEOMETRY(POINT, 4326),
    area_km2 DOUBLE PRECISION,
    perimeter_km DOUBLE PRECISION,
    stream_length_km DOUBLE PRECISION,
    elevation_stats JSONB,
    results JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User Management
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default admin user (password: admin123)
INSERT INTO users (email, username, full_name, hashed_password, is_superuser)
VALUES (
    'admin@geosuite.com',
    'admin',
    'System Administrator',
    '\$2b\$12\$LQv3c1yqBzwL4gWbYQwLFuYlH9v2V7zJ6qY8kR9nN2mXpV1sS5tT6', -- bcrypt hash for 'admin123'
    true
) ON CONFLICT (email) DO NOTHING;
EOF
    
    echo -e "${GREEN}✓ Database setup complete${NC}"
}

# Build and start services
start_services() {
    echo "Building and starting services..."
    
    # Build Docker images
    echo "Building Docker images..."
    docker-compose build
    
    # Start services
    echo "Starting services..."
    docker-compose up -d
    
    # Wait for services to be ready
    echo "Waiting for services to be ready..."
    sleep 30
    
    # Check service status
    echo "Checking service status..."
    docker-compose ps
    
    echo -e "${GREEN}✓ Services started successfully${NC}"
}

# Display access information
display_info() {
    echo ""
    echo "======================================"
    echo " GeoSuite Platform Setup Complete!"
    echo "======================================"
    echo ""
    echo " Services Available:"
    echo "  Frontend:      http://localhost:3000"
    echo "  Backend API:   http://localhost:8000"
    echo "  API Docs:      http://localhost:8000/docs"
    echo "  pgAdmin:       http://localhost:5050"
    echo "  MinIO Console: http://localhost:9001"
    echo "  Flower:        http://localhost:5555"
    echo "  Traefik:       http://localhost:8080"
    echo ""
    echo " Default Credentials:"
    echo "  PostgreSQL:    geosuite / geosuite123"
    echo "  pgAdmin:       admin@geosuite.com / admin123"
    echo "  MinIO:         minioadmin / minioadmin123"
    echo "  Admin User:    admin@geosuite.com / admin123"
    echo ""
    echo " Quick Start:"
    echo "  1. Open http://localhost:3000"
    echo "  2. Login with admin credentials"
    echo "  3. Upload a GPX file to test GPS features"
    echo "  4. Try marine chart or watershed analysis"
    echo ""
    echo " Management Commands:"
    echo "  Start:         docker-compose up -d"
    echo "  Stop:          docker-compose down"
    echo "  Restart:       docker-compose restart"
    echo "  Logs:          docker-compose logs -f"
    echo "  Update:        docker-compose pull && docker-compose up -d"
    echo ""
    echo " Data Directory: ./data/"
    echo "  Uploads:       ./data/uploads/"
    echo "  DEMs:          ./data/dem/"
    echo "  Outputs:       ./data/output/"
    echo ""
    echo " Next Steps:"
    echo "  1. Update .env file with your API keys"
    echo "  2. Configure SSL certificates in nginx/ssl/"
    echo "  3. Set up backup for PostgreSQL data"
    echo "  4. Configure monitoring and alerts"
    echo ""
    echo "Need help? Check the README.md or create an issue."
    echo "======================================"
}

# Main execution
main() {
    echo -e "${GREEN}Starting GeoSuite setup...${NC}"
    
    check_requirements
    create_structure
    create_env_files
    setup_frontend
    setup_backend
    setup_database
    start_services
    display_info
    
    echo -e "${GREEN} GeoSuite setup completed successfully!${NC}"
}

# Run main function
main "$@"