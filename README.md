# Calista Backend

API FastAPI qui genere des cartes educatives geographiques via un LLM, avec un moteur de rendu carto (calistaEG).

## Stack

- Python 3.14 / uv
- FastAPI + uvicorn
- pydantic-ai (agent LLM)
- Groq (provider gratuit : `qwen/qwen3.6-27b`)

## Installation

```bash
uv sync
cp .env.example .env   # ou editer .env directement
```

### Variables d'environnement (`.env`)

| Variable | Description | Defaut |
|---|---|---|
| `LLM_PROVIDER` | `groq`, `openai`, `hf`, `ollama` ou `custom` | `groq` |
| `GROQ_MODEL` | Modele Groq | `qwen/qwen3.6-27b` |
| `GROQ_API_KEY` | Cle API Groq | *(requis)* |
| `OLLAMA_MODEL` | Modele Ollama local | `llama3.2:1b` |
| `LLM_BASE_URL` | URL custom (provider=custom) | — |
| `LLM_API_KEY` | Cle API custom | — |
| `HOST` | Adresse du serveur | `127.0.0.1` |
| `PORT` | Port du serveur | `8000` |

## Lancement

```bash
backend                    # via l'entry point du pyproject.toml
# ou
uvicorn backend.main:app --reload
```

Serveur sur http://127.0.0.1:8000 — docs interactives sur /docs.

## Endpoints

| Methode | Route | Description |
|---|---|---|
| `GET` | `/` | Statut + version |
| `POST` | `/cards/generate` | Genere une carte educative (JSON uniquement) |
| `POST` | `/cards/svg` | Genere une carte + rendu SVG (agent + calistaEG) |
| `POST` | `/geojson/to-svg` | Convertit un GeoJSON en SVG (test du moteur) |

### Exemples

```bash
# Generer une carte (JSON)
curl -s -X POST localhost:8000/cards/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"le Maroc"}' | python3 -m json.tool

# Carte + SVG
curl -s -X POST localhost:8000/cards/svg \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"la France"}' -o france.json

# GeoJSON → SVG (sans LLM)
curl -s -X POST localhost:8000/geojson/to-svg \
  -H 'Content-Type: application/json' \
  -d '{"geojson":{"type":"FeatureCollection","features":[{"type":"Feature","geometry":{"type":"Polygon","coordinates":[[[2.3,48.8],[6.0,49.5],[5.0,46.5],[2.3,48.8]]]}}]}}' \
  -o test.svg
```

## Tests

```bash
# Demarrer le serveur dans un terminal
backend

# Lancer les tests dans un autre terminal
python src/test/test.py "la France"
```

Le script teste les 4 endpoints et sauvegarde le SVG dans `output_test.svg`.

## Structure

```
src/backend/
  main.py              # entry point, charge .env, lance uvicorn
  agent/
    models.py          # modeles pydantic (Card, GeoFeature, Fact...)
    agent.py           # agent LLM (pydantic-ai, mode texte, parse JSON tolérant)
  calistaeg/
    engine.py          # moteur GeoJSON → SVG
  api/
    routes.py          # routes FastAPI
src/test/
  test.py              # script de test
```

## Limitations (prototype)

- Le rendu carto est un SVG vectoriel simplifie (equirectangular) — en cours de refonte.
- La fiabilite JSON du LLM depend du provider (tier gratuit Groq intermittent).
- Les donnees geographiques dependent de la qualite du modele LLM (pas de source OSM/Natural Earth).
