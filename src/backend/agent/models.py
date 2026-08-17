from typing import Any

from pydantic import BaseModel, Field


class Fact(BaseModel):
    label: str = Field(description="Nom du fait / de la donnée, ex: Capitale")
    value: str = Field(description="Valeur précise et correcte, ex: Paris")


class Geometry(BaseModel):
    type: str = Field(description="Type GeoJSON: Point, LineString, Polygon ou MultiPolygon")
    coordinates: list[Any] = Field(
        description="Coordonnées GeoJSON [lon, lat] (nested lists pour les polygones)"
    )


class GeoFeature(BaseModel):
    type: str = "Feature"
    geometry: Geometry | None = Field(default=None, description="Géométrie GeoJSON")
    properties: dict[str, Any] = Field(default_factory=dict)


class Geography(BaseModel):
    type: str = "FeatureCollection"
    features: list[GeoFeature] = Field(default_factory=list)


class Card(BaseModel):
    id: str | None = Field(default=None, description="Identifiant unique de la carte (optionnel)")
    title: str = Field(description="Titre de la carte éducative")
    subject: str = Field(description="Sujet, ex: Géographie - Europe")
    facts: list[Fact] = Field(description="Données éducatives précises et correctes")
    geojson: Geography | None = Field(
        default=None, description="Données géographiques de la carte (FeatureCollection GeoJSON)"
    )
    palette: list[str] = Field(default_factory=list, description="Palette de couleurs de la carte")


class Cards(BaseModel):
    cards: list[Card]