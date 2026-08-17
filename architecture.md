# Calista Backend Architecture

## Overview

Calista is a stateless API backend that generates educational geography cards using an LLM. The backend receives a prompt, calls an LLM to produce structured JSON (country/region data, GeoJSON coordinates, color palettes), then optionally renders that data into SVG maps via a custom rendering engine called **calistaEG**.

```mermaid
flowchart LR
    Client["Client (Frontend)"] -->|"POST /cards/svg"| FastAPI["FastAPI Server"]
    FastAPI -->|"1. Prompt"| Agent["LLM Agent"]
    Agent -->|"Structured Card JSON"| FastAPI
    FastAPI -->|"2. Render"| CalistaEG["calistaEG Engine"]
    CalistaEG -->|"SVG Map"| FastAPI
    FastAPI -->|"Card + SVG"| Client
```

### Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.14 |
| Web Framework | FastAPI |
| ASGI Server | Uvicorn |
| LLM Agent | pydantic-ai |
| Data Validation | Pydantic |
| LLM Provider | Groq (qwen3.6-27b) |
| Package Manager | uv |

### Project Structure

```
src/
├── backend/
│   ├── main.py              # Entry point
│   ├── api/
│   │   └── routes.py        # HTTP endpoints
│   ├── agent/
│   │   ├── agent.py         # LLM agent logic
│   │   └── models.py        # Pydantic data models
│   └── calistaeg/
│       └── engine.py        # GeoJSON-to-SVG renderer
└── test/
    └── test.py              # Integration tests
```

---

## API Layer

### Endpoint Architecture

```mermaid
flowchart TD
    A["GET /"] -->|"Health Check"| R1["{ status: online, version }"]
    B["POST /cards/generate"] -->|"LLM Prompt"| Agent["LLM Agent"]
    Agent -->|"Card JSON"| R2["Card Response"]
    C["POST /cards/svg"] -->|"LLM + Render"| Pipeline
    Pipeline -->|"Card + SVG"| R3["Full Response"]
    D["POST /geojson/to-svg"] -->|"Direct Render"| Engine["calistaEG"]
    Engine -->|"SVG String"| R4["SVG Response"]
```

### Request/Response Models

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

### Error Handling

All endpoints follow a consistent error pattern:

- **502 Bad Gateway** — LLM call failures (prompt processing, JSON parsing)
- **422 Unprocessable Entity** — Invalid GeoJSON input for rendering
- **200 OK** — Successful responses

---

## LLM Agent Service

### Agent Architecture

```mermaid
flowchart TD
    A["generate_card(prompt)"] -->|"Up to 3 retries"| B["build_agent()"]
    B -->|"System Prompt"| C["pydantic-ai Agent"]
    C -->|"Raw LLM Output"| D["parse_card()"]
    D --> E{"Strip markdown fences"}
    E --> F{"json.loads direct?"}
    F -->|"Yes"| G["Pydantic Validation"]
    F -->|"No"| H["_extract_json_object()"]
    H --> I["_loads_lenient()"]
    I --> J["Pydantic Validation"]
    G -->|"Valid"| K["Card Object"]
    G -->|"Invalid"| L["Retry or Fail"]
```

### Provider Selection

```mermaid
flowchart TD
    A["LLM_PROVIDER env var"] --> B{Provider}
    B -->|"groq"| C["Groq API\napi.groq.com/openai/v1"]
    B -->|"ollama"| D["Local Ollama\nlocalhost:11434"]
    B -->|"hf"| E["Hugging Face\nInference Router"]
    B -->|"custom"| F["Custom Endpoint\nLLM_BASE_URL"]
    B -->|"other"| G["OpenAI API\ngpt-4o-mini"]
```

### JSON Parsing Pipeline

The agent uses a defensive 3-layer parsing strategy to handle imperfect LLM output:

1. **Direct parse** — Standard `json.loads()` on cleaned text
2. **Comma stripping** — Remove trailing commas before `}` or `]`
3. **Brace recovery** — Try appending combinations of `]` and `}` to fix unclosed structures

```mermaid
flowchart LR
    A["Raw LLM text"] --> B["Strip markdown ``` fences"]
    B --> C["json.loads()"]
    C -->|Success| D["Card"]
    C -->|Fail| E["Strip trailing commas"]
    E --> F["json.loads()"]
    F -->|Success| D
    F -->|Fail| G["_extract_json_object()"]
    G --> H["_loads_lenient() + brace recovery"]
    H -->|Success| D
    H -->|Fail| I["ValueError"]
```

---

## calistaEG Rendering Engine

### Rendering Pipeline

```mermaid
flowchart TD
    A["GeoJSON FeatureCollection"] --> B["_iter_positions()"]
    B --> C["_bbox() — Compute bounds"]
    C --> D["_project() — Equirectangular\nlon/lat to x/y"]
    D --> E{Feature Type}
    E -->|"Polygon/MultiPolygon"| F["_feature_path()\nSVG path M...L...Z"]
    E -->|"Point"| G["_point_circle()\nSVG circle element"]
    E -->|"LineString"| H["_line_path()\nSVG line path"]
    F --> I["Assemble SVG"]
    G --> I
    H --> I
    I --> J["Background rect + styled features"]
    J --> K["SVG String"]
```

### Projection Details

```mermaid
flowchart LR
    A["GeoJSON coords\n[lon, lat]"] --> B["Equirectangular\nProjection"]
    B --> C["Bounding Box\nmin_lon, min_lat\nmax_lon, max_lat"]
    C --> D["Scale to 85%\nof viewport"]
    D --> E["Center on\nbounding box"]
    E --> F["Pixel coords\nx, y"]
```

### Rendering Rules

| Feature Type | Fill | Stroke | Default Style |
|---|---|---|---|
| Polygon | Palette color | White 2px | Filled shape |
| Point | — | — | Red circle, r=6 |
| LineString | — | Palette color 3px | No fill |
| Background | Last palette color or `#eef4fa` | — | Full viewport rect |

---

## Data Models

### Core Domain Model

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

    CARD ||--o{ FACT : contains
    CARD ||--o| GEOGRAPHY : has
    GEOGRAPHY ||--o{ GEO_FEATURE : contains
    GEO_FEATURE ||--o| GEOMETRY : has
```

---

## Configuration & Environment

### Environment Variables

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

### Startup Flow

```mermaid
flowchart TD
    A["python -m backend.main"] --> B["load_dotenv()"]
    B --> C["Import FastAPI app"]
    C --> D["Read HOST / PORT"]
    D --> E["uvicorn.run()"]
    E --> F["Server ready\n127.0.0.1:8000"]
```
