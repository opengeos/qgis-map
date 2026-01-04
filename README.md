# qgis-map

[![image](https://img.shields.io/pypi/v/qgis-map.svg)](https://pypi.python.org/pypi/qgis-map)
<!-- [![image](https://img.shields.io/conda/vn/conda-forge/qgis-map.svg)](https://anaconda.org/conda-forge/qgis-map) -->

**A Python library that provides a high-level, leafmap-like API for working with PyQGIS**

- Free software: MIT License
- Documentation: https://qgis-map.gishub.org

## Features

- **High-level API**: Simple, intuitive methods inspired by [leafmap](https://leafmap.org)
- **Basemap support**: Easy access to OpenStreetMap, Esri, Google, CartoDB, and more
- **Vector layers**: Add shapefiles, GeoJSON, GeoPackage, and other vector formats
- **Raster layers**: Add GeoTIFFs, COGs, and apply color ramps
- **Time slider**: Create interactive time-based visualizations with dockable panels
- **Dockable panels**: Create custom interactive panels in QGIS

## Installation

```bash
pip install qgis-map
```

## Quick Start

Use `qgis-map` within the QGIS Python console or in a PyQGIS script:

```python
from qgis_map import Map

# Create a map with a basemap
m = Map(basemap="OpenStreetMap")

# Add vector data
m.add_vector("path/to/data.geojson", layer_name="My Data", zoom_to_layer=True)

# Add raster data with a color ramp
m.add_raster("path/to/dem.tif", colormap="terrain", layer_name="Elevation")
```

## Usage Examples

### Adding Basemaps

```python
from qgis_map import Map, get_basemap_names

# See all available basemaps
print(get_basemap_names())

# Create map with a basemap
m = Map(basemap="CartoDB.DarkMatter")

# Add additional basemaps
m.add_basemap("Esri.WorldImagery", layer_name="Satellite")
m.add_basemap("HYBRID")  # Google Hybrid

# Add custom XYZ tiles
m.add_basemap(
    "https://custom.tiles.server/{z}/{x}/{y}.png",
    layer_name="Custom Tiles"
)
```

### Adding Vector Layers

```python
from qgis_map import Map

m = Map()

# Add a shapefile
m.add_vector("countries.shp", layer_name="Countries")

# Add GeoJSON with styling
m.add_vector(
    "cities.geojson",
    layer_name="Cities",
    style={
        "color": "#3388ff",
        "stroke_color": "#000000",
        "stroke_width": 1
    },
    zoom_to_layer=True
)

# Add a GeoDataFrame
import geopandas as gpd
gdf = gpd.read_file("data.gpkg")
m.add_gdf(gdf, layer_name="My GeoDataFrame")
```

### Adding Raster Layers

```python
from qgis_map import Map

m = Map()

# Add a GeoTIFF
m.add_raster("elevation.tif", layer_name="DEM")

# Add with color ramp
m.add_raster(
    "temperature.tif",
    colormap="RdYlBu",
    vmin=-10,
    vmax=40,
    layer_name="Temperature"
)

# Add a Cloud Optimized GeoTIFF (COG)
m.add_cog(
    "https://example.com/data.tif",
    layer_name="Remote COG",
    zoom_to_layer=True
)

# Add a WMS layer
m.add_wms(
    url="https://ows.mundialis.de/services/service",
    layers="TOPO-OSM-WMS",
    layer_name="Topo WMS"
)
```

### Time Slider

```python
from qgis_map import Map

m = Map()

# Create a time slider to switch between layers
layers = {
    "2020": "data/ndvi_2020.tif",
    "2021": "data/ndvi_2021.tif",
    "2022": "data/ndvi_2022.tif",
    "2023": "data/ndvi_2023.tif",
}
m.add_time_slider(layers=layers, time_interval=2)
```

### Utility Methods

```python
from qgis_map import Map

m = Map()
m.add_basemap("OpenStreetMap")
m.add_vector("data.geojson", layer_name="My Layer")

# Get layer names
print(m.get_layer_names())

# Zoom to a layer
m.zoom_to_layer("My Layer")

# Zoom to bounds
m.zoom_to_bounds((-122.5, 37.5, -121.5, 38.5))

# Set center and zoom
m.set_center(lat=37.7749, lon=-122.4194, zoom=12)

# Remove a layer
m.remove_layer("My Layer")

# Clear all layers (keep basemap)
m.clear_layers(keep_basemap=True)

# Export to image
m.to_image("output.png", width=1920, height=1080)
```

### Creating Custom Dock Widgets

```python
from qgis_map import Map
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

m = Map()

# Create a custom widget
widget = QWidget()
layout = QVBoxLayout()
layout.addWidget(QLabel("Custom Panel Content"))
widget.setLayout(layout)

# Add as dockable panel
dock = m.create_dock_widget("My Panel", widget, position="right")
```

## Available Basemaps

- **OpenStreetMap**: `OpenStreetMap`, `OSM`
- **CartoDB**: `CartoDB.Positron`, `CartoDB.DarkMatter`, `CartoDB.Voyager`
- **Stadia/Stamen**: `Stadia.StamenToner`, `Stadia.StamenTerrain`, `Stadia.StamenWatercolor`
- **Esri**: `Esri.WorldStreetMap`, `Esri.WorldImagery`, `Esri.WorldTopoMap`, `Esri.WorldTerrain`, `Esri.NatGeoWorldMap`, `Esri.OceanBasemap`
- **Google**: `ROADMAP`, `SATELLITE`, `TERRAIN`, `HYBRID`
- **Other**: `OpenTopoMap`

## API Reference

See the full [API documentation](https://qgis-map.gishub.org/qgis_map/) for detailed information about all available methods.

## Credits

This package was inspired by [leafmap](https://leafmap.org) and is built on [PyQGIS](https://docs.qgis.org/latest/en/docs/pyqgis_developer_cookbook/).
