from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .. import __version__
from ..agent.agent import generate_card
from ..calistaeg.engine import geojson_to_svg


class GenerateRequest(BaseModel):
    prompt: str = Field(description="Sujet des cartes éducatives, ex: les pays du Maghreb")


class GenerateSVGRequest(BaseModel):
    prompt: str


class GeojsonRequest(BaseModel):
    geojson: dict
    colors: list[str] = Field(default_factory=list)
    width: int = 800
    height: int = 600


app = FastAPI(title="Calista Backend", version=__version__)


@app.get("/")
def default() -> dict:
    return {"status": "online", "version": __version__}


@app.post("/cards/generate")
async def generate_cards_endpoint(req: GenerateRequest) -> dict:
    """Envoie le prompt au LLM et renvoie le JSON de la carte éducative."""
    try:
        card = await generate_card(req.prompt)
    except Exception as exc:  # pas d'API key, erreur réseau, etc.
        raise HTTPException(status_code=502, detail=f"Erreur LLM: {exc}") from exc
    return {"cards": [card.model_dump()]}


@app.post("/cards/svg")
async def generate_svg_endpoint(req: GenerateSVGRequest) -> dict:
    """Génère la carte puis rend le SVG via calistaEG."""
    try:
        card = await generate_card(req.prompt)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur LLM: {exc}") from exc

    if not card.geojson:
        raise HTTPException(status_code=422, detail="La carte n'a pas de données géographiques")

    svg = geojson_to_svg(card.geojson.model_dump(), colors=card.palette)
    return {"cards": [card.model_dump()], "svg": svg}


@app.post("/geojson/to-svg")
def geojson_to_svg_endpoint(req: GeojsonRequest) -> dict:
    """Convertit directement un GeoJSON en SVG (test du moteur calistaEG)."""
    try:
        svg = geojson_to_svg(req.geojson, width=req.width, height=req.height, colors=req.colors)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"GeoJSON invalide: {exc}") from exc
    return {"svg": svg}