"""The common module contains common functions and classes used by the other modules."""

from typing import Any, Dict, List, Optional, Tuple, Union
import os


def hello_world():
    """Prints "Hello World!" to the console."""
    print("Hello World!")


def is_qgis_available() -> bool:
    """Check if QGIS libraries are available.

    Returns:
        True if QGIS is available, False otherwise.
    """
    try:
        from qgis.core import QgsApplication

        return True
    except ImportError:
        return False


def check_qgis() -> None:
    """Check if QGIS is available and raise an error if not.

    Raises:
        ImportError: If QGIS libraries are not available.
    """
    if not is_qgis_available():
        raise ImportError(
            "QGIS libraries are not available. "
            "Please run this code within QGIS or install PyQGIS."
        )


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert a hex color string to RGB tuple.

    Args:
        hex_color: A hex color string (e.g., "#ff0000" or "ff0000").

    Returns:
        A tuple of (R, G, B) values.
    """
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        raise ValueError(
            f"Invalid hex color '{hex_color}': expected 6 hexadecimal characters."
        )
    if not all(c in "0123456789abcdefABCDEF" for c in hex_color):
        raise ValueError(
            f"Invalid hex color '{hex_color}': contains non-hexadecimal characters."
        )
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB values to a hex color string.

    Args:
        r: Red component (0-255).
        g: Green component (0-255).
        b: Blue component (0-255).

    Returns:
        A hex color string (e.g., "#ff0000").
    """
    return "#{:02x}{:02x}{:02x}".format(r, g, b)


def get_file_extension(filepath: str) -> str:
    """Get the file extension from a filepath.

    Args:
        filepath: The file path.

    Returns:
        The file extension (lowercase, without the dot).
    """
    return os.path.splitext(filepath)[1].lower().lstrip(".")


def is_vector_file(filepath: str) -> bool:
    """Check if a file is a vector format.

    Args:
        filepath: The file path.

    Returns:
        True if the file is a vector format, False otherwise.
    """
    vector_extensions = {
        "shp",
        "geojson",
        "json",
        "gpkg",
        "kml",
        "kmz",
        "gml",
        "tab",
        "mif",
        "mid",
        "dgn",
        "dxf",
        "dwg",
        "gpx",
        "csv",
        "xlsx",
        "xls",
        "ods",
        "parquet",
        "feather",
        "gdb",
    }
    return get_file_extension(filepath) in vector_extensions


def is_raster_file(filepath: str) -> bool:
    """Check if a file is a raster format.

    Args:
        filepath: The file path.

    Returns:
        True if the file is a raster format, False otherwise.
    """
    raster_extensions = {
        "tif",
        "tiff",
        "geotiff",
        "img",
        "jp2",
        "png",
        "jpg",
        "jpeg",
        "gif",
        "bmp",
        "ecw",
        "sid",
        "nc",
        "hdf",
        "hdf4",
        "hdf5",
        "grd",
        "asc",
        "dem",
        "dt0",
        "dt1",
        "dt2",
        "vrt",
    }
    return get_file_extension(filepath) in raster_extensions


def random_string(length: int = 8) -> str:
    """Generate a random string of specified length.

    Args:
        length: The length of the random string. Defaults to 8.

    Returns:
        A random string.
    """
    import random
    import string

    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def download_file(
    url: str,
    output_path: Optional[str] = None,
    overwrite: bool = False,
    **kwargs,
) -> str:
    """Download a file from a URL.

    Args:
        url: The URL to download from.
        output_path: The output file path. If None, uses a temp file.
        overwrite: Whether to overwrite existing files. Defaults to False.
        **kwargs: Additional keyword arguments for urllib.request.urlretrieve.

    Returns:
        The path to the downloaded file.

    Raises:
        Exception: If the download fails.
    """
    import urllib.request
    import tempfile

    if output_path is None:
        suffix = os.path.splitext(url.split("?")[0])[1]
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            output_path = tmp.name

    if os.path.exists(output_path) and not overwrite:
        return output_path

    try:
        urllib.request.urlretrieve(url, output_path)
        return output_path
    except Exception as e:
        raise Exception(f"Failed to download {url}: {e}")


def get_sample_data(name: str = "countries") -> str:
    """Get a path to sample data.

    Args:
        name: The name of the sample dataset. Options:
            - "countries": Natural Earth countries
            - "cities": Natural Earth populated places
            - "rivers": Natural Earth rivers

    Returns:
        The path to the sample data file.
    """
    samples = {
        "countries": "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson",
        "cities": "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_populated_places.geojson",
        "rivers": "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_rivers_lake_centerlines.geojson",
    }

    if name not in samples:
        raise ValueError(
            f"Unknown sample data: {name}. Options: {list(samples.keys())}"
        )

    url = samples[name]
    return download_file(url)
