# The Research Roundup

An automated Python pipeline that collects new economics research every week (top journals, G10 and European central banks, the 12 regional Feds, NBER, BPEA, the IMF and the BIS), screens and classifies each paper for a Global Markets audience, and publishes a monthly email-ready newsletter with a static web dashboard.

> Work in progress. A full README (architecture, live URLs, deployment, costs, design choices) comes with the final milestone. See [docs/PLAN.md](docs/PLAN.md) for the build plan and [docs/SOURCES.md](docs/SOURCES.md) for the source inventory.

## Repository layout

```
config/sources.yaml   every source and how it is collected
pipeline/             Python package (`roundup` CLI), managed with uv
web/                  Next.js static dashboard
data/                 SQLite database (committed; the pipeline's source of truth)
docs/                 plan, sources, methodology
```

## Quickstart

```bash
cp .env.example .env          # add LLM_API_KEY and CONTACT_EMAIL
cd pipeline
uv sync
uv run pytest                 # offline: saved responses and FakeLLM

uv run roundup collect --since 2026-10-01      # fetch new papers into data/roundup.db
uv run roundup screen --limit 20               # classify with the screening model (set LLM_PROVIDER=fake for a free dry run)
uv run roundup build-issue --month 2026-10     # editor picks 5-8 papers; writes web/public/newsletters/2026-10.html
uv run roundup export                          # writes web/public/data/*.json

cd ../web && npm install && npm run dev        # dashboard at http://localhost:3000
```
