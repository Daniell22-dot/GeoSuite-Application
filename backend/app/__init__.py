"""
GeoSuite backend application package.
"""
from app.config import settings

__version__ = settings.APP_VERSION
__author__ = "GeoSuite Team"
__description__ = "Complete Geospatial Processing Platform"

# Initialize logging
import logging
import sys

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('geosuite.log')
    ]
)

logger = logging.getLogger(__name__)
logger.info(f"Initializing {settings.APP_NAME} v{settings.APP_VERSION}")

# Export commonly used items
__all__ = [
    'settings',
    'logger',
]