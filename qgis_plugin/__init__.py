"""
KLISS CV Plugin initialization — registers the plugin with QGIS.
"""
from .kliss_cv_plugin import KLISSCVPlugin


def classFactory(iface):
    return KLISSCVPlugin(iface)
