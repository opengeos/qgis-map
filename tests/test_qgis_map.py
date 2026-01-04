#!/usr/bin/env python

"""Tests for `qgis_map` package."""

import unittest

from qgis_map import basemaps
from qgis_map import common


class TestBasemaps(unittest.TestCase):
    """Tests for basemaps module."""

    def test_basemaps_dict_exists(self):
        """Test that BASEMAPS dictionary exists and has entries."""
        self.assertIsInstance(basemaps.BASEMAPS, dict)
        self.assertGreater(len(basemaps.BASEMAPS), 0)

    def test_get_basemap_names(self):
        """Test get_basemap_names returns a list."""
        names = basemaps.get_basemap_names()
        self.assertIsInstance(names, list)
        self.assertIn("OpenStreetMap", names)
        self.assertIn("Esri.WorldImagery", names)

    def test_get_basemap_url(self):
        """Test get_basemap_url returns correct URLs."""
        url = basemaps.get_basemap_url("OpenStreetMap")
        self.assertIn("openstreetmap", url.lower())

        url = basemaps.get_basemap_url("Esri.WorldImagery")
        self.assertIn("arcgisonline", url.lower())

    def test_get_basemap_url_case_insensitive(self):
        """Test that basemap lookup is case-insensitive."""
        url1 = basemaps.get_basemap_url("OpenStreetMap")
        url2 = basemaps.get_basemap_url("OPENSTREETMAP")
        self.assertEqual(url1, url2)

    def test_get_basemap_url_invalid(self):
        """Test that invalid basemap name raises ValueError."""
        with self.assertRaises(ValueError):
            basemaps.get_basemap_url("InvalidBasemap123")

    def test_get_xyz_uri(self):
        """Test XYZ URI generation."""
        url = "https://example.com/{z}/{x}/{y}.png"
        uri = basemaps.get_xyz_uri(url)
        self.assertIn("type=xyz", uri)
        self.assertIn(url, uri)
        self.assertIn("zmin=0", uri)
        self.assertIn("zmax=22", uri)

    def test_get_xyz_uri_custom_zoom(self):
        """Test XYZ URI with custom zoom levels."""
        url = "https://example.com/{z}/{x}/{y}.png"
        uri = basemaps.get_xyz_uri(url, zmin=5, zmax=18)
        self.assertIn("zmin=5", uri)
        self.assertIn("zmax=18", uri)


class TestCommon(unittest.TestCase):
    """Tests for common module."""

    def test_hex_to_rgb(self):
        """Test hex to RGB conversion."""
        self.assertEqual(common.hex_to_rgb("#ff0000"), (255, 0, 0))
        self.assertEqual(common.hex_to_rgb("00ff00"), (0, 255, 0))
        self.assertEqual(common.hex_to_rgb("#0000ff"), (0, 0, 255))

    def test_rgb_to_hex(self):
        """Test RGB to hex conversion."""
        self.assertEqual(common.rgb_to_hex(255, 0, 0), "#ff0000")
        self.assertEqual(common.rgb_to_hex(0, 255, 0), "#00ff00")
        self.assertEqual(common.rgb_to_hex(0, 0, 255), "#0000ff")

    def test_get_file_extension(self):
        """Test file extension extraction."""
        self.assertEqual(common.get_file_extension("file.shp"), "shp")
        self.assertEqual(common.get_file_extension("path/to/file.TIF"), "tif")
        self.assertEqual(common.get_file_extension("file.geojson"), "geojson")

    def test_is_vector_file(self):
        """Test vector file detection."""
        self.assertTrue(common.is_vector_file("data.shp"))
        self.assertTrue(common.is_vector_file("data.geojson"))
        self.assertTrue(common.is_vector_file("data.gpkg"))
        self.assertFalse(common.is_vector_file("data.tif"))
        self.assertFalse(common.is_vector_file("data.png"))

    def test_is_raster_file(self):
        """Test raster file detection."""
        self.assertTrue(common.is_raster_file("data.tif"))
        self.assertTrue(common.is_raster_file("data.tiff"))
        self.assertTrue(common.is_raster_file("data.png"))
        self.assertFalse(common.is_raster_file("data.shp"))
        self.assertFalse(common.is_raster_file("data.geojson"))

    def test_random_string(self):
        """Test random string generation."""
        s1 = common.random_string()
        s2 = common.random_string()
        self.assertEqual(len(s1), 8)
        self.assertNotEqual(s1, s2)

        s3 = common.random_string(16)
        self.assertEqual(len(s3), 16)

    def test_is_qgis_available(self):
        """Test QGIS availability check."""
        # This will likely return False outside QGIS
        result = common.is_qgis_available()
        self.assertIsInstance(result, bool)


class TestMapClass(unittest.TestCase):
    """Tests for Map class (without QGIS)."""

    def test_import_map(self):
        """Test that Map class can be imported."""
        # Import should work even without QGIS
        try:
            from qgis_map import Map

            # Map class exists
            self.assertTrue(hasattr(Map, "add_basemap"))
            self.assertTrue(hasattr(Map, "add_vector"))
            self.assertTrue(hasattr(Map, "add_raster"))
            self.assertTrue(hasattr(Map, "add_time_slider"))
        except ImportError:
            # Import error is expected if running outside QGIS
            pass


if __name__ == "__main__":
    unittest.main()
