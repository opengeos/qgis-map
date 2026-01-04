# Usage

This guide covers the main features of `qgis-map` and how to use them effectively.

## Getting Started

Import the `Map` class and create a new map instance:

```python
from qgis_map import Map

# Create a map with default settings
m = Map()

# Create a map with specific basemap
m = Map(basemap="CartoDB.DarkMatter")

# Create a map with center and zoom
m = Map(center=(40.7128, -74.0060), zoom=10, basemap="OpenStreetMap")
```

## Working with Basemaps

### Available Basemaps

Use `get_basemap_names()` to see all available basemaps:

```python
from qgis_map import get_basemap_names

print(get_basemap_names())
```

Available basemap categories:

| Category | Basemaps |
|----------|----------|
| OpenStreetMap | `OpenStreetMap`, `OSM` |
| CartoDB | `CartoDB.Positron`, `CartoDB.DarkMatter`, `CartoDB.Voyager` |
| Stadia | `Stadia.StamenToner`, `Stadia.StamenTerrain`, `Stadia.StamenWatercolor` |
| Esri | `Esri.WorldStreetMap`, `Esri.WorldImagery`, `Esri.WorldTopoMap`, `Esri.WorldTerrain`, `Esri.NatGeoWorldMap`, `Esri.OceanBasemap` |
| Google | `ROADMAP`, `SATELLITE`, `TERRAIN`, `HYBRID` |
| Other | `OpenTopoMap` |

### Adding Basemaps

```python
m = Map()

# Add by name
m.add_basemap("Esri.WorldImagery")

# Add with custom layer name
m.add_basemap("SATELLITE", layer_name="Google Satellite")

# Add custom XYZ tiles
m.add_basemap(
    "https://tiles.example.com/{z}/{x}/{y}.png",
    layer_name="Custom Tiles"
)

# Control visibility and opacity
m.add_basemap("OpenStreetMap", visible=True, opacity=0.7)
```

## Working with Vector Data

### Adding Vector Layers

```python
# Add a shapefile
m.add_vector("path/to/data.shp", layer_name="My Shapefile")

# Add GeoJSON
m.add_vector("path/to/data.geojson", layer_name="GeoJSON Data")

# Add GeoPackage
m.add_vector("path/to/data.gpkg", layer_name="GeoPackage Layer")

# Zoom to layer after adding
m.add_vector("data.geojson", zoom_to_layer=True)
```

### Styling Vector Layers

Apply styles using a dictionary:

```python
m.add_vector(
    "polygons.geojson",
    layer_name="Styled Polygons",
    style={
        "color": "#3388ff",          # Fill color
        "stroke_color": "#000000",   # Outline color
        "stroke_width": 2,           # Outline width
        "opacity": 0.7               # Fill opacity
    }
)
```

### Adding GeoDataFrames

If you have GeoPandas installed, you can add GeoDataFrames directly:

```python
import geopandas as gpd

gdf = gpd.read_file("data.gpkg")
m.add_gdf(gdf, layer_name="My GeoDataFrame", zoom_to_layer=True)
```

## Working with Raster Data

### Adding Raster Layers

```python
# Add a GeoTIFF
m.add_raster("elevation.tif", layer_name="Elevation")

# Add with zoom
m.add_raster("landsat.tif", zoom_to_layer=True)
```

### Applying Color Ramps

Use QGIS color ramps for visualization:

```python
m.add_raster(
    "temperature.tif",
    colormap="RdYlBu",       # Color ramp name
    vmin=-20,                # Min value for scaling
    vmax=40,                 # Max value for scaling
    layer_name="Temperature"
)
```

### Working with Specific Bands

```python
# Display a specific band
m.add_raster("landsat.tif", band=4, layer_name="NIR Band")
```

### Cloud Optimized GeoTIFFs (COGs)

```python
m.add_cog(
    "https://example.com/cog.tif",
    layer_name="Remote COG",
    zoom_to_layer=True
)
```

### WMS Layers

```python
m.add_wms(
    url="https://ows.mundialis.de/services/service",
    layers="TOPO-OSM-WMS",
    layer_name="Topo WMS",
    format="image/png"
)
```

## Time Slider

Create interactive time-based visualizations:

```python
# Define layers for each time step
layers = {
    "January": "data/jan.tif",
    "February": "data/feb.tif",
    "March": "data/mar.tif",
    "April": "data/apr.tif",
}

# Add time slider (creates a dockable panel)
m.add_time_slider(
    layers=layers,
    time_interval=2,    # Seconds between auto-play steps
    position="bottom"   # Dock position
)
```

The time slider panel includes:
- A slider to select time steps
- Previous/Next buttons
- Play/Pause for automatic animation

## Map Navigation

### Setting Center and Zoom

```python
# Set center (lat, lon) and zoom level
m.set_center(lat=40.7128, lon=-74.0060, zoom=12)
```

### Zooming to Layers

```python
# Zoom to a specific layer
m.zoom_to_layer("My Layer")

# Zoom to bounds (xmin, ymin, xmax, ymax)
m.zoom_to_bounds((-122.5, 37.5, -121.5, 38.5))
```

## Layer Management

### Listing Layers

```python
# Get all layer names
names = m.get_layer_names()
print(names)

# Get a specific layer object
layer = m.get_layer("My Layer")
```

### Removing Layers

```python
# Remove a specific layer
m.remove_layer("My Layer")

# Clear all layers (keep basemap)
m.clear_layers(keep_basemap=True)

# Clear everything
m.clear_layers(keep_basemap=False)
```

## Creating Custom Dock Widgets

Create custom interactive panels in QGIS:

```python
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget, QPushButton

# Create widget content
widget = QWidget()
layout = QVBoxLayout()
layout.addWidget(QLabel("My Custom Panel"))
layout.addWidget(QPushButton("Click Me"))
widget.setLayout(layout)

# Add as dockable panel
dock = m.create_dock_widget(
    title="My Panel",
    widget=widget,
    position="right"  # "left", "right", "top", "bottom"
)
```

## Exporting Maps

### Export to Image

```python
m.to_image(
    "output.png",
    width=1920,
    height=1080
)

# With specific extent
m.to_image(
    "cropped.png",
    width=800,
    height=600,
    extent=(-122.5, 37.5, -121.5, 38.5)
)
```

## Complete Example

```python
from qgis_map import Map

# Create map
m = Map(basemap="CartoDB.Positron")

# Add satellite imagery as secondary basemap
m.add_basemap("Esri.WorldImagery", visible=False)

# Add vector data
m.add_vector(
    "countries.geojson",
    layer_name="Countries",
    style={"color": "#3388ff", "stroke_color": "#ffffff", "opacity": 0.5}
)

# Add raster data
m.add_raster(
    "elevation.tif",
    colormap="terrain",
    layer_name="Elevation",
    opacity=0.7
)

# Zoom to area of interest
m.zoom_to_bounds((-125, 24, -66, 50))

# Export
m.to_image("map_output.png")
```
