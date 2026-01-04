"""Main module for qgis-map.

This module provides a high-level Map class for working with QGIS,
similar to the leafmap Map class but designed for PyQGIS.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, Union
import os

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

    def __repr__(self) -> str:
        """Return a string representation of the Map.

        Returns:
            A string representation.
        """
        n_layers = len(self.project.mapLayers())
        return f"Map(layers={n_layers}, crs={self.project.crs().authid()})"
