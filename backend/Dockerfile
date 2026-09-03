# GeoSuite Backend Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    cmake \
    build-essential \
    curl \
    software-properties-common \
    gcc \
    g++ \
    libgdal-dev \
    gdal-bin \
    libspatialindex-dev \
    libgeos-dev \
    libproj-dev \
    libsqlite3-mod-spatialite \
    spatialite-bin \
    libspatialite-dev \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL environment variables
ENV GDAL_DATA=/usr/share/gdal
ENV PROJ_LIB=/usr/share/proj

# Create and set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Build C++ Extensions
RUN mkdir -p /opt/geosuite/lib && \
    cd cpp_extensions && \
    mkdir build && \
    cd build && \
    cmake .. && \
    make && \
    cp geospatial_cpp*.so /opt/geosuite/lib/

# Set environment variables for the app
ENV PYTHONPATH="${PYTHONPATH}:/opt/geosuite/lib:/app"

# Create necessary directories
RUN mkdir -p /app/data/uploads \
    /app/data/dem \
    /app/data/temp \
    /app/data/output \
    /app/data/drone_surveys

# Set permissions
RUN chmod -R 755 /app/data && \
    chown -R 1000:1000 /opt/geosuite/lib

# Create non-root user
RUN useradd -m -u 1000 geosuite && \
    chown -R geosuite:geosuite /app

USER geosuite

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]