"""Top-level package for qgis-map.

A high-level Python API for working with QGIS, inspired by leafmap.
"""

__author__ = """Qiusheng Wu"""
__email__ = "giswqs@gmail.com"
__version__ = "0.1.0"

from .qgis_map import Map
from .basemaps import BASEMAPS, get_basemap_names, get_basemap_url, get_xyz_uri
from .common import *

__all__ = [
    "Map",
    "BASEMAPS",
    "get_basemap_names",
    "get_basemap_url",
    "get_xyz_uri",
]
