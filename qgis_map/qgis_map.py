"""Main module for qgis-map.

This module provides a high-level Map class for working with QGIS,
similar to the leafmap Map class but designed for PyQGIS.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, Union
import os
import json
import fnmatch
import tempfile

# Use TYPE_CHECKING to avoid runtime import errors for type hints
if TYPE_CHECKING:
    from qgis.core import QgsRasterLayer, QgsVectorLayer
    from PyQt5.QtWidgets import QDockWidget, QWidget

try:
    from qgis.core import (
        Qgis,
        QgsApplication,
        QgsCoordinateReferenceSystem,
        QgsCoordinateTransform,
        QgsFeatureRequest,
        QgsLayerTreeGroup,
        QgsLayerTreeLayer,
        QgsMapLayerType,
        QgsPointXY,
        QgsProject,
        QgsRasterLayer,
        QgsRectangle,
        QgsRendererCategory,
        QgsCategorizedSymbolRenderer,
        QgsGraduatedSymbolRenderer,
        QgsRendererRange,
        QgsSingleSymbolRenderer,
        QgsSymbol,
        QgsVectorLayer,
        QgsWkbTypes,
        QgsRasterBandStats,
        QgsSingleBandGrayRenderer,
        QgsSingleBandPseudoColorRenderer,
        QgsMultiBandColorRenderer,
        QgsRasterShader,
        QgsColorRampShader,
        QgsStyle,
        QgsGradientColorRamp,
        QgsTemporalNavigationObject,
        QgsDateTimeRange,
        QgsInterval,
        QgsHeatmapRenderer,
        QgsClassificationQuantile,
        QgsClassificationEqualInterval,
        QgsClassificationJenks,
        QgsClassificationStandardDeviation,
        QgsMarkerSymbol,
        QgsProperty,
        QgsField,
        QgsFields,
        QgsFeature,
        QgsGeometry,
    )
    from qgis.gui import (
        QgsMapCanvas,
        QgsMapToolPan,
        QgsMapToolZoom,
        QgsLayerTreeMapCanvasBridge,
    )
    from qgis.utils import iface

    HAS_QGIS = True
except ImportError:
    HAS_QGIS = False
    iface = None

try:
    from PyQt5.QtCore import Qt, QDateTime, QDate, QTime
    from PyQt5.QtWidgets import (
        QDockWidget,
        QVBoxLayout,
        QHBoxLayout,
        QWidget,
        QLabel,
        QSlider,
        QPushButton,
        QComboBox,
        QSpinBox,
        QCheckBox,
        QGroupBox,
        QMainWindow,
    )
    from PyQt5.QtGui import QColor

    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False
    # Define placeholder for type hints
    QColor = None

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from pystac_client import Client as STACClient

    HAS_PYSTAC = True
except ImportError:
    HAS_PYSTAC = False

from .basemaps import BASEMAPS, get_basemap_url, get_xyz_uri, get_basemap_names


class Map:
    """A high-level Map class for QGIS, inspired by the leafmap API.

    This class provides a simple, user-friendly interface for common QGIS
    operations like adding basemaps, vector layers, raster layers, and
    creating interactive dockable panels.

    Attributes:
        project: The current QGIS project instance.
        canvas: The QGIS map canvas (if available).
        layers: A dictionary of layers added to the map.

    Example:
        >>> from qgis_map import Map
        >>> m = Map()
        >>> m.add_basemap("OpenStreetMap")
        >>> m.add_vector("path/to/data.shp", layer_name="My Layer")
        >>> m.add_raster("path/to/image.tif", layer_name="My Raster")
    """

    def __init__(
        self,
        center: Optional[Tuple[float, float]] = None,
        zoom: Optional[int] = None,
        crs: str = "EPSG:3857",
        basemap: Optional[str] = "OpenStreetMap",
        **kwargs,
    ):
        """Initialize a Map instance.

        Args:
            center: The initial center of the map as (latitude, longitude).
                Defaults to (0, 0).
            zoom: The initial zoom level. Defaults to 2.
            crs: The coordinate reference system. Defaults to "EPSG:3857".
            basemap: The initial basemap to add. Defaults to "OpenStreetMap".
                Set to None to skip adding a basemap.
            **kwargs: Additional keyword arguments.
        """
        if not HAS_QGIS:
            raise ImportError(
                "QGIS libraries are not available. "
                "Please run this code within QGIS or install PyQGIS."
            )

        self.project = QgsProject.instance()
        self._iface = iface
        self._layers: Dict[str, Any] = {}
        self._basemap_layers: List[str] = []
        self._crs = QgsCoordinateReferenceSystem(crs)
        self._center = center or (0, 0)
        self._zoom = zoom or 2
        self._time_slider_dock = None
        self._temporal_controller = None

        # Get the map canvas if running in QGIS
        if self._iface is not None:
            self.canvas = self._iface.mapCanvas()
        else:
            self.canvas = None

        # Set the project CRS
        self.project.setCrs(self._crs)

        # # Add initial basemap if specified
        # if basemap is not None:
        #     self.add_basemap(basemap)

        # Set initial center and zoom if canvas is available
        if self.canvas is not None and center is not None:
            self.set_center(center[0], center[1], zoom)

    @property
    def layers(self) -> Dict[str, Any]:
        """Get all layers added to the map.

        Returns:
            A dictionary mapping layer names to layer objects.
        """
        return self._layers

    def get_layer_names(self) -> List[str]:
        """Get the names of all layers in the project.

        Returns:
            A list of layer names.
        """
        return [layer.name() for layer in self.project.mapLayers().values()]

    def get_layer(self, name: str) -> Optional[Any]:
        """Get a layer by name.

        Args:
            name: The name of the layer.

        Returns:
            The layer object, or None if not found.
        """
        layers = self.project.mapLayersByName(name)
        return layers[0] if layers else None

    def set_center(self, lat: float, lon: float, zoom: Optional[int] = None) -> None:
        """Set the center of the map.

        Args:
            lat: Latitude of the center point.
            lon: Longitude of the center point.
            zoom: Optional zoom level to set.
        """
        if self.canvas is None:
            return

        # Transform coordinates if needed
        point = QgsPointXY(lon, lat)
        if self._crs.authid() != "EPSG:4326":
            transform = QgsCoordinateTransform(
                QgsCoordinateReferenceSystem("EPSG:4326"),
                self.canvas.mapSettings().destinationCrs(),
                self.project,
            )
            point = transform.transform(point)

        self.canvas.setCenter(point)

        if zoom is not None:
            # Approximate scale from zoom level
            scale = 591657550.500000 / (2**zoom)
            self.canvas.zoomScale(scale)

        self.canvas.refresh()

    def zoom_to_layer(self, layer_name: str) -> None:
        """Zoom the map to the extent of a layer.

        Args:
            layer_name: The name of the layer to zoom to.
        """
        layer = self.get_layer(layer_name)
        if layer is None:
            print(f"Layer '{layer_name}' not found.")
            return

        if self.canvas is not None:
            extent = layer.extent()
            # Transform extent if needed
            if layer.crs() != self.canvas.mapSettings().destinationCrs():
                transform = QgsCoordinateTransform(
                    layer.crs(),
                    self.canvas.mapSettings().destinationCrs(),
                    self.project,
                )
                extent = transform.transformBoundingBox(extent)
            self.canvas.setExtent(extent)
            self.canvas.refresh()
        elif self._iface is not None:
            self._iface.zoomToActiveLayer()

    def zoom_to_bounds(
        self, bounds: Tuple[float, float, float, float], crs: str = "EPSG:4326"
    ) -> None:
        """Zoom the map to the specified bounds.

        Args:
            bounds: The bounds as (xmin, ymin, xmax, ymax).
            crs: The CRS of the bounds. Defaults to "EPSG:4326".
        """
        if self.canvas is None:
            return

        xmin, ymin, xmax, ymax = bounds
        extent = QgsRectangle(xmin, ymin, xmax, ymax)

        # Transform if needed
        source_crs = QgsCoordinateReferenceSystem(crs)
        if source_crs != self.canvas.mapSettings().destinationCrs():
            transform = QgsCoordinateTransform(
                source_crs,
                self.canvas.mapSettings().destinationCrs(),
                self.project,
            )
            extent = transform.transformBoundingBox(extent)

        self.canvas.setExtent(extent)
        self.canvas.refresh()

    def add_basemap(
        self,
        basemap: str = "OpenStreetMap",
        layer_name: Optional[str] = None,
        visible: bool = True,
        opacity: float = 1.0,
        **kwargs,
    ) -> Optional["QgsRasterLayer"]:
        """Add a basemap to the map.

        Args:
            basemap: The name of the basemap or an XYZ tile URL.
                Available basemaps include: OpenStreetMap, CartoDB.Positron,
                CartoDB.DarkMatter, Esri.WorldImagery, SATELLITE, HYBRID, etc.
                Use get_basemap_names() to see all available basemaps.
            layer_name: The name for the layer. Defaults to the basemap name.
            visible: Whether the layer should be visible. Defaults to True.
            opacity: The layer opacity (0-1). Defaults to 1.0.
            **kwargs: Additional keyword arguments.

        Returns:
            The created raster layer, or None if failed.

        Example:
            >>> m = Map()
            >>> m.add_basemap("OpenStreetMap")
            >>> m.add_basemap("Esri.WorldImagery", layer_name="Satellite")
            >>> m.add_basemap(
            ...     "https://custom.tiles.com/{z}/{x}/{y}.png",
            ...     layer_name="Custom Tiles"
            ... )
        """
        # Determine the URL
        if basemap in BASEMAPS:
            url = BASEMAPS[basemap]["url"]
            name = layer_name or BASEMAPS[basemap]["name"]
        elif basemap.startswith("http"):
            url = basemap
            name = layer_name or "Custom Basemap"
        else:
            # Try case-insensitive match
            try:
                url = get_basemap_url(basemap)
                name = layer_name or basemap
            except ValueError as e:
                print(str(e))
                return None

        # Create the XYZ layer URI
        uri = get_xyz_uri(url)

        # Create and add the layer
        layer = QgsRasterLayer(uri, name, "wms")

        if not layer.isValid():
            print(f"Failed to load basemap: {name}")
            return None

        # Set opacity
        layer.renderer().setOpacity(opacity)

        # Add to project
        self.project.addMapLayer(layer, False)

        # Add to layer tree at the bottom (below other layers)
        root = self.project.layerTreeRoot()
        root.insertLayer(-1, layer)

        # Set visibility
        layer_node = root.findLayer(layer.id())
        if layer_node:
            layer_node.setItemVisibilityChecked(visible)

        # Track the layer
        self._layers[name] = layer
        self._basemap_layers.append(name)

        # Refresh canvas
        if self.canvas is not None:
            self.canvas.refresh()

        return layer

    def add_vector(
        self,
        source: str,
        layer_name: Optional[str] = None,
        style: Optional[Dict] = None,
        zoom_to_layer: bool = False,
        visible: bool = True,
        opacity: float = 1.0,
        encoding: str = "UTF-8",
        **kwargs,
    ) -> Optional["QgsVectorLayer"]:
        """Add a vector layer to the map.

        Args:
            source: Path to the vector file (shapefile, GeoJSON, GeoPackage, etc.)
                or a URL to a web service.
            layer_name: The name for the layer. Defaults to the file name.
            style: A dictionary specifying the style. Supported keys:
                - color: Fill color as hex string (e.g., "#ff0000") or RGB tuple.
                - stroke_color: Stroke/outline color.
                - stroke_width: Stroke width in pixels.
                - opacity: Fill opacity (0-1).
                - symbol: Symbol type for points ("circle", "square", "triangle").
            zoom_to_layer: Whether to zoom to the layer extent. Defaults to False.
            visible: Whether the layer should be visible. Defaults to True.
            opacity: Layer opacity (0-1). Defaults to 1.0.
            encoding: File encoding. Defaults to "UTF-8".
            **kwargs: Additional keyword arguments passed to QgsVectorLayer.

        Returns:
            The created vector layer, or None if failed.

        Example:
            >>> m = Map()
            >>> m.add_vector("data/cities.geojson", layer_name="Cities")
            >>> m.add_vector(
            ...     "data/polygons.shp",
            ...     style={"color": "#3388ff", "stroke_color": "#000000"},
            ...     zoom_to_layer=True
            ... )
        """
        # Determine the layer name
        if layer_name is None:
            layer_name = os.path.splitext(os.path.basename(source))[0]

        # Handle different source types
        if source.startswith("http"):
            # Web service (WFS, etc.)
            layer = QgsVectorLayer(source, layer_name, "WFS")
        else:
            # Local file
            layer = QgsVectorLayer(source, layer_name, "ogr")
            if encoding:
                layer.setProviderEncoding(encoding)

        if not layer.isValid():
            print(f"Failed to load vector layer: {source}")
            return None

        # Apply style if provided
        if style:
            self._apply_vector_style(layer, style)

        # Set opacity
        layer.setOpacity(opacity)

        # Add to project
        self.project.addMapLayer(layer)

        # Set visibility
        root = self.project.layerTreeRoot()
        layer_node = root.findLayer(layer.id())
        if layer_node:
            layer_node.setItemVisibilityChecked(visible)

        # Track the layer
        self._layers[layer_name] = layer

        # Zoom to layer if requested
        if zoom_to_layer:
            self.zoom_to_layer(layer_name)
        elif self.canvas is not None:
            self.canvas.refresh()

        return layer

    def add_gdf(
        self,
        gdf: Any,
        layer_name: str = "GeoDataFrame",
        style: Optional[Dict] = None,
        zoom_to_layer: bool = False,
        visible: bool = True,
        **kwargs,
    ) -> Optional["QgsVectorLayer"]:
        """Add a GeoDataFrame to the map.

        Args:
            gdf: A GeoPandas GeoDataFrame.
            layer_name: The name for the layer. Defaults to "GeoDataFrame".
            style: A dictionary specifying the style (see add_vector).
            zoom_to_layer: Whether to zoom to the layer extent. Defaults to False.
            visible: Whether the layer should be visible. Defaults to True.
            **kwargs: Additional keyword arguments.

        Returns:
            The created vector layer, or None if failed.
        """
        try:
            import geopandas as gpd
        except ImportError:
            print(
                "GeoPandas is required to add GeoDataFrames. Install with: pip install geopandas"
            )
            return None

        # Create a temporary file to store the GeoDataFrame
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as tmp:
            gdf.to_file(tmp.name, driver="GeoJSON")
            return self.add_vector(
                tmp.name,
                layer_name=layer_name,
                style=style,
                zoom_to_layer=zoom_to_layer,
                visible=visible,
                **kwargs,
            )

    def _apply_vector_style(self, layer: "QgsVectorLayer", style: Dict) -> None:
        """Apply a style dictionary to a vector layer.

        Args:
            layer: The vector layer to style.
            style: The style dictionary.
        """
        symbol = layer.renderer().symbol()

        if symbol is None:
            return

        # Get geometry type
        geom_type = layer.geometryType()

        # Apply fill color
        if "color" in style:
            color = self._parse_color(style["color"])
            if color:
                symbol.setColor(color)

        # Apply stroke/outline
        if "stroke_color" in style:
            color = self._parse_color(style["stroke_color"])
            if color:
                if geom_type == QgsWkbTypes.PolygonGeometry:
                    symbol.symbolLayer(0).setStrokeColor(color)
                elif geom_type == QgsWkbTypes.LineGeometry:
                    symbol.setColor(color)
                elif geom_type == QgsWkbTypes.PointGeometry:
                    symbol.symbolLayer(0).setStrokeColor(color)

        if "stroke_width" in style:
            width = style["stroke_width"]
            if geom_type == QgsWkbTypes.PolygonGeometry:
                symbol.symbolLayer(0).setStrokeWidth(width)
            elif geom_type == QgsWkbTypes.LineGeometry:
                symbol.setWidth(width)
            elif geom_type == QgsWkbTypes.PointGeometry:
                symbol.symbolLayer(0).setStrokeWidth(width)

        # Apply opacity
        if "opacity" in style:
            opacity = style["opacity"]
            color = symbol.color()
            color.setAlphaF(opacity)
            symbol.setColor(color)

        # Trigger a repaint
        layer.triggerRepaint()

    def _parse_color(self, color: Union[str, Tuple]) -> Optional["QColor"]:
        """Parse a color specification into a QColor.

        Args:
            color: A color as hex string, RGB tuple, or RGBA tuple.

        Returns:
            A QColor object, or None if parsing failed.
        """
        if isinstance(color, str):
            return QColor(color)
        elif isinstance(color, (list, tuple)):
            if len(color) == 3:
                return QColor(*color)
            elif len(color) == 4:
                return QColor(*color[:3], int(color[3] * 255))
        return None

    def add_raster(
        self,
        source: str,
        layer_name: Optional[str] = None,
        band: Optional[int] = None,
        colormap: Optional[str] = None,
        vmin: Optional[float] = None,
        vmax: Optional[float] = None,
        nodata: Optional[float] = None,
        zoom_to_layer: bool = False,
        visible: bool = True,
        opacity: float = 1.0,
        **kwargs,
    ) -> Optional["QgsRasterLayer"]:
        """Add a raster layer to the map.

        Args:
            source: Path to the raster file (GeoTIFF, etc.) or a URL.
            layer_name: The name for the layer. Defaults to the file name.
            band: The band number to display (1-indexed). Defaults to None (auto).
            colormap: The name of a color ramp to apply (e.g., "viridis", "Spectral").
            vmin: Minimum value for color scaling. Defaults to band minimum.
            vmax: Maximum value for color scaling. Defaults to band maximum.
            nodata: The nodata value. Defaults to the layer's nodata value.
            zoom_to_layer: Whether to zoom to the layer extent. Defaults to False.
            visible: Whether the layer should be visible. Defaults to True.
            opacity: Layer opacity (0-1). Defaults to 1.0.
            **kwargs: Additional keyword arguments.

        Returns:
            The created raster layer, or None if failed.

        Example:
            >>> m = Map()
            >>> m.add_raster("elevation.tif", colormap="terrain", zoom_to_layer=True)
            >>> m.add_raster("landsat.tif", band=4, vmin=0, vmax=3000)
        """
        # Determine the layer name
        if layer_name is None:
            layer_name = os.path.splitext(os.path.basename(source))[0]

        # Create the raster layer
        layer = QgsRasterLayer(source, layer_name)

        if not layer.isValid():
            print(f"Failed to load raster layer: {source}")
            return None

        # Get the data provider
        provider = layer.dataProvider()

        # Set nodata if specified
        if nodata is not None:
            provider.setNoDataValue(1, nodata)

        # Apply colormap/renderer
        if colormap or band or vmin is not None or vmax is not None:
            self._apply_raster_style(layer, band, colormap, vmin, vmax)

        # Set opacity
        layer.renderer().setOpacity(opacity)

        # Add to project
        self.project.addMapLayer(layer)

        # Set visibility
        root = self.project.layerTreeRoot()
        layer_node = root.findLayer(layer.id())
        if layer_node:
            layer_node.setItemVisibilityChecked(visible)

        # Track the layer
        self._layers[layer_name] = layer

        # Zoom to layer if requested
        if zoom_to_layer:
            self.zoom_to_layer(layer_name)
        elif self.canvas is not None:
            self.canvas.refresh()

        return layer

    def _apply_raster_style(
        self,
        layer: "QgsRasterLayer",
        band: Optional[int],
        colormap: Optional[str],
        vmin: Optional[float],
        vmax: Optional[float],
    ) -> None:
        """Apply styling to a raster layer.

        Args:
            layer: The raster layer to style.
            band: The band number (1-indexed).
            colormap: The name of the color ramp.
            vmin: Minimum value for color scaling.
            vmax: Maximum value for color scaling.
        """
        provider = layer.dataProvider()
        band_count = provider.bandCount()

        if band is None:
            band = 1

        # Get statistics for the band
        stats = provider.bandStatistics(band, QgsRasterBandStats.All, layer.extent(), 0)

        if vmin is None:
            vmin = stats.minimumValue
        if vmax is None:
            vmax = stats.maximumValue

        if band_count == 1 or band is not None:
            # Single band rendering
            if colormap:
                # Use a color ramp shader
                shader = QgsRasterShader()
                color_ramp_shader = QgsColorRampShader()
                color_ramp_shader.setColorRampType(QgsColorRampShader.Interpolated)

                # Try to get the color ramp from QGIS styles
                style = QgsStyle.defaultStyle()
                ramp = style.colorRamp(colormap)

                if ramp is None:
                    # Create a default gradient
                    color_ramp_shader.setColorRampItemList(
                        [
                            QgsColorRampShader.ColorRampItem(vmin, QColor(68, 1, 84)),
                            QgsColorRampShader.ColorRampItem(
                                (vmin + vmax) / 2, QColor(59, 82, 139)
                            ),
                            QgsColorRampShader.ColorRampItem(
                                vmax, QColor(253, 231, 37)
                            ),
                        ]
                    )
                else:
                    # Use the color ramp
                    items = []
                    num_classes = 10
                    for i in range(num_classes + 1):
                        value = vmin + (vmax - vmin) * i / num_classes
                        color = ramp.color(i / num_classes)
                        items.append(QgsColorRampShader.ColorRampItem(value, color))
                    color_ramp_shader.setColorRampItemList(items)

                shader.setRasterShaderFunction(color_ramp_shader)
                renderer = QgsSingleBandPseudoColorRenderer(provider, band, shader)
            else:
                # Grayscale rendering
                renderer = QgsSingleBandGrayRenderer(provider, band)
                renderer.setContrastEnhancement(layer.renderer().contrastEnhancement())

            layer.setRenderer(renderer)

        elif band_count >= 3:
            # Multi-band RGB rendering
            renderer = QgsMultiBandColorRenderer(provider, 1, 2, 3)
            layer.setRenderer(renderer)

        layer.triggerRepaint()

    def add_cog(
        self,
        url: str,
        layer_name: Optional[str] = None,
        zoom_to_layer: bool = False,
        **kwargs,
    ) -> Optional["QgsRasterLayer"]:
        """Add a Cloud Optimized GeoTIFF (COG) to the map.

        Args:
            url: The URL to the COG file.
            layer_name: The name for the layer. Defaults to "COG".
            zoom_to_layer: Whether to zoom to the layer extent. Defaults to False.
            **kwargs: Additional keyword arguments passed to add_raster.

        Returns:
            The created raster layer, or None if failed.
        """
        if layer_name is None:
            layer_name = "COG"

        # Use GDAL's vsicurl for remote access
        vsicurl_url = f"/vsicurl/{url}"

        return self.add_raster(
            vsicurl_url,
            layer_name=layer_name,
            zoom_to_layer=zoom_to_layer,
            **kwargs,
        )

    def add_wms(
        self,
        url: str,
        layers: str,
        layer_name: Optional[str] = None,
        format: str = "image/png",
        crs: str = "EPSG:4326",
        visible: bool = True,
        opacity: float = 1.0,
        **kwargs,
    ) -> Optional["QgsRasterLayer"]:
        """Add a WMS layer to the map.

        Args:
            url: The WMS service URL.
            layers: The layer name(s) to request from the WMS.
            layer_name: The display name for the layer.
            format: The image format. Defaults to "image/png".
            crs: The CRS to request. Defaults to "EPSG:4326".
            visible: Whether the layer should be visible. Defaults to True.
            opacity: Layer opacity (0-1). Defaults to 1.0.
            **kwargs: Additional keyword arguments.

        Returns:
            The created raster layer, or None if failed.
        """
        if layer_name is None:
            layer_name = layers

        # Build WMS URI
        uri = (
            f"url={url}&"
            f"layers={layers}&"
            f"format={format}&"
            f"crs={crs}&"
            f"styles="
        )

        layer = QgsRasterLayer(uri, layer_name, "wms")

        if not layer.isValid():
            print(f"Failed to load WMS layer: {url}")
            return None

        layer.renderer().setOpacity(opacity)

        self.project.addMapLayer(layer)

        # Set visibility
        root = self.project.layerTreeRoot()
        layer_node = root.findLayer(layer.id())
        if layer_node:
            layer_node.setItemVisibilityChecked(visible)

        self._layers[layer_name] = layer

        if self.canvas is not None:
            self.canvas.refresh()

        return layer

    def add_time_slider(
        self,
        layers: Optional[Dict[str, str]] = None,
        labels: Optional[List[str]] = None,
        time_interval: int = 1,
        position: str = "bottomright",
        time_format: str = "%Y-%m-%d",
        **kwargs,
    ) -> Optional["QDockWidget"]:
        """Add a time slider to control temporal layers or switch between layers.

        This method creates a dockable panel with a slider that can either:
        1. Control the temporal properties of a single layer with time-enabled data.
        2. Switch between multiple layers representing different time periods.

        Args:
            layers: A dictionary mapping labels to layer sources (file paths or URLs).
                If provided, clicking the slider will switch between these layers.
            labels: A list of labels for the time steps (used with `layers`).
            time_interval: Time interval between steps in seconds. Defaults to 1.
            position: Position of the dock widget ("left", "right", "top", "bottom").
                Defaults to "bottomright".
            time_format: The format string for displaying time labels.
            **kwargs: Additional keyword arguments.

        Returns:
            The created QDockWidget, or None if failed.

        Example:
            >>> m = Map()
            >>> # Switch between multiple raster layers
            >>> layers = {
            ...     "2020": "data/ndvi_2020.tif",
            ...     "2021": "data/ndvi_2021.tif",
            ...     "2022": "data/ndvi_2022.tif",
            ... }
            >>> m.add_time_slider(layers=layers)
        """
        if not HAS_PYQT:
            print("PyQt5 is required for time slider functionality.")
            return None

        if self._iface is None:
            print("Time slider requires running within QGIS.")
            return None

        # Create the dock widget
        dock = QDockWidget("Time Slider", self._iface.mainWindow())
        dock.setObjectName("TimeSliderDock")

        # Create the main widget
        main_widget = QWidget()
        layout = QVBoxLayout()

        if layers is not None:
            # Mode 1: Switch between multiple layers
            layer_list = list(layers.items())
            if labels is None:
                labels = list(layers.keys())

            # Load all layers but hide them except the first
            loaded_layers = []
            failed_layers = []
            for i, (label, source) in enumerate(layer_list):
                # Determine if raster or vector
                if source.lower().endswith(
                    (".tif", ".tiff", ".img", ".jp2", ".png", ".jpg")
                ):
                    layer = self.add_raster(
                        source,
                        layer_name=label,
                        visible=(i == 0),
                        zoom_to_layer=(i == 0),
                    )
                else:
                    layer = self.add_vector(
                        source,
                        layer_name=label,
                        visible=(i == 0),
                        zoom_to_layer=(i == 0),
                    )

                if layer is None:
                    failed_layers.append((label, source))
                    print(f"Warning: Failed to load layer '{label}' from {source}")
                loaded_layers.append(layer)

            # Check if any layers were loaded successfully
            if all(layer is None for layer in loaded_layers):
                print(
                    "Error: No layers were loaded successfully. Please check your file paths."
                )
                if failed_layers:
                    print("Failed layers:")
                    for label, source in failed_layers:
                        print(f"  - {label}: {source}")
                return None

            # Create the slider
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(0)
            slider.setMaximum(len(layer_list) - 1)
            slider.setValue(0)
            slider.setTickPosition(QSlider.TicksBelow)
            slider.setTickInterval(1)

            # Create label display
            label_display = QLabel(labels[0])
            label_display.setAlignment(Qt.AlignCenter)

            # Play/Pause button
            play_btn = QPushButton("▶ Play")
            play_btn.setCheckable(True)

            # Timer for auto-play
            from PyQt5.QtCore import QTimer

            timer = QTimer()
            timer.setInterval(time_interval * 1000)

            def on_slider_change(value):
                label_display.setText(labels[value])
                # Hide all layers except the current one
                for i, layer in enumerate(loaded_layers):
                    if layer is not None:
                        root = self.project.layerTreeRoot()
                        layer_node = root.findLayer(layer.id())
                        if layer_node:
                            layer_node.setItemVisibilityChecked(i == value)
                if self.canvas:
                    self.canvas.refresh()

            def on_timeout():
                current = slider.value()
                next_val = (current + 1) % len(layer_list)
                slider.setValue(next_val)

            def on_play_clicked(checked):
                if checked:
                    play_btn.setText("⏸ Pause")
                    timer.start()
                else:
                    play_btn.setText("▶ Play")
                    timer.stop()

            slider.valueChanged.connect(on_slider_change)
            timer.timeout.connect(on_timeout)
            play_btn.clicked.connect(on_play_clicked)

            # Add widgets to layout
            layout.addWidget(label_display)
            layout.addWidget(slider)

            # Add control buttons
            btn_layout = QHBoxLayout()
            prev_btn = QPushButton("◀ Prev")
            next_btn = QPushButton("Next ▶")
            prev_btn.clicked.connect(
                lambda: slider.setValue(max(0, slider.value() - 1))
            )
            next_btn.clicked.connect(
                lambda: slider.setValue(min(len(layer_list) - 1, slider.value() + 1))
            )
            btn_layout.addWidget(prev_btn)
            btn_layout.addWidget(play_btn)
            btn_layout.addWidget(next_btn)
            layout.addLayout(btn_layout)

        else:
            # Mode 2: Control QGIS temporal navigation
            info_label = QLabel(
                "Use the QGIS Temporal Controller for time-enabled layers.\n"
                "Enable temporal properties on your layer first."
            )
            info_label.setWordWrap(True)
            layout.addWidget(info_label)

            # Add a button to open the temporal controller
            open_temporal_btn = QPushButton("Open Temporal Controller")
            open_temporal_btn.clicked.connect(
                lambda: (
                    self._iface.mainWindow()
                    .findChild(QDockWidget, "TemporalControllerDock")
                    .show()
                    if self._iface.mainWindow().findChild(
                        QDockWidget, "TemporalControllerDock"
                    )
                    else None
                )
            )
            layout.addWidget(open_temporal_btn)

        main_widget.setLayout(layout)
        dock.setWidget(main_widget)

        # Determine dock area
        dock_areas = {
            "left": Qt.LeftDockWidgetArea,
            "right": Qt.RightDockWidgetArea,
            "top": Qt.TopDockWidgetArea,
            "bottom": Qt.BottomDockWidgetArea,
            "bottomright": Qt.BottomDockWidgetArea,
            "bottomleft": Qt.BottomDockWidgetArea,
            "topright": Qt.TopDockWidgetArea,
            "topleft": Qt.TopDockWidgetArea,
        }
        area = dock_areas.get(position.lower(), Qt.BottomDockWidgetArea)

        self._iface.addDockWidget(area, dock)
        self._time_slider_dock = dock

        return dock

    def remove_layer(self, layer_name: str) -> bool:
        """Remove a layer from the map.

        Args:
            layer_name: The name of the layer to remove.

        Returns:
            True if the layer was removed, False otherwise.
        """
        layer = self.get_layer(layer_name)
        if layer is None:
            print(f"Layer '{layer_name}' not found.")
            return False

        self.project.removeMapLayer(layer.id())

        if layer_name in self._layers:
            del self._layers[layer_name]

        if layer_name in self._basemap_layers:
            self._basemap_layers.remove(layer_name)

        if self.canvas is not None:
            self.canvas.refresh()

        return True

    def clear_layers(self, keep_basemap: bool = True) -> None:
        """Remove all layers from the map.

        Args:
            keep_basemap: Whether to keep basemap layers. Defaults to True.
        """
        layers_to_remove = []

        for layer in self.project.mapLayers().values():
            if keep_basemap and layer.name() in self._basemap_layers:
                continue
            layers_to_remove.append(layer.id())

        for layer_id in layers_to_remove:
            self.project.removeMapLayer(layer_id)

        # Update internal tracking
        if keep_basemap:
            self._layers = {
                name: layer
                for name, layer in self._layers.items()
                if name in self._basemap_layers
            }
        else:
            self._layers = {}
            self._basemap_layers = []

        if self.canvas is not None:
            self.canvas.refresh()

    def add_layer_control(self) -> None:
        """Show the layer panel in QGIS.

        This opens or focuses the Layers panel in QGIS.
        """
        if self._iface is not None:
            # The layer panel is usually already visible, but ensure it is
            layers_dock = self._iface.mainWindow().findChild(QDockWidget, "Layers")
            if layers_dock:
                layers_dock.show()
                layers_dock.raise_()

    def to_image(
        self,
        output_path: str,
        width: int = 1920,
        height: int = 1080,
        extent: Optional[Tuple[float, float, float, float]] = None,
        **kwargs,
    ) -> str:
        """Export the current map view to an image.

        Args:
            output_path: The output file path.
            width: Image width in pixels. Defaults to 1920.
            height: Image height in pixels. Defaults to 1080.
            extent: Optional extent as (xmin, ymin, xmax, ymax).
            **kwargs: Additional keyword arguments.

        Returns:
            The output file path.
        """
        from qgis.core import QgsMapSettings, QgsMapRendererCustomPainterJob
        from PyQt5.QtGui import QImage, QPainter
        from PyQt5.QtCore import QSize

        # Set up map settings
        settings = QgsMapSettings()
        settings.setOutputSize(QSize(width, height))
        settings.setLayers(list(self.project.mapLayers().values()))

        if extent:
            xmin, ymin, xmax, ymax = extent
            settings.setExtent(QgsRectangle(xmin, ymin, xmax, ymax))
        elif self.canvas:
            settings.setExtent(self.canvas.extent())

        settings.setBackgroundColor(QColor(255, 255, 255))
        settings.setDestinationCrs(self.project.crs())

        # Create image
        image = QImage(QSize(width, height), QImage.Format_ARGB32)
        image.fill(Qt.white)

        # Render
        painter = QPainter(image)
        job = QgsMapRendererCustomPainterJob(settings, painter)
        job.start()
        job.waitForFinished()
        painter.end()

        # Save
        image.save(output_path)

        return output_path

    def add_legend(
        self,
        title: str = "Legend",
        legend_dict: Optional[Dict[str, str]] = None,
        labels: Optional[List[str]] = None,
        colors: Optional[List[Union[str, Tuple]]] = None,
        position: str = "bottomright",
        layer_name: Optional[str] = None,
        **kwargs,
    ) -> Optional["QDockWidget"]:
        """Add a legend to the map.

        Args:
            title: Title of the legend. Defaults to "Legend".
            legend_dict: A dictionary containing legend items as keys and colors as values.
                If provided, labels and colors will be ignored.
            labels: A list of legend labels.
            colors: A list of legend colors (hex strings, RGB tuples, or color names).
            position: Position of the legend ("topleft", "topright", "bottomleft", "bottomright").
                Defaults to "bottomright".
            layer_name: Layer name to associate the legend with. Defaults to None.
            **kwargs: Additional keyword arguments (e.g., width, height).

        Returns:
            The created QDockWidget, or None if failed.

        Example:
            >>> m = Map()
            >>> m.add_legend(
            ...     title="Land Cover",
            ...     labels=["Forest", "Water", "Urban"],
            ...     colors=["#228B22", "#4169E1", "#DC143C"]
            ... )
            >>> # Or using a dictionary
            >>> m.add_legend(
            ...     legend_dict={"Forest": "#228B22", "Water": "#4169E1", "Urban": "#DC143C"}
            ... )
        """
        if not HAS_PYQT:
            print("PyQt5 is required for legend functionality.")
            return None

        if self._iface is None:
            print("Legend requires running within QGIS.")
            return None

        # Process legend_dict
        if legend_dict is not None:
            if not isinstance(legend_dict, dict):
                print("The legend_dict must be a dictionary.")
                return None
            labels = list(legend_dict.keys())
            colors = list(legend_dict.values())

        # Validate labels and colors
        if labels is None:
            labels = ["One", "Two", "Three", "Four"]
        if colors is None:
            colors = ["#8DD3C7", "#FFFFB3", "#BEBADA", "#FB8072"]

        if not isinstance(labels, list):
            print("The labels must be a list.")
            return None
        if not isinstance(colors, list):
            print("The colors must be a list.")
            return None

        # Convert RGB tuples to hex if needed
        converted_colors = []
        for color in colors:
            if isinstance(color, tuple):
                if len(color) == 3:
                    converted_colors.append(
                        "#{:02x}{:02x}{:02x}".format(
                            int(color[0]), int(color[1]), int(color[2])
                        )
                    )
                elif len(color) == 4:
                    converted_colors.append(
                        "#{:02x}{:02x}{:02x}".format(
                            int(color[0]), int(color[1]), int(color[2])
                        )
                    )
                else:
                    print(f"Invalid color tuple: {color}")
                    return None
            elif isinstance(color, str):
                # Handle colors without # prefix
                if len(color) == 6 and not color.startswith("#"):
                    converted_colors.append("#" + color)
                else:
                    converted_colors.append(color)
            else:
                print(f"Invalid color type: {type(color)}")
                return None
        colors = converted_colors

        if len(labels) != len(colors):
            print("The labels and colors must be the same length.")
            return None

        # Validate position
        allowed_positions = ["topleft", "topright", "bottomleft", "bottomright"]
        if position not in allowed_positions:
            print(f"The position must be one of: {', '.join(allowed_positions)}")
            return None

        # Create the dock widget
        dock = QDockWidget(title, self._iface.mainWindow())
        dock.setObjectName(f"{title}LegendDock")

        # Create the main widget with scroll area
        from PyQt5.QtWidgets import QScrollArea

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        main_widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # Add legend items
        for label, color in zip(labels, colors):
            item_layout = QHBoxLayout()

            # Color box
            color_label = QLabel()
            color_label.setFixedSize(20, 20)
            color_label.setStyleSheet(
                f"background-color: {color}; border: 1px solid #000000;"
            )

            # Label text
            text_label = QLabel(label)

            item_layout.addWidget(color_label)
            item_layout.addWidget(text_label)
            item_layout.addStretch()

            layout.addLayout(item_layout)

        layout.addStretch()
        main_widget.setLayout(layout)
        scroll.setWidget(main_widget)
        dock.setWidget(scroll)

        # Set size constraints if provided
        if "width" in kwargs:
            dock.setMinimumWidth(kwargs["width"])
        else:
            dock.setMinimumWidth(150)

        if "height" in kwargs:
            dock.setMinimumHeight(kwargs["height"])

        # Determine dock area
        dock_areas = {
            "topleft": Qt.LeftDockWidgetArea,
            "topright": Qt.RightDockWidgetArea,
            "bottomleft": Qt.LeftDockWidgetArea,
            "bottomright": Qt.RightDockWidgetArea,
        }
        area = dock_areas.get(position.lower(), Qt.RightDockWidgetArea)

        self._iface.addDockWidget(area, dock)

        return dock

    def add_colorbar(
        self,
        colors: List[Union[str, Tuple]],
        vmin: float = 0,
        vmax: float = 1.0,
        index: Optional[List[float]] = None,
        caption: str = "",
        categorical: bool = False,
        step: Optional[int] = None,
        width: int = 300,
        height: int = 60,
        position: str = "bottomright",
        **kwargs,
    ) -> Optional["QDockWidget"]:
        """Add a colorbar to the map.

        Args:
            colors: The set of colors for interpolation. Can be:
                - List of hex strings (e.g., ["#ff0000", "#00ff00", "#0000ff"])
                - List of RGB tuples (e.g., [(255, 0, 0), (0, 255, 0), (0, 0, 255)])
                - List of color names (e.g., ["red", "green", "blue"])
            vmin: The minimum value for the colormap. Defaults to 0.
            vmax: The maximum value for the colormap. Defaults to 1.0.
            index: The values corresponding to each color. Must be sorted and same length as colors.
                If None, a regular grid between vmin and vmax is created.
            caption: The caption/title for the colorbar. Defaults to "".
            categorical: Whether to create a categorical (discrete) colorbar. Defaults to False.
            step: The number of steps for categorical colorbar. Defaults to None.
            width: The width of the colorbar widget in pixels. Defaults to 300.
            height: The height of the colorbar widget in pixels. Defaults to 60.
            position: Position of the colorbar ("topleft", "topright", "bottomleft", "bottomright").
                Defaults to "bottomright".
            **kwargs: Additional keyword arguments.

        Returns:
            The created QDockWidget, or None if failed.

        Example:
            >>> m = Map()
            >>> m.add_colorbar(
            ...     colors=["blue", "cyan", "yellow", "red"],
            ...     vmin=0,
            ...     vmax=100,
            ...     caption="Temperature (°C)"
            ... )
            >>> # Categorical colorbar
            >>> m.add_colorbar(
            ...     colors=["#00ff00", "#ffff00", "#ff0000"],
            ...     vmin=0,
            ...     vmax=1,
            ...     categorical=True,
            ...     caption="Risk Level"
            ... )
        """
        if not HAS_PYQT:
            print("PyQt5 is required for colorbar functionality.")
            return None

        if self._iface is None:
            print("Colorbar requires running within QGIS.")
            return None

        from PyQt5.QtWidgets import QScrollArea
        from PyQt5.QtGui import QPainter, QLinearGradient
        from PyQt5.QtCore import QRectF

        # Convert colors to QColor
        qcolors = []
        for color in colors:
            if isinstance(color, tuple):
                if len(color) == 3:
                    qcolors.append(QColor(int(color[0]), int(color[1]), int(color[2])))
                elif len(color) == 4:
                    qcolors.append(
                        QColor(
                            int(color[0]),
                            int(color[1]),
                            int(color[2]),
                            int(color[3] * 255) if color[3] <= 1 else int(color[3]),
                        )
                    )
            elif isinstance(color, str):
                if len(color) == 6 and not color.startswith("#"):
                    qcolors.append(QColor("#" + color))
                else:
                    qcolors.append(QColor(color))
            else:
                print(f"Invalid color type: {type(color)}")
                return None

        # Create index if not provided
        if index is None:
            index = [
                vmin + (vmax - vmin) * i / (len(qcolors) - 1)
                for i in range(len(qcolors))
            ]
        elif len(index) != len(qcolors):
            print("The index and colors must be the same length.")
            return None

        # Create the dock widget
        title = caption if caption else "Colorbar"
        dock = QDockWidget(title, self._iface.mainWindow())
        dock.setObjectName(f"{title}ColorbarDock")

        # Create the main widget
        main_widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # Create colorbar as a pixmap and display in QLabel
        from PyQt5.QtGui import QPixmap, QImage
        from PyQt5.QtCore import Qt as QtCore

        # Create the colorbar image
        bar_height = 30
        pixmap = QPixmap(width, bar_height)
        pixmap.fill(QtCore.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        if categorical and step and step > 1:
            # Draw discrete color segments
            segment_width = width / step
            for i in range(step):
                if step > 1:
                    color_idx = int(i * (len(qcolors) - 1) / (step - 1))
                else:
                    color_idx = 0
                color_idx = min(color_idx, len(qcolors) - 1)
                painter.fillRect(
                    int(i * segment_width),
                    0,
                    int(segment_width + 1),
                    bar_height,
                    qcolors[color_idx],
                )
        else:
            # Draw continuous gradient
            gradient = QLinearGradient(0, 0, width, 0)
            if len(qcolors) > 1:
                for i, color in enumerate(qcolors):
                    pos = i / (len(qcolors) - 1)
                    gradient.setColorAt(pos, color)
            else:
                gradient.setColorAt(0, qcolors[0])
                gradient.setColorAt(1, qcolors[0])
            painter.fillRect(0, 0, width, bar_height, gradient)

        # Draw border
        painter.setPen(QColor("#000000"))
        painter.drawRect(0, 0, width - 1, bar_height - 1)
        painter.end()

        # Create label with the colorbar pixmap
        colorbar_label = QLabel()
        colorbar_label.setPixmap(pixmap)
        colorbar_label.setMinimumSize(width, bar_height)
        colorbar_label.setMaximumSize(width, bar_height)
        layout.addWidget(colorbar_label)

        # Add value labels
        labels_layout = QHBoxLayout()
        vmin_label = QLabel(f"{vmin:.2f}")
        vmax_label = QLabel(f"{vmax:.2f}")
        labels_layout.addWidget(vmin_label)
        labels_layout.addStretch()
        labels_layout.addWidget(vmax_label)
        layout.addLayout(labels_layout)

        main_widget.setLayout(layout)
        dock.setWidget(main_widget)

        # Set size constraints instead of fixed size
        dock.setMinimumWidth(width + 40)
        dock.setMaximumWidth(width + 60)
        dock.setMinimumHeight(height + 80)
        dock.setMaximumHeight(height + 100)

        # Determine dock area
        dock_areas = {
            "topleft": Qt.LeftDockWidgetArea,
            "topright": Qt.RightDockWidgetArea,
            "bottomleft": Qt.LeftDockWidgetArea,
            "bottomright": Qt.RightDockWidgetArea,
        }
        area = dock_areas.get(position.lower(), Qt.RightDockWidgetArea)

        self._iface.addDockWidget(area, dock)

        return dock

    def create_dock_widget(
        self,
        title: str,
        widget: Optional["QWidget"] = None,
        position: str = "right",
    ) -> "QDockWidget":
        """Create a custom dockable panel in QGIS.

        Args:
            title: The title of the dock widget.
            widget: The widget to place in the dock. If None, creates an empty container.
            position: Position of the dock ("left", "right", "top", "bottom").

        Returns:
            The created QDockWidget.
        """
        if self._iface is None:
            raise RuntimeError("Dock widgets require running within QGIS.")

        dock = QDockWidget(title, self._iface.mainWindow())
        dock.setObjectName(f"{title}Dock")

        if widget is None:
            widget = QWidget()
            widget.setLayout(QVBoxLayout())

        dock.setWidget(widget)

        dock_areas = {
            "left": Qt.LeftDockWidgetArea,
            "right": Qt.RightDockWidgetArea,
            "top": Qt.TopDockWidgetArea,
            "bottom": Qt.BottomDockWidgetArea,
        }
        area = dock_areas.get(position.lower(), Qt.RightDockWidgetArea)

        self._iface.addDockWidget(area, dock)

        return dock

    def layer_opacity(
        self,
        layer_name: str,
        opacity: float,
    ) -> bool:
        """Set opacity for an existing layer.

        Args:
            layer_name: Name of the layer to modify.
            opacity: Opacity value between 0.0 (transparent) and 1.0 (opaque).

        Returns:
            True if opacity was set successfully, False if layer not found.

        Example:
            >>> m = Map()
            >>> m.add_vector("data.shp", layer_name="test")
            >>> m.layer_opacity("test", 0.5)
            True
        """
        if not HAS_QGIS:
            print("QGIS libraries not available")
            return False

        # Get the layer
        layer = self.get_layer(layer_name)
        if layer is None:
            print(f"Layer '{layer_name}' not found")
            return False

        # Clamp opacity to valid range
        opacity = max(0.0, min(1.0, opacity))

        try:
            # Set opacity based on layer type
            if layer.type() == QgsMapLayerType.VectorLayer:
                layer.setOpacity(opacity)
            elif layer.type() == QgsMapLayerType.RasterLayer:
                layer.renderer().setOpacity(opacity)

            # Trigger repaint
            layer.triggerRepaint()

            if self.canvas:
                self.canvas.refresh()

            return True

        except Exception as e:
            print(f"Error setting layer opacity: {e}")
            return False

    def zoom_to_gdf(
        self,
        gdf: Any,
        crs: Optional[str] = None,
    ) -> None:
        """Zoom map to GeoDataFrame extent.

        Args:
            gdf: GeoDataFrame to zoom to.
            crs: Optional CRS string. If None, uses gdf.crs.

        Example:
            >>> import geopandas as gpd
            >>> m = Map()
            >>> gdf = gpd.read_file("data.geojson")
            >>> m.zoom_to_gdf(gdf)
        """
        if not HAS_QGIS:
            print("QGIS libraries not available")
            return

        try:
            # Get bounds from GeoDataFrame
            bounds = gdf.total_bounds  # Returns (minx, miny, maxx, maxy)

            # Get CRS from gdf if not specified
            if crs is None:
                crs = str(gdf.crs)

            # Use existing zoom_to_bounds method
            self.zoom_to_bounds(bounds, crs=crs)

        except Exception as e:
            print(f"Error zooming to GeoDataFrame: {e}")

    def find_layer(
        self,
        name: str,
    ) -> Optional[List["QgsMapLayer"]]:
        """Find all layers matching a name pattern.

        Supports exact matching and wildcard patterns using * and ?.

        Args:
            name: Layer name or pattern to search for.

        Returns:
            List of matching layers, or None if no matches found.

        Example:
            >>> m = Map()
            >>> m.add_vector("data.shp", layer_name="test1")
            >>> m.add_vector("data2.shp", layer_name="test2")
            >>> layers = m.find_layer("test*")
            >>> len(layers)
            2
        """
        if not HAS_QGIS:
            print("QGIS libraries not available")
            return None

        # First try exact match
        exact_matches = self.project.mapLayersByName(name)
        if exact_matches:
            return exact_matches

        # If no exact match, try pattern matching
        all_layers = list(self.project.mapLayers().values())
        matches = []

        for layer in all_layers:
            if fnmatch.fnmatch(layer.name(), name):
                matches.append(layer)

        return matches if matches else None

    def add_geojson(
        self,
        source: Union[str, Dict],
        layer_name: Optional[str] = None,
        style: Optional[Dict] = None,
        zoom_to_layer: bool = False,
        **kwargs,
    ) -> Optional["QgsVectorLayer"]:
        """Add a GeoJSON layer from file, URL, or Python dict.

        Args:
            source: GeoJSON file path, URL, or Python dictionary.
            layer_name: Name for the layer. If None, auto-generated.
            style: Optional style dictionary with keys: color, stroke_color, stroke_width, opacity, symbol.
            zoom_to_layer: Whether to zoom to layer extent. Defaults to False.
            **kwargs: Additional keyword arguments passed to add_vector.

        Returns:
            The created vector layer, or None if creation failed.

        Example:
            >>> m = Map()
            >>> # From file
            >>> m.add_geojson("data.geojson")
            >>> # From URL
            >>> m.add_geojson("https://example.com/data.geojson")
            >>> # From dict
            >>> geojson_dict = {"type": "FeatureCollection", "features": [...]}
            >>> m.add_geojson(geojson_dict, layer_name="custom")
        """
        if not HAS_QGIS:
            print("QGIS libraries not available")
            return None

        temp_file = None

        try:
            # Handle different source types
            if isinstance(source, dict):
                # Python dictionary - save to temporary file
                temp_file = tempfile.NamedTemporaryFile(
                    mode="w", suffix=".geojson", delete=False
                )
                json.dump(source, temp_file)
                temp_file.close()
                file_path = temp_file.name

            elif source.startswith(("http://", "https://")):
                # URL - download the file
                from . import common

                file_path = common.download_file(source)

            else:
                # Assume it's a file path
                file_path = source

            # Use existing add_vector method
            layer = self.add_vector(
                file_path,
                layer_name=layer_name,
                style=style,
                zoom_to_layer=zoom_to_layer,
                **kwargs,
            )

            return layer

        except Exception as e:
            print(f"Error adding GeoJSON: {e}")
            return None

        finally:
            # Clean up temporary file if created
            if temp_file is not None:
                try:
                    os.unlink(temp_file.name)
                except:
                    pass

    def add_circle_markers_from_xy(
        self,
        data: Union[str, Any],
        x: str = "longitude",
        y: str = "latitude",
        radius: Union[float, str] = 10,
        color: Union[str, List] = "#3388ff",
        stroke_color: str = "#000000",
        stroke_width: float = 1,
        layer_name: str = "Circle Markers",
        crs: str = "EPSG:4326",
        zoom_to_layer: bool = False,
        **kwargs,
    ) -> Optional["QgsVectorLayer"]:
        """Add circle markers from CSV or DataFrame point data.

        Args:
            data: Path to CSV file or pandas DataFrame.
            x: Column name for x-coordinate (longitude). Defaults to "longitude".
            y: Column name for y-coordinate (latitude). Defaults to "latitude".
            radius: Circle radius in pixels (fixed) or column name for data-defined sizing.
            color: Fill color as hex string, RGB tuple, or list of colors.
            stroke_color: Stroke color as hex string or RGB tuple.
            stroke_width: Stroke width in pixels.
            layer_name: Name for the layer. Defaults to "Circle Markers".
            crs: Coordinate reference system. Defaults to "EPSG:4326".
            zoom_to_layer: Whether to zoom to layer extent. Defaults to False.
            **kwargs: Additional keyword arguments.

        Returns:
            The created vector layer, or None if creation failed.

        Example:
            >>> m = Map()
            >>> m.add_circle_markers_from_xy(
            ...     "cities.csv",
            ...     x="lon",
            ...     y="lat",
            ...     radius=15,
            ...     color="#ff0000"
            ... )
        """
        if not HAS_QGIS:
            print("QGIS libraries not available")
            return None

        try:
            from . import common

            # Parse point data
            df, attr_columns = common.parse_point_data(data, x, y)

            # Create memory layer
            layer = QgsVectorLayer(f"Point?crs={crs}", layer_name, "memory")
            provider = layer.dataProvider()

            # Add attribute fields
            fields = QgsFields()
            for col in attr_columns:
                fields.append(QgsField(col, 10))  # QVariant::String = 10

            provider.addAttributes(fields.toList())
            layer.updateFields()

            # Add features
            features = []
            for idx, row in df.iterrows():
                feat = QgsFeature(layer.fields())
                point = QgsPointXY(float(row[x]), float(row[y]))
                feat.setGeometry(QgsGeometry.fromPointXY(point))

                # Set attributes
                for col in attr_columns:
                    feat.setAttribute(col, row[col])

                features.append(feat)

            provider.addFeatures(features)
            layer.updateExtents()

            # Apply circle marker styling
            symbol = QgsMarkerSymbol.createSimple(
                {
                    "name": "circle",
                    "color": (
                        color if isinstance(color, str) else ",".join(map(str, color))
                    ),
                    "outline_color": stroke_color,
                    "outline_width": str(stroke_width),
                    "size": str(radius) if isinstance(radius, (int, float)) else "10",
                }
            )

            # Handle data-defined sizing if radius is a column name
            if isinstance(radius, str) and radius in attr_columns:
                symbol.setDataDefinedProperty(
                    QgsSymbol.PropertySize, QgsProperty.fromField(radius)
                )

            renderer = QgsSingleSymbolRenderer(symbol)
            layer.setRenderer(renderer)

            # Add to project
            self.project.addMapLayer(layer, False)
            root = self.project.layerTreeRoot()
            root.addLayer(layer)

            # Track layer
            self._layers[layer_name] = layer

            # Zoom if requested
            if zoom_to_layer:
                self.zoom_to_layer(layer_name)

            # Refresh canvas
            if self.canvas:
                self.canvas.refresh()

            return layer

        except ImportError as e:
            print(f"Missing dependency: {e}")
            return None
        except Exception as e:
            print(f"Error adding circle markers: {e}")
            return None

    def add_points_from_xy(
        self,
        data: Union[str, Any],
        x: str = "longitude",
        y: str = "latitude",
        layer_name: str = "Points",
        crs: str = "EPSG:4326",
        style: Optional[Dict] = None,
        color_column: Optional[str] = None,
        size_column: Optional[str] = None,
        popup_fields: Optional[List[str]] = None,
        zoom_to_layer: bool = False,
        **kwargs,
    ) -> Optional["QgsVectorLayer"]:
        """Enhanced CSV point loading with data-driven styling and popups.

        Args:
            data: Path to CSV file or pandas DataFrame.
            x: Column name for x-coordinate (longitude). Defaults to "longitude".
            y: Column name for y-coordinate (latitude). Defaults to "latitude".
            layer_name: Name for the layer. Defaults to "Points".
            crs: Coordinate reference system. Defaults to "EPSG:4326".
            style: Optional style dictionary with keys: color, stroke_color, stroke_width, opacity, symbol.
            color_column: Column name for color-based categorization.
            size_column: Column name for size-based scaling.
            popup_fields: List of field names to include in popup. If None, includes all fields.
            zoom_to_layer: Whether to zoom to layer extent. Defaults to False.
            **kwargs: Additional keyword arguments.

        Returns:
            The created vector layer, or None if creation failed.

        Example:
            >>> m = Map()
            >>> m.add_points_from_xy(
            ...     "cities.csv",
            ...     x="lon",
            ...     y="lat",
            ...     color_column="category",
            ...     size_column="population",
            ...     popup_fields=["name", "population"]
            ... )
        """
        if not HAS_QGIS:
            print("QGIS libraries not available")
            return None

        try:
            from . import common

            # Parse point data
            df, attr_columns = common.parse_point_data(data, x, y)

            # Create memory layer
            layer = QgsVectorLayer(f"Point?crs={crs}", layer_name, "memory")
            provider = layer.dataProvider()

            # Add attribute fields with proper types
            fields = QgsFields()
            for col in attr_columns:
                # Infer field type from data
                dtype = df[col].dtype
                if dtype in ["int64", "int32"]:
                    fields.append(QgsField(col, 2))  # QVariant::Int
                elif dtype in ["float64", "float32"]:
                    fields.append(QgsField(col, 6))  # QVariant::Double
                else:
                    fields.append(QgsField(col, 10))  # QVariant::String

            provider.addAttributes(fields.toList())
            layer.updateFields()

            # Add features
            features = []
            for idx, row in df.iterrows():
                feat = QgsFeature(layer.fields())
                point = QgsPointXY(float(row[x]), float(row[y]))
                feat.setGeometry(QgsGeometry.fromPointXY(point))

                # Set attributes
                for col in attr_columns:
                    feat.setAttribute(col, row[col])

                features.append(feat)

            provider.addFeatures(features)
            layer.updateExtents()

            # Apply styling
            if color_column and color_column in attr_columns:
                # Use categorized renderer for color column
                unique_values = df[color_column].unique()
                categories = []
                colors = [
                    "#e41a1c",
                    "#377eb8",
                    "#4daf4a",
                    "#984ea3",
                    "#ff7f00",
                    "#ffff33",
                    "#a65628",
                    "#f781bf",
                ]

                for i, value in enumerate(unique_values):
                    color = colors[i % len(colors)]
                    symbol = QgsSymbol.defaultSymbol(0)  # Point = 0
                    symbol.setColor(self._parse_color(color))
                    category = QgsRendererCategory(value, symbol, str(value))
                    categories.append(category)

                renderer = QgsCategorizedSymbolRenderer(color_column, categories)
                layer.setRenderer(renderer)
            elif style:
                self._apply_vector_style(layer, style)

            # Handle data-defined sizing
            if size_column and size_column in attr_columns:
                symbol = layer.renderer().symbol()
                if symbol:
                    symbol.setDataDefinedProperty(
                        QgsSymbol.PropertySize, QgsProperty.fromField(size_column)
                    )

            # Set popup template
            if popup_fields:
                fields_to_show = [f for f in popup_fields if f in attr_columns]
            else:
                fields_to_show = attr_columns

            popup_html = "<html><body>"
            for field in fields_to_show:
                popup_html += f'<p><b>{field}:</b> [% "{field}" %]</p>'
            popup_html += "</body></html>"
            layer.setMapTipTemplate(popup_html)

            # Add to project
            self.project.addMapLayer(layer, False)
            root = self.project.layerTreeRoot()
            root.addLayer(layer)

            # Track layer
            self._layers[layer_name] = layer

            # Zoom if requested
            if zoom_to_layer:
                self.zoom_to_layer(layer_name)

            # Refresh canvas
            if self.canvas:
                self.canvas.refresh()

            return layer

        except ImportError as e:
            print(f"Missing dependency: {e}")
            return None
        except Exception as e:
            print(f"Error adding points from XY: {e}")
            return None

    def add_heatmap(
        self,
        data: Union[str, Any],
        latitude: str = "latitude",
        longitude: str = "longitude",
        value: Optional[str] = None,
        layer_name: str = "Heatmap",
        radius: int = 20,
        weight_field: Optional[str] = None,
        max_value: Optional[float] = None,
        color_ramp: str = "YlOrRd",
        zoom_to_layer: bool = False,
        **kwargs,
    ) -> Optional["QgsVectorLayer"]:
        """Create a heatmap visualization from point data.

        Args:
            data: Path to CSV file or pandas DataFrame containing point data.
            latitude: Column name for latitude values. Defaults to "latitude".
            longitude: Column name for longitude values. Defaults to "longitude".
            value: Optional column name for weighting values.
            layer_name: Name for the layer. Defaults to "Heatmap".
            radius: Heatmap radius in pixels. Defaults to 20.
            weight_field: Field to use for weighting (overrides value). Defaults to None.
            max_value: Maximum value for scaling. If None, uses data maximum.
            color_ramp: Color ramp name. Defaults to "YlOrRd".
            zoom_to_layer: Whether to zoom to layer extent. Defaults to False.
            **kwargs: Additional keyword arguments.

        Returns:
            The created heatmap layer, or None if creation failed.

        Example:
            >>> m = Map()
            >>> layer = m.add_heatmap(
            ...     "cities.csv",
            ...     latitude="lat",
            ...     longitude="lon",
            ...     value="population",
            ...     radius=30,
            ...     color_ramp="Reds"
            ... )
        """
        if not HAS_QGIS:
            print("QGIS libraries not available")
            return None

        try:
            from . import common

            # Parse point data
            df, attr_columns = common.parse_point_data(data, longitude, latitude)

            # Create memory layer
            layer = QgsVectorLayer(f"Point?crs=EPSG:4326", layer_name, "memory")
            provider = layer.dataProvider()

            # Add attribute fields
            fields = QgsFields()
            for col in attr_columns:
                # Infer field type
                dtype = df[col].dtype
                if dtype in ["int64", "int32", "float64", "float32"]:
                    fields.append(QgsField(col, 6))  # QVariant::Double
                else:
                    fields.append(QgsField(col, 10))  # QVariant::String

            provider.addAttributes(fields.toList())
            layer.updateFields()

            # Add features
            features = []
            for idx, row in df.iterrows():
                feat = QgsFeature(layer.fields())
                point = QgsPointXY(float(row[longitude]), float(row[latitude]))
                feat.setGeometry(QgsGeometry.fromPointXY(point))

                # Set attributes
                for col in attr_columns:
                    feat.setAttribute(col, row[col])

                features.append(feat)

            provider.addFeatures(features)
            layer.updateExtents()

            # Apply heatmap renderer
            heatmap_renderer = QgsHeatmapRenderer()
            heatmap_renderer.setRadius(radius)

            # Set weight field if specified
            if weight_field and weight_field in attr_columns:
                heatmap_renderer.setWeightExpression(f'"{weight_field}"')
            elif value and value in attr_columns:
                heatmap_renderer.setWeightExpression(f'"{value}"')

            # Set maximum value
            if max_value:
                heatmap_renderer.setMaximumValue(max_value)

            # Set color ramp
            try:
                ramp = common.get_color_ramp(color_ramp)
                heatmap_renderer.setColorRamp(ramp)
            except Exception as e:
                print(f"Could not set color ramp: {e}")

            layer.setRenderer(heatmap_renderer)

            # Add to project
            self.project.addMapLayer(layer, False)
            root = self.project.layerTreeRoot()
            root.addLayer(layer)

            # Track layer
            self._layers[layer_name] = layer

            # Zoom if requested
            if zoom_to_layer:
                self.zoom_to_layer(layer_name)

            # Refresh canvas
            if self.canvas:
                self.canvas.refresh()

            return layer

        except ImportError as e:
            print(f"Missing dependency: {e}")
            return None
        except Exception as e:
            print(f"Error adding heatmap: {e}")
            return None

    def add_styled_vector(
        self,
        source: Union[str, Any],
        layer_name: Optional[str] = None,
        column: Optional[str] = None,
        scheme: str = "Quantiles",
        k: int = 5,
        color_ramp: str = "Spectral",
        legend: bool = True,
        legend_title: Optional[str] = None,
        zoom_to_layer: bool = False,
        **kwargs,
    ) -> Optional["QgsVectorLayer"]:
        """Add vector layer with automatic data-driven classification and legend.

        Args:
            source: File path or GeoDataFrame.
            layer_name: Name for the layer. If None, auto-generated.
            column: Column name for classification. If None, uses simple styling.
            scheme: Classification scheme: "Quantiles", "EqualInterval", "NaturalBreaks", "StandardDeviation".
            k: Number of classes. Defaults to 5.
            color_ramp: Color ramp name. Defaults to "Spectral".
            legend: Whether to auto-generate legend. Defaults to True.
            legend_title: Title for legend. If None, uses column name.
            zoom_to_layer: Whether to zoom to layer extent. Defaults to False.
            **kwargs: Additional keyword arguments.

        Returns:
            The created vector layer, or None if creation failed.

        Example:
            >>> m = Map()
            >>> m.add_styled_vector(
            ...     "states.shp",
            ...     column="population",
            ...     scheme="Quantiles",
            ...     k=5,
            ...     color_ramp="YlOrRd",
            ...     legend=True
            ... )
        """
        if not HAS_QGIS:
            print("QGIS libraries not available")
            return None

        try:
            # Load vector layer
            if hasattr(source, "to_file"):  # GeoDataFrame
                layer = self.add_gdf(
                    source, layer_name=layer_name, zoom_to_layer=False, **kwargs
                )
            else:
                layer = self.add_vector(
                    source, layer_name=layer_name, zoom_to_layer=False, **kwargs
                )

            if layer is None or column is None:
                return layer

            # Get classification method
            classification_methods = {
                "Quantiles": QgsClassificationQuantile,
                "EqualInterval": QgsClassificationEqualInterval,
                "NaturalBreaks": QgsClassificationJenks,
                "Jenks": QgsClassificationJenks,
                "StandardDeviation": QgsClassificationStandardDeviation,
            }

            classification_class = classification_methods.get(
                scheme, QgsClassificationQuantile
            )
            classification_method = classification_class()

            # Get color ramp
            from . import common

            ramp = common.get_color_ramp(color_ramp, n_colors=k)

            # Create graduated renderer
            renderer = QgsGraduatedSymbolRenderer()
            renderer.setClassAttribute(column)
            renderer.setSourceColorRamp(ramp)

            # Calculate classes
            renderer.updateClasses(layer, classification_method, k)

            # Apply renderer
            layer.setRenderer(renderer)
            layer.triggerRepaint()

            # Generate legend if requested
            if legend:
                legend_dict = {}
                for i, range_obj in enumerate(renderer.ranges()):
                    label = range_obj.label()
                    color = range_obj.symbol().color()
                    # Convert QColor to hex
                    hex_color = (
                        f"#{color.red():02x}{color.green():02x}{color.blue():02x}"
                    )
                    legend_dict[label] = hex_color

                title = legend_title if legend_title else column
                self.add_legend(title=title, legend_dict=legend_dict)

            # Zoom if requested
            if zoom_to_layer:
                self.zoom_to_layer(layer.name() if layer_name is None else layer_name)

            # Refresh canvas
            if self.canvas:
                self.canvas.refresh()

            return layer

        except Exception as e:
            print(f"Error adding styled vector: {e}")
            return None

    def add_stac_layer(
        self,
        url: Optional[str] = None,
        item: Optional[Dict] = None,
        assets: Optional[Union[str, List[str]]] = None,
        layer_name: Optional[str] = None,
        zoom_to_layer: bool = True,
        **kwargs,
    ) -> Optional["QgsRasterLayer"]:
        """Load STAC item as COG layer.

        Args:
            url: URL to STAC item JSON.
            item: STAC item dictionary (if not providing URL).
            assets: Asset name(s) to load. If None, uses first visual/data asset.
            layer_name: Name for the layer. If None, uses item ID.
            zoom_to_layer: Whether to zoom to layer extent. Defaults to True.
            **kwargs: Additional keyword arguments passed to add_cog.

        Returns:
            The created raster layer, or None if creation failed.

        Example:
            >>> m = Map()
            >>> m.add_stac_layer(
            ...     url="https://example.com/item.json",
            ...     assets="visual"
            ... )
        """
        if not HAS_QGIS:
            print("QGIS libraries not available")
            return None

        try:
            # Fetch STAC item if URL provided
            if url and not item:
                if not HAS_REQUESTS:
                    print("requests library required for fetching STAC items from URL")
                    return None

                response = requests.get(url)
                response.raise_for_status()
                item = response.json()

            if not item:
                print("No STAC item provided (url or item required)")
                return None

            # Extract assets
            item_assets = item.get("assets", {})
            if not item_assets:
                print("No assets found in STAC item")
                return None

            # Select asset(s) to load
            if assets:
                if isinstance(assets, str):
                    asset_names = [assets]
                else:
                    asset_names = assets
            else:
                # Auto-select first visual or data asset
                visual_assets = ["visual", "rendered_preview", "thumbnail", "overview"]
                data_assets = ["data", "cog", "image"]

                asset_names = []
                for name in visual_assets + data_assets:
                    if name in item_assets:
                        asset_names = [name]
                        break

                if not asset_names:
                    # Just use first asset
                    asset_names = [list(item_assets.keys())[0]]

            # Load first asset as COG
            asset_name = asset_names[0]
            if asset_name not in item_assets:
                print(
                    f"Asset '{asset_name}' not found. Available: {list(item_assets.keys())}"
                )
                return None

            asset = item_assets[asset_name]
            cog_url = asset.get("href")

            if not cog_url:
                print(f"No href found for asset '{asset_name}'")
                return None

            # Generate layer name
            if layer_name is None:
                layer_name = f"{item.get('id', 'STAC')}_{asset_name}"

            # Load as COG
            layer = self.add_cog(
                cog_url, layer_name=layer_name, zoom_to_layer=zoom_to_layer, **kwargs
            )

            return layer

        except ImportError as e:
            print(f"Missing dependency: {e}")
            return None
        except Exception as e:
            print(f"Error adding STAC layer: {e}")
            return None

    def __repr__(self) -> str:
        """Return a string representation of the Map.

        Returns:
            A string representation.
        """
        n_layers = len(self.project.mapLayers())
        return f"Map(layers={n_layers}, crs={self.project.crs().authid()})"
