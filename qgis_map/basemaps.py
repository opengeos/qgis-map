"""Basemap definitions for common tile services."""

# XYZ tile URL templates for common basemaps
BASEMAPS = {
    # OpenStreetMap
    "OpenStreetMap": {
        "url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attribution": "© OpenStreetMap contributors",
        "name": "OpenStreetMap",
    },
    "OSM": {
        "url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attribution": "© OpenStreetMap contributors",
        "name": "OpenStreetMap",
    },
    # CartoDB
    "CartoDB.Positron": {
        "url": "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
        "attribution": "© CartoDB © OpenStreetMap contributors",
        "name": "CartoDB Positron",
    },
    "CartoDB.DarkMatter": {
        "url": "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
        "attribution": "© CartoDB © OpenStreetMap contributors",
        "name": "CartoDB Dark Matter",
    },
    "CartoDB.Voyager": {
        "url": "https://a.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png",
        "attribution": "© CartoDB © OpenStreetMap contributors",
        "name": "CartoDB Voyager",
    },
    # Stamen (now Stadia)
    "Stadia.StamenToner": {
        "url": "https://tiles.stadiamaps.com/tiles/stamen_toner/{z}/{x}/{y}.png",
        "attribution": "© Stadia Maps © Stamen Design © OpenStreetMap contributors",
        "name": "Stamen Toner",
    },
    "Stadia.StamenTerrain": {
        "url": "https://tiles.stadiamaps.com/tiles/stamen_terrain/{z}/{x}/{y}.png",
        "attribution": "© Stadia Maps © Stamen Design © OpenStreetMap contributors",
        "name": "Stamen Terrain",
    },
    "Stadia.StamenWatercolor": {
        "url": "https://tiles.stadiamaps.com/tiles/stamen_watercolor/{z}/{x}/{y}.jpg",
        "attribution": "© Stadia Maps © Stamen Design © OpenStreetMap contributors",
        "name": "Stamen Watercolor",
    },
    # ESRI
    "Esri.WorldStreetMap": {
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
        "attribution": "Tiles © Esri",
        "name": "Esri World Street Map",
    },
    "Esri.WorldImagery": {
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "attribution": "Tiles © Esri",
        "name": "Esri World Imagery",
    },
    "Esri.WorldTopoMap": {
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
        "attribution": "Tiles © Esri",
        "name": "Esri World Topo Map",
    },
    "Esri.WorldTerrain": {
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/{z}/{y}/{x}",
        "attribution": "Tiles © Esri",
        "name": "Esri World Terrain",
    },
    "Esri.WorldShadedRelief": {
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Shaded_Relief/MapServer/tile/{z}/{y}/{x}",
        "attribution": "Tiles © Esri",
        "name": "Esri World Shaded Relief",
    },
    "Esri.WorldGrayCanvas": {
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        "attribution": "Tiles © Esri",
        "name": "Esri World Gray Canvas",
    },
    "Esri.NatGeoWorldMap": {
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}",
        "attribution": "Tiles © Esri",
        "name": "Esri NatGeo World Map",
    },
    "Esri.OceanBasemap": {
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}",
        "attribution": "Tiles © Esri",
        "name": "Esri Ocean Basemap",
    },
    # Google Maps
    "ROADMAP": {
        "url": "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
        "attribution": "© Google",
        "name": "Google Maps",
    },
    "SATELLITE": {
        "url": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        "attribution": "© Google",
        "name": "Google Satellite",
    },
    "TERRAIN": {
        "url": "https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}",
        "attribution": "© Google",
        "name": "Google Terrain",
    },
    "HYBRID": {
        "url": "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        "attribution": "© Google",
        "name": "Google Hybrid",
    },
    # OpenTopoMap
    "OpenTopoMap": {
        "url": "https://a.tile.opentopomap.org/{z}/{x}/{y}.png",
        "attribution": "© OpenTopoMap (CC-BY-SA)",
        "name": "OpenTopoMap",
    },
}


def get_basemap_url(name: str) -> str:
    """Get the URL template for a basemap by name.

    Args:
        name: The name of the basemap (case-insensitive).

    Returns:
        The URL template for the basemap.

    Raises:
        ValueError: If the basemap name is not found.
    """
    # Try exact match first
    if name in BASEMAPS:
        return BASEMAPS[name]["url"]

    # Try case-insensitive match
    name_upper = name.upper()
    for key in BASEMAPS:
        if key.upper() == name_upper:
            return BASEMAPS[key]["url"]

    raise ValueError(
        f"Basemap '{name}' not found. Available basemaps: {list(BASEMAPS.keys())}"
    )


def get_basemap_names() -> list:
    """Get a list of available basemap names.

    Returns:
        A list of available basemap names.
    """
    return list(BASEMAPS.keys())


def get_xyz_uri(url: str, zmin: int = 0, zmax: int = 22) -> str:
    """Convert an XYZ tile URL to a QGIS-compatible URI.

    Args:
        url: The XYZ tile URL template with {x}, {y}, {z} placeholders.
        zmin: Minimum zoom level. Defaults to 0.
        zmax: Maximum zoom level. Defaults to 22.

    Returns:
        A QGIS-compatible URI string for XYZ tiles.
    """
    return f"type=xyz&url={url}&zmin={zmin}&zmax={zmax}"
