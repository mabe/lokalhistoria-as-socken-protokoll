# Ås Socken Protokoll – GitHub Pages

**Webbplats:** https://mabe.github.io/lokalhistoria-as-socken-protokoll

En Jekyll-baserad GitHub Pages-webbplats som listar och presenterar **protokoll från Ås Socken**, hämtade från [Lokalhistoria.nu](http://www.lokalhistoria.nu/) via SLHD:s API.

## Vad är det här?

Webbplatsen innehåller:
- En **indexsida** med sökbar förteckning över ~520 protokoll
- En **individuell sida per protokoll** med titel, år, källa och länk till originalet

## Teknisk beskrivning

| Del | Teknik |
|-----|--------|
| Sidgenerator | [Jekyll](https://jekyllrb.com/) (GitHub Pages) |
| Sidegenereringsskript | Python 3 (`scripts/generate_pages.py`) |
| Datakälla | SLHD JSONP-API (`slhd.evryonehalmstad.se`) |
| CI/CD | GitHub Actions |

## Struktur

```
.
├── _layouts/           # Jekyll-layouter
│   ├── default.html    # Grundlayout
│   └── protocol.html   # Layout för protokollsidor
├── _protokoll/         # Auto-genererade markdown-sidor (en per protokoll)
├── assets/css/         # Stilmallar
├── scripts/
│   └── generate_pages.py  # Skript som hämtar data och genererar sidor
├── .github/workflows/
│   ├── generate_pages.yml  # Kör skriptet varje vecka
│   └── deploy_pages.yml    # Bygger och driftsätter Jekyll-sidan
├── _config.yml         # Jekyll-konfiguration
└── index.md            # Auto-genererad indexsida
```

## Köra lokalt

### Generera sidor

```bash
python3 scripts/generate_pages.py
```

Skriptet hämtar alla protokoll från Lokalhistoria.nu, skapar en markdown-fil
per protokoll i `_protokoll/` och uppdaterar `index.md`.

### Starta Jekyll lokalt

```bash
bundle install
bundle exec jekyll serve
```

Webbplatsen är sedan tillgänglig på `http://localhost:4000`.

## Automatisk uppdatering

GitHub Action `generate_pages.yml` körs varje söndag klockan 03:00 UTC och
uppdaterar automatiskt alla sidor om det finns förändringar i datakällan.

## Datakälla

Data hämtas från SLHD:s (Svensk Lokalhistorisk Databas) JSONP-API:

```
https://slhd.evryonehalmstad.se/Widget/Result?type=map&MapLocality=103&pagedResults=600&page=1
```

`MapLocality=103` avser Ås Socken.
