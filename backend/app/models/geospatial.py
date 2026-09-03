"""
SQLAlchemy models for geospatial data.
Dialect-agnostic: works with PostgreSQL (PostGIS) and SQLite.
"""
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean,
    JSON, Text, ForeignKey, LargeBinary, TypeDecorator
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid


class GUID(TypeDecorator):
    """Platform-independent UUID type. Uses CHAR(36) for SQLite, native UUID for Postgres."""
    impl = String(36)

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value) if not isinstance(value, str) else value
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return uuid.UUID(value) if not isinstance(value, uuid.UUID) else value
        return value


Base = declarative_base()


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tracks = relationship("GPSTrack", back_populates="user")
    analyses = relationship("WatershedAnalysis", back_populates="user")


class GPSTrack(Base):
    """GPS track model."""
    __tablename__ = "gps_tracks"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), index=True)
    name = Column(String(255))
    description = Column(Text)
    file_name = Column(String(255))
    file_size = Column(Integer)
    file_type = Column(String(50))
    points_count = Column(Integer)
    distance_2d = Column(Float)
    distance_3d = Column(Float)
    elevation_gain = Column(Float)
    elevation_loss = Column(Float)
    duration_seconds = Column(Float)
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    bounds = Column(JSON)
    extra_data = Column("metadata", JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="tracks")
    points = relationship("GPSPoint", back_populates="track", cascade="all, delete-orphan")


class GPSPoint(Base):
    """GPS point model."""
    __tablename__ = "gps_points"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    track_id = Column(GUID(), ForeignKey("gps_tracks.id"), index=True)
    point_number = Column(Integer)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    elevation_raw = Column(Float)
    elevation_corrected = Column(Float)
    time = Column(DateTime(timezone=True))
    speed = Column(Float)
    accuracy = Column(Float)
    heart_rate = Column(Float)
    cadence = Column(Float)
    temperature = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    track = relationship("GPSTrack", back_populates="points")


class MarineChart(Base):
    """Marine chart model."""
    __tablename__ = "marine_charts"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), index=True)
    name = Column(String(255))
    chart_number = Column(String(50))
    scale = Column(Float)
    projection = Column(String(50))
    bounds = Column(JSON)
    file_path = Column(String(500))
    file_type = Column(String(10))
    extra_data = Column("metadata", JSON)
    thumbnail = Column(LargeBinary)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    soundings = relationship("ChartSounding", back_populates="chart", cascade="all, delete-orphan")
    contours = relationship("DepthContour", back_populates="chart", cascade="all, delete-orphan")


class ChartSounding(Base):
    """Chart sounding model."""
    __tablename__ = "chart_soundings"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    chart_id = Column(GUID(), ForeignKey("marine_charts.id"), index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    depth = Column(Float, nullable=False)
    unit = Column(String(20), default="meters")
    quality = Column(String(20))
    feature_type = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chart = relationship("MarineChart", back_populates="soundings")


class DepthContour(Base):
    """Depth contour model."""
    __tablename__ = "depth_contours"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    chart_id = Column(GUID(), ForeignKey("marine_charts.id"), index=True)
    depth = Column(Float, nullable=False)
    unit = Column(String(20), default="meters")
    contour_type = Column(String(20))
    points = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chart = relationship("MarineChart", back_populates="contours")


class DEMFile(Base):
    """Digital Elevation Model file."""
    __tablename__ = "dem_files"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), index=True)
    name = Column(String(255))
    file_path = Column(String(500))
    resolution = Column(Float)
    bounds = Column(JSON)
    source = Column(String(50))
    extra_data = Column("metadata", JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class WatershedAnalysis(Base):
    """Watershed analysis model."""
    __tablename__ = "watershed_analyses"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), index=True)
    dem_id = Column(GUID(), ForeignKey("dem_files.id"), index=True)
    name = Column(String(255))
    pour_point = Column(JSON)
    area_km2 = Column(Float)
    perimeter_km = Column(Float)
    stream_length_km = Column(Float)
    elevation_stats = Column(JSON)
    results = Column(JSON)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="analyses")
    dem = relationship("DEMFile")


class HECRASAnalysis(Base):
    """HEC-RAS hydraulic analysis model."""
    __tablename__ = "hecras_analyses"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), index=True)
    watershed_id = Column(GUID(), ForeignKey("watershed_analyses.id"), index=True)
    name = Column(String(255))
    analysis_type = Column(String(50))
    geometry_file = Column(String(500))
    plan_file = Column(String(500))
    results_file = Column(String(500))
    parameters = Column(JSON)
    results = Column(JSON)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    user = relationship("User")
    watershed = relationship("WatershedAnalysis")


class Task(Base):
    """Celery task tracking."""
    __tablename__ = "tasks"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), index=True)
    task_id = Column(String(255), unique=True, index=True)
    task_type = Column(String(50))
    status = Column(String(20), default="pending")
    progress = Column(Float, default=0.0)
    result = Column(JSON)
    error = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")


# ── Drone survey models ──────────────────────────────────────────────

class DroneSurvey(Base):
    """A drone survey session — contains many images and produces an orthomosaic."""
    __tablename__ = "drone_surveys"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(30), default="uploaded")  # uploaded, processing, completed, failed
    image_count = Column(Integer, default=0)
    # Bounding box of the survey area
    bounds = Column(JSON)  # {north, south, east, west}
    # Camera / sensor metadata
    camera_model = Column(String(255))
    ground_sample_distance = Column(Float)  # GSD in cm/pixel
    area_hectares = Column(Float)
    # Processing outputs
    orthomosaic_path = Column(String(500))
    dsm_path = Column(String(500))
    dtm_path = Column(String(500))
    point_cloud_path = Column(String(500))
    tile_path = Column(String(500))  # PMTiles / MBTiles for web viewing
    # Progress tracking
    progress = Column(Float, default=0.0)
    progress_message = Column(String(500))
    error_message = Column(Text)
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processing_started_at = Column(DateTime(timezone=True))
    processing_completed_at = Column(DateTime(timezone=True))

    user = relationship("User")
    images = relationship("DroneImage", back_populates="survey", cascade="all, delete-orphan")


class DroneImage(Base):
    """Individual drone image with EXIF metadata."""
    __tablename__ = "drone_images"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    survey_id = Column(GUID(), ForeignKey("drone_surveys.id"), index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    # GPS position from EXIF
    latitude = Column(Float)
    longitude = Column(Float)
    altitude = Column(Float)  # meters above sea level
    # Camera metadata
    focal_length = Column(Float)
    sensor_width = Column(Float)
    sensor_height = Column(Float)
    image_width = Column(Integer)
    image_height = Column(Integer)
    gimbal_pitch = Column(Float)
    gimbal_yaw = Column(Float)
    gimbal_roll = Column(Float)
    # Computed position
    center_lat = Column(Float)
    center_lon = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    survey = relationship("DroneSurvey", back_populates="images")


class SurveyPlan(Base):
    """Survey plan image linked to digitization/CV results."""
    __tablename__ = "survey_plans"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), index=True)
    file_name = Column(String(255))
    file_path = Column(String(500))
    coordinate_system = Column(String(50), default="cassini")
    zone = Column(String(50))
    status = Column(String(20), default="pending")
    result = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")


class Annotation(Base):
    """Generic annotation record for CV training data."""
    __tablename__ = "annotations"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), index=True)
    image_id = Column(String(50), index=True)
    image_path = Column(String(500))
    annotations = Column(JSON)
    annotated = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")


def init_db():
    """Initialize database tables."""
    from sqlalchemy import create_engine
    from app.config import settings
    from app.models import geospatial

    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    return engine
