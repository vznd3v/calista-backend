<p align="center">
  <img src="https://i.postimg.cc/QtKGVHhJ/2.png" alt="Calista Banner" width="100%">
</p>

<h1 align="center">🌍 Calista Backend</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.14">
  <img src="https://img.shields.io/badge/FastAPI-0.141-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/pydantic--ai-2.31-E535AB?style=for-the-badge&logo=pydantic&logoColor=white" alt="pydantic-ai">
  <img src="https://img.shields.io/badge/Groq-Qwen3.6--27B-FF6B00?style=for-the-badge&logoColor=white" alt="Groq">
  <img src="https://img.shields.io/badge/uv-Package%20Manager-DE5FE9?style=for-the-badge&logo=uv&logoColor=white" alt="uv">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Prototype-orange?style=for-the-badge" alt="Prototype">
  <img src="https://img.shields.io/github/license/vzn/calista?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/Version-0.1.0-blue?style=for-the-badge" alt="v0.1.0">
</p>

<p align="center">
  <em>API qui genere des cartes educatives geographiques via un LLM 🧠,<br>avec un moteur de rendu cartographique (calistaEG) 🗺️</em>
</p>

---

## ⚡ Stack

| Composant | Role |
|---|---|
| 🐍 **Python 3.14** | Langage |
| ⚡ **FastAPI + uvicorn** | API HTTP asynchrone |
| 🤖 **pydantic-ai** | Agent LLM + validation schema |
| 🔮 **Groq** | Provider LLM gratuit (`qwen/qwen3.6-27b`) |
| 🗺️ **calistaEG** | Moteur GeoJSON → SVG |
| 📦 **uv** | Gestionnaire de paquets |

## 🔧 Installation

```bash
uv sync
cp .env.example .env   # ou editer .env directement
```

### 🔐 Variables d'environnement (`.env`)

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

## 🚀 Lancement

```bash
backend                    # via l'entry point du pyproject.toml
# ou
uvicorn backend.main:app --reload
```

> 📡 Serveur sur http://127.0.0.1:8000 — 📖 docs interactives sur /docs

## 🛣️ Endpoints

| Methode | Route | Description |
|---|---|---|
| `GET` | `/` | ✅ Statut + version |
| `POST` | `/cards/generate` | 🧠 Genere une carte educative (JSON) |
| `POST` | `/cards/svg` | 🗺️ Carte + rendu SVG (agent + calistaEG) |
| `POST` | `/geojson/to-svg` | 🔄 Convertit un GeoJSON en SVG |

### 💡 Exemples

```bash
# 🧠 Generer une carte (JSON)
curl -s -X POST localhost:8000/cards/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"le Maroc"}' | python3 -m json.tool

# 🗺️ Carte + SVG
curl -s -X POST localhost:8000/cards/svg \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"la France"}' -o france.json

# 🔄 GeoJSON → SVG (sans LLM)
curl -s -X POST localhost:8000/geojson/to-svg \
  -H 'Content-Type: application/json' \
  -d '{"geojson":{"type":"FeatureCollection","features":[{"type":"Feature","geometry":{"type":"Polygon","coordinates":[[[2.3,48.8],[6.0,49.5],[5.0,46.5],[2.3,48.8]]]}}]}}' \
  -o test.svg
```

## 🧪 Tests

```bash
# 1. Demarrer le serveur dans un terminal
backend

# 2. Lancer les tests dans un autre terminal
python src/test/test.py "la France"
```

> Le script teste les 4 endpoints et sauvegarde le SVG dans `output_test.svg` 🎯

## 📁 Structure

```
src/backend/
  main.py              🚀 Entry point, charge .env, lance uvicorn
  agent/
    models.py          📐 Modeles pydantic (Card, GeoFeature, Fact...)
    agent.py           🤖 Agent LLM (pydantic-ai, mode texte, parse JSON tolerant)
  calistaeg/
    engine.py          🗺️ Moteur GeoJSON → SVG
  api/
    routes.py          🛣️ Routes FastAPI
src/test/
  test.py              🧪 Script de test
```

## ⚠️ Limitations (prototype)

- 🔶 Le rendu carto est un SVG vectoriel simplifie (equirectangular) — en cours de refonte.
- 🔶 La fiabilite JSON du LLM depend du provider (tier gratuit Groq intermittent).
- 🔶 Les donnees geographiques dependent de la qualite du modele LLM (pas de source OSM/Natural Earth).

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/vzn">vzn.d3v</a>
</p>
