# TODO - Calista Backend


## Refonte calistaEG

- [ ] Abandonner le rendu SVG actuel (trop simpliste, cartes pas belles)
- [ ] Choisir un nouveau moteur de rendu carto :
  - [ ] matplotlib + cartopy (rendu statique haute qualité, projections correctes)
  - [ ] plotly (interactif, exports PNG)
  - [ ] maplibre / folium (tiles OpenStreetMap, rendu web riche)
  - [ ] Autre ?
- [ ] Decider du format de sortie (PNG statique ? HTML interactif ? les deux ?)
- [ ] Decider si on utilise des sources de donnees reelles (Natural Earth, OSM) ou si on garde les coords du LLM

## Ameliorations agent / pipeline

- [ ] Fiabiliser la sortie JSON du LLM (actuellement ~50-70% avec Groq gratuit)
- [ ] Explorer un provider plus fiable / mode non-reasoning
- [ ] Enrichir le system prompt (types de cartes : physique, politique, thematique)
