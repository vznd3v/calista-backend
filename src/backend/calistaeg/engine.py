"""calistaEG : moteur de carte qui transforme des données GeoJSON en code SVG valide.

Prototype minimal : projection équirectangulaire simple, pas de projection complexe.
"""

from __future__ import annotations

from typing import Any, Iterable


def _iter_positions(coordinates: Any) -> Iterable[tuple[float, float]]:
    """Parcourt une structure de coordonnées GeoJSON et renvoie chaque [lon, lat]."""
    if coordinates and isinstance(coordinates[0], (int, float)):
        yield float(coordinates[0]), float(coordinates[1])
        return
    for child in coordinates:
        yield from _iter_positions(child)


def _bbox(coordinates: Any) -> tuple[float, float, float, float]:
    positions = list(_iter_positions(coordinates))
    if not positions:
        return 0.0, 0.0, 1.0, 1.0
    lons = [p[0] for p in positions]
    lats = [p[1] for p in positions]
    return min(lons), min(lats), max(lons), max(lats)


def _project(
    lon: float, lat: float, bounds: tuple[float, float, float, float], width: int, height: int
) -> tuple[float, float]:
    min_lon, min_lat, max_lon, max_lat = bounds
    lon_span = max(max_lon - min_lon, 1e-9)
    lat_span = max(max_lat - min_lat, 1e-9)
    scale = min(width / lon_span, height / lat_span) * 0.85
    cx, cy = (min_lon + max_lon) / 2, (min_lat + max_lat) / 2
    x = width / 2 + (lon - cx) * scale
    y = height / 2 - (lat - cy) * scale
    return round(x, 2), round(y, 2)


def _ring_path(ring: list, bounds, width, height) -> str:
    """Trace un anneau GeoJSON en path SVG, tolère les formats de coords variables."""
    pts = list(_iter_positions(ring))
    if not pts:
        return ""
    projected = [_project(lon, lat, bounds, width, height) for lon, lat in pts]
    return "M " + " L ".join(f"{x} {y}" for x, y in projected) + " Z"


def _to_rings(coords: Any, ftype: str) -> list:
    """Extrait les anneaux depuis les coordonnées GeoJSON en tolérant les niveaux d'imbrication."""
    if ftype == "MultiPolygon":
        rings = []
        for poly in coords:
            if poly and isinstance(poly[0], list) and poly[0] and isinstance(poly[0][0], list):
                rings.extend(poly)
            elif poly:
                rings.append(poly)
        return rings
    if ftype == "Polygon":
        if coords and isinstance(coords[0], list) and coords[0] and isinstance(coords[0][0], list):
            return coords
        return [coords]
    return []


def _feature_path(geom: dict, bounds, width, height) -> str:
    coords = geom["coordinates"]
    ftype = geom.get("type", "Polygon")
    rings = _to_rings(coords, ftype)
    parts = [_ring_path(r, bounds, width, height) for r in rings]
    return " ".join(p for p in parts if p)


def _point_circle(geom: dict, props: dict, bounds, width, height) -> str:
    coords = geom["coordinates"]
    x, y = _project(coords[0], coords[1], bounds, width, height)
    return f'<circle cx="{x}" cy="{y}" r="6" fill="{props.get("fill", "#ff5c33")}"/>'


def _line_path(geom: dict, bounds, width, height) -> str:
    coords = geom["coordinates"]
    pts = [_project(p[0], p[1], bounds, width, height) for p in coords]
    return "M " + " L ".join(f"{x} {y}" for x, y in pts)


def _geometry(feature: dict) -> dict:
    return feature.get("geometry") or feature


def geojson_to_svg(
    geojson: dict[str, Any],
    width: int = 800,
    height: int = 600,
    colors: list[str] | None = None,
) -> str:
    """Convertit une FeatureCollection GeoJSON en chaîne SVG valide."""
    features = geojson.get("features", [])
    if not features:
        return "<svg xmlns='http://www.w3.org/2000/svg'></svg>"

    palette = colors or ["#2f6f9f", "#3f8fbf", "#4fafd8"]
    bounds = _bbox(
        [_geometry(f)["coordinates"] for f in features if _geometry(f).get("coordinates")]
    )

    body: list[str] = [
        f'<rect width="{width}" height="{height}" fill="{palette[-1] if len(palette) > 1 else "#eef4fa"}"/>'
    ]

    for i, feature in enumerate(features):
        geom = _geometry(feature)
        ftype = geom.get("type", "Polygon")
        props = feature.get("properties", {})
        if ftype in ("Polygon", "MultiPolygon"):
            path = _feature_path(geom, bounds, width, height)
            if path:
                fill = props.get("fill", palette[i % (len(palette) - 1 if len(palette) > 1 else 1)])
                body.append(f'<path d="{path}" fill="{fill}" stroke="#ffffff" stroke-width="2"/>')
        elif ftype == "Point":
            body.append(_point_circle(geom, props, bounds, width, height))
        elif ftype == "LineString":
            body.append(f'<path d="{_line_path(geom, bounds, width, height)}" fill="none" '
                        f'stroke="{palette[i % len(palette)]}" stroke-width="3"/>')

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">'
        + "".join(body)
        + "</svg>"
    )