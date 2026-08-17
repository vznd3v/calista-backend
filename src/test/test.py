"""Script de test du backend Calista (agent + moteur calistaEG)."""

import asyncio
import sys
from pathlib import Path

import httpx

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = httpx.Timeout(180.0)
RETRIES = 3


def green(t): return f"\033[32m{t}\033[0m"
def red(t):   return f"\033[31m{t}\033[0m"


async def call_llm(client, path, payload):
    """Appel LLM avec retries indépendants (le tier gratuit Groq est intermittent)."""
    last = None
    for attempt in range(1, RETRIES + 1):
        try:
            r = await client.post(path, json=payload)
            if r.status_code == 200:
                return r
            last = f"HTTP {r.status_code}"
        except httpx.HTTPError as e:
            last = str(e)
        if attempt < RETRIES:
            await asyncio.sleep(2)
    raise RuntimeError(f"{path}: {last} après {RETRIES} tentatives")


async def main():
    prompt = sys.argv[1] if len(sys.argv) > 1 else "le Maroc"
    results = []
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
        # 1. Santé
        r = await client.get("/")
        ok = r.status_code == 200
        results.append(("GET /", ok, r.json()))
        print(f"[{'OK' if ok else 'KO'}] GET /  → {r.json()}")

        # 2. Moteur seul (sans LLM, fiable)
        geojson = {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {"name": "France"},
             "geometry": {"type": "Polygon",
                          "coordinates": [[[2.3, 48.8], [6.0, 49.5], [5.0, 46.5], [2.3, 48.8]]]}},
            {"type": "Feature", "properties": {"name": "Paris"},
             "geometry": {"type": "Point", "coordinates": [2.35, 48.85]}},
        ]}
        r = await client.post("/geojson/to-svg", json={"geojson": geojson})
        svg_len = len(r.json()["svg"])
        ok = r.status_code == 200 and r.json()["svg"].startswith("<svg")
        results.append(("POST /geojson/to-svg", ok, f"{svg_len} chars"))
        print(f"[{'OK' if ok else 'KO'}] POST /geojson/to-svg → SVG {svg_len} chars")

        # 3. Agent seul (LLM)
        r = await call_llm(client, "/cards/generate", {"prompt": prompt})
        card = r.json()["cards"][0]
        ok = bool(card.get("facts"))
        results.append(("POST /cards/generate", ok, card["title"]))
        print(f"[{'OK' if ok else 'KO'}] POST /cards/generate → {card['title']} ({len(card['facts'])} faits)")

        # 4. Pipeline complet (agent → calistaEG)
        r = await call_llm(client, "/cards/svg", {"prompt": prompt})
        svg = r.json()["svg"]
        ok = svg.startswith("<svg") and svg.endswith("</svg>")
        out = Path("output_test.svg")
        out.write_text(svg)
        results.append(("POST /cards/svg", ok, f"SVG {len(svg)} chars → {out}"))
        print(f"[{'OK' if ok else 'KO'}] POST /cards/svg → SVG {len(svg)} chars sauvegardé dans {out}")

    # Bilan
    print("\n=== BILAN ===")
    failures = [name for name, ok, _ in results if not ok]
    for name, ok, msg in results:
        print(f"  {green('PASS') if ok else red('FAIL')}  {name}: {msg}")
    if failures:
        print(red(f"\n{len(failures)} test(s) en échec: {', '.join(failures)}"))
        sys.exit(1)
    print(green("\nTous les tests sont passés."))


if __name__ == "__main__":
    asyncio.run(main())