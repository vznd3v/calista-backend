import itertools
import json
import os
import re

from pydantic import TypeAdapter
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.output import TextOutput
from pydantic_ai.providers.ollama import OllamaProvider

from .models import Card

SYSTEM_PROMPT = """Tu crées UNE carte éducative géographique au format JSON.
Réponds UNIQUEMENT avec l'objet JSON, sur UNE SEULE ligne, sans raisonnement,
sans explication, sans markdown ni fences.
Champs:
- title: str
- subject: str (ex: Géographie - Maroc)
- facts: liste [{label, value}] avec des données PRÉCISES et correctes, en français
- geojson: FeatureCollection GeoJSON — Polygons/MultiPolygons pour les zones,
  Points pour capitales/villes, coordonnées [longitude, latitude]
- palette: liste de couleurs hex (ex: ["#2f6f9f", "#e8f0f8", "#123c55"])
Si le sujet n'est pas géographique, geojson=null."""

_CARD_ADAPTER = TypeAdapter(Card)


def _extract_json_object(text: str) -> str:
    """Extrait le premier objet JSON { ... } équilibré du texte (tolère du
    raisonnement/texte parasite autour du JSON produit par le modèle)."""
    start = text.find("{")
    if start == -1:
        raise ValueError("Aucun objet JSON dans la réponse")
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
    raise ValueError("Objet JSON non fermé")


def _loads_lenient(text: str) -> dict:
    """Charge du JSON en tolérant les erreurs courantes des LLM :
    raisonnement parasite, virgules terminales et fermetures manquantes en fin.
    """
    cleaned = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    closers = ["".join(combo) for n in range(1, 5) for combo in itertools.product("]}", repeat=n)]
    for suffix in closers:
        try:
            return json.loads(cleaned + suffix)
        except json.JSONDecodeError:
            pass
    raise ValueError("JSON du LLM illisible après réparation")


def parse_card(text: str) -> Card:
    """Parse la réponse du LLM en Card (tolère fences, raisonnement et JSON imparfait)."""
    content = text.strip()
    if content.startswith("```"):
        content = re.sub(r"^```[a-zA-Z]*\s*", "", content)
        content = re.sub(r"```$", "", content).strip()
    try:
        payload = _loads_lenient(content)
    except ValueError:
        payload = _loads_lenient(_extract_json_object(content))
    return _CARD_ADAPTER.validate_python(payload)


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _model() -> OpenAIChatModel:
    """Construit le modèle selon la variable d'env LLM_PROVIDER.

    openai  (défaut) : OpenAI officiel, clé OPENAI_API_KEY
    groq             : groq.com (gratuit), clé GROQ_API_KEY
    hf               : Hugging Face Inference (gratuit), clé HF_API_KEY
    ollama           : local gratuit, pas de clé (OLLAMA_BASE_URL)
    custom           : tout endpoint OpenAI-compatible (LLM_BASE_URL + LLM_API_KEY)
    """
    provider = _env("LLM_PROVIDER", "openai").lower()

    if provider == "ollama":
        base_url = _env("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        return OpenAIChatModel(
            _env("OLLAMA_MODEL", "llama3.2"),
            provider=OllamaProvider(base_url=base_url),
        )

    if provider == "groq":
        api_key = _env("GROQ_API_KEY")
        return OpenAIChatModel(
            _env("GROQ_MODEL", "qwen/qwen3.6-27b"),
            provider=OllamaProvider(base_url="https://api.groq.com/openai/v1", api_key=api_key),
        )

    if provider == "hf":
        api_key = _env("HF_API_KEY", _env("HF_TOKEN"))
        return OpenAIChatModel(
            _env("HF_MODEL", "meta-llama/Llama-3.3-70B-Instruct"),
            provider=OllamaProvider(base_url="https://router.huggingface.co/v1", api_key=api_key),
        )

    if provider == "custom":
        base_url = _env("LLM_BASE_URL")
        return OpenAIChatModel(
            _env("LLM_MODEL"),
            provider=OllamaProvider(base_url=base_url, api_key=_env("LLM_API_KEY") or None),
        )

    return OpenAIChatModel(_env("OPENAI_MODEL", "gpt-4o-mini"))


def build_agent() -> Agent[Card]:
    return Agent(
        model=_model(),
        output_type=TextOutput(output_function=parse_card),
        system_prompt=SYSTEM_PROMPT,
        retries=0,
        model_settings={"max_tokens": 6000},
    )


async def generate_card(prompt: str) -> Card:
    """Envoie le prompt au LLM et retourne la carte éducative structurée.
    Chaque tentative est un appel indépendant (pas de feedback d'erreur au modèle)
    pour éviter que les modèles reasoning ne dérivent vers du raisonnement en texte."""
    last_error = None
    for _ in range(3):
        try:
            agent = build_agent()
            result = await agent.run(prompt)
            return result.output
        except Exception as exc:
            last_error = exc
    raise last_error