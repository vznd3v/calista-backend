# Architecture du Backend Calista

## Vue d'ensemble

Calista est un backend API stateless qui génère des cartes éducatives de géographie en utilisant un LLM. Le backend reçoit un prompt, appelle un LLM pour produire du JSON structuré (données de pays/région, coordonnées GeoJSON, palettes de couleurs), puis rendoptionnellement ces données en cartes SVG via un moteur de rendu personnalisé appelé **calistaEG**.

```mermaid
flowchart LR
    Client["Client (Frontend)"] -->|"POST /cards/svg"| FastAPI["Serveur FastAPI"]
    FastAPI -->|"1. Prompt"| Agent["Agent LLM"]
    Agent -->|"JSON de Carte structuré"| FastAPI
    FastAPI -->|"2. Rendu"| CalistaEG["Moteur calistaEG"]
    CalistaEG -->|"Carte SVG"| FastAPI
    FastAPI -->|"Carte + SVG"| Client
```

### Stack Technologique

| Composant | Technologie |
|---|---|
| Langage | Python 3.14 |
| Framework Web | FastAPI |
| Serveur ASGI | Uvicorn |
| Agent LLM | pydantic-ai |
| Validation de données | Pydantic |
| Fournisseur LLM | Groq (qwen3.6-27b) |
| Gestionnaire de paquets | uv |

### Structure du Projet

```
src/
├── backend/
│   ├── main.py              # Point d'entrée
│   ├── api/
│   │   └── routes.py        # Endpoints HTTP
│   ├── agent/
│   │   ├── agent.py         # Logique de l'agent LLM
│   │   └── models.py        # Modèles de données Pydantic
│   └── calistaeg/
│       └── engine.py        # Rendu GeoJSON-vers-SVG
└── test/
    └── test.py              # Tests d'intégration
```

---

## Couche API

### Architecture des Endpoints

```mermaid
flowchart TD
    A["GET /"] -->|"Vérification de santé"| R1["{ status: online, version }"]
    B["POST /cards/generate"] -->|"Prompt LLM"| Agent["Agent LLM"]
    Agent -->|"JSON de Carte"| R2["Réponse Carte"]
    C["POST /cards/svg"] -->|"LLM + Rendu"| Pipeline
    Pipeline -->|"Carte + SVG"| R3["Réponse Complète"]
    D["POST /geojson/to-svg"] -->|"Rendu Direct"| Engine["calistaEG"]
    Engine -->|"Chaîne SVG"| R4["Réponse SVG"]
```

### Modèles de Requête/Réponse

```mermaid
classDiagram
    class GenerateRequest {
        +str prompt
    }
    class GenerateSVGRequest {
        +str prompt
    }
    class GeojsonRequest {
        +dict geojson
        +list~str~ colors
        +int width = 800
        +int height = 600
    }
    class Card {
        +str id
        +str title
        +str subject
        +list~Fact~ facts
        +Geography geojson
        +list~str~ palette
    }
    class Fact {
        +str label
        +str value
    }
    class Geography {
        +str type = "FeatureCollection"
        +list~GeoFeature~ features
    }
    class GeoFeature {
        +str type = "Feature"
        +Geometry geometry
        +dict properties
    }
    class Geometry {
        +str type
        +list coordinates
    }

    Card *-- Fact
    Card *-- Geography
    Geography *-- GeoFeature
    GeoFeature *-- Geometry
```

### Gestion des Erreurs

Tous les endpoints suivent un schéma d'erreur cohérent :

- **502 Passerelle incorrecte** — Échec d'appel LLM (traitement du prompt, parsing JSON)
- **422 Entité non traitable** — Entrée GeoJSON invalide pour le rendu
- **200 OK** — Réponses réussies

---

## Service Agent LLM

### Architecture de l'Agent

```mermaid
flowchart TD
    A["generate_card(prompt)"] -->|"Jusqu'à 3 tentatives"| B["build_agent()"]
    B -->|"Prompt Système"| C["Agent pydantic-ai"]
    C -->|"Sortie brute du LLM"| D["parse_card()"]
    D --> E{"Supprimer les barrières markdown"}
    E --> F{"json.loads direct ?"}
    F -->|"Oui"| G["Validation Pydantic"]
    F -->|"Non"| H["_extract_json_object()"]
    H --> I["_loads_lenient()"]
    I --> G
    G -->|"Valide"| K["Objet Card"]
    G -->|"Invalide"| L["Réessayer ou Échouer"]
```

### Sélection du Fournisseur

```mermaid
flowchart TD
    A["Variable d'env LLM_PROVIDER"] --> B{Fournisseur}
    B -->|"groq"| C["API Groq\napi.groq.com/openai/v1"]
    B -->|"ollama"| D["Ollama Local\nlocalhost:11434"]
    B -->|"hf"| E["Hugging Face\nInference Router"]
    B -->|"custom"| F["Endpoint Custom\nLLM_BASE_URL"]
    B -->|"other"| G["API OpenAI\ngpt-4o-mini"]
```

### Pipeline de Parsing JSON

L'agent utilise une stratégie de parsing défensive à 3 couches pour gérer les sorties imparfaites du LLM :

1. **Parsing direct** — `json.loads()` standard sur le texte nettoyé
2. **Suppression des virgules** — Retirer les virgules traînantes avant `}` ou `]`
3. **Récupération des accolades** — Essayer d'ajouter des combinaisons de `]` et `}` pour corriger les structures non fermées

```mermaid
flowchart LR
    A["Texte brut du LLM"] --> B["Supprimer les barrières markdown ```"]
    B --> C["json.loads()"]
    C -->|Succès| D["Card"]
    C -->|Échec| E["Supprimer virgules traînantes"]
    E --> F["json.loads()"]
    F -->|Succès| D
    F -->|Échec| G["_extract_json_object()"]
    G --> H["_loads_lenient() + récupération accolades"]
    H -->|Succès| D
    H -->|Échec| I["ValueError"]
```

---

## Moteur de Rendu calistaEG

### Pipeline de Rendu

```mermaid
flowchart TD
    A["FeatureCollection GeoJSON"] --> B["_iter_positions()"]
    B --> C["_bbox() — Calculer les limites"]
    C --> D["_project() — Projection\nequirectangulaire lon/lat vers x/y"]
    D --> E{Type de Feature}
    E -->|"Polygon/MultiPolygon"| F["_feature_path()\nChemin SVG M...L...Z"]
    E -->|"Point"| G["_point_circle()\nÉlément SVG circle"]
    E -->|"LineString"| H["_line_path()\nChemin SVG ligne"]
    F --> I["Assembler le SVG"]
    G --> I
    H --> I
    I --> J["Rect d'arrière-plan + features stylisées"]
    J --> K["Chaîne SVG"]
```

### Détails de la Projection

```mermaid
flowchart LR
    A["Coords GeoJSON\n[lon, lat]"] --> B["Projection\nEquirectangulaire"]
    B --> C["Boîte de englobante\nmin_lon, min_lat\nmax_lon, max_lat"]
    C --> D["Mise à l'échelle à 85%\ndu viewport"]
    D --> E["Centrer sur\nla boîte englobante"]
    E --> F["Coords pixels\nx, y"]
```

### Règles de Rendu

| Type de Feature | Remplissage | Contour | Style par défaut |
|---|---|---|---|
| Polygon | Couleur palette | Blanc 2px | Forme remplie |
| Point | — | — | Cercle rouge, r=6 |
| LineString | — | Couleur palette 3px | Pas de remplissage |
| Arrière-plan | Dernière couleur palette ou `#eef4fa` — | — | Rect du viewport complet |

---

## Modèles de Données

### Modèle de Domaine Principal

```mermaid
erDiagram
    CARD {
        string id PK
        string title
        string subject
        string[] palette
    }
    FACT {
        string label
        string value
    }
    GEOGRAPHY {
        string type
    }
    GEO_FEATURE {
        string type
        dict properties
    }
    GEOMETRY {
        string type
        list coordinates
    }

    CARD ||--o{ FACT : contient
    CARD ||--o| GEOGRAPHY : possède
    GEOGRAPHY ||--o{ GEO_FEATURE : contient
    GEO_FEATURE ||--o| GEOMETRY : possède
```

---

## Configuration & Environnement

### Variables d'Environnement

```mermaid
flowchart LR
    A[".env"] --> B["LLM_PROVIDER"]
    A --> C["GROQ_MODEL"]
    A --> D["GROQ_API_KEY"]
    A --> E["HOST / PORT"]
    A --> F["OLLAMA_MODEL"]
    A --> G["HF_API_KEY"]
    A --> H["LLM_BASE_URL"]
    A --> I["LLM_API_KEY"]
    A --> J["OPENAI_MODEL"]
```

### Flux de Démarrage

```mermaid
flowchart TD
    A["python -m backend.main"] --> B["load_dotenv()"]
    B --> C["Importer l'app FastAPI"]
    C --> D["Lire HOST / PORT"]
    D --> E["uvicorn.run()"]
    E --> F["Serveur prêt\n127.0.0.1:8000"]
```
