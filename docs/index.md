# Welcome to qgis-map

[![image](https://img.shields.io/pypi/v/qgis-map.svg)](https://pypi.python.org/pypi/qgis-map)

**A Python library that provides a high-level, leafmap-like API for working with PyQGIS**

## Overview

`qgis-map` is designed to make working with QGIS in Python easier and more intuitive. Inspired by the popular [leafmap](https://leafmap.org) library, it provides a simple, high-level API for common GIS operations within QGIS.

## Key Features

- **High-level API**: Simple, intuitive methods for common operations
- **Basemap support**: Easy access to OpenStreetMap, Esri, Google, CartoDB, and more
- **Vector layers**: Add shapefiles, GeoJSON, GeoPackage, and other formats
- **Raster layers**: Add GeoTIFFs, COGs, and apply color ramps
- **Time slider**: Create interactive time-based visualizations
- **Dockable panels**: Create custom interactive panels in QGIS
- **Map export**: Export maps to images

## Quick Example

```python
from qgis_map import Map

# Create a map with OpenStreetMap basemap
m = Map(basemap="OpenStreetMap")

# Add vector data
m.add_vector("cities.geojson", layer_name="Cities", zoom_to_layer=True)

# Add raster with color ramp
m.add_raster("elevation.tif", colormap="terrain", layer_name="DEM")

# Create a time slider for temporal data
m.add_time_slider(layers={
    "2020": "data_2020.tif",
    "2021": "data_2021.tif",
    "2022": "data_2022.tif"
})
```

## Contents

```{toctree}
:maxdepth: 2
:caption: Getting Started

installation
usage
```

```{toctree}
:maxdepth: 2
:caption: Examples

examples/intro
```

```{toctree}
:maxdepth: 2
:caption: API Reference

qgis_map
common
```

```{toctree}
:maxdepth: 2
:caption: Development

contributing
changelog
faq
```

## Credits

This package was inspired by [leafmap](https://leafmap.org) and is built on [PyQGIS](https://docs.qgis.org/latest/en/docs/pyqgis_developer_cookbook/).
