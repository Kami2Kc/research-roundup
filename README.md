# The Research Roundup

An automated Python pipeline that collects new economics research every week (top journals, G10 and European central banks, the 12 regional Feds, NBER, BPEA, the IMF and the BIS), screens and classifies each paper for a Global Markets audience, and publishes a monthly email-ready newsletter with a static web dashboard.

**Live:** [dashboard](https://research-roundup-zeta.vercel.app) · [October 2026 newsletter](https://research-roundup-zeta.vercel.app/newsletters/2026-10/) · [paper explorer](https://research-roundup-zeta.vercel.app/papers/) · [sources and coverage](https://research-roundup-zeta.vercel.app/sources/)

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

## Automation

Two GitHub Actions workflows run the pipeline and commit the results (the SQLite database and the dashboard's JSON and HTML), which redeploys the site:

| Workflow | Schedule | Runs |
|---|---|---|
| [`weekly.yml`](.github/workflows/weekly.yml) | Mondays 06:00 UTC | `roundup run-weekly`: collect (14-day lookback), screen, export |
| [`monthly.yml`](.github/workflows/monthly.yml) | 1st of the month, 07:00 UTC | `roundup run-monthly`: collect from the start of last month, screen, build last month's issue, export |

Both can be started by hand from the Actions tab (**Run workflow**). The monthly workflow accepts an optional month. They share a concurrency group so they never overlap.

Repository secrets (Settings → Secrets and variables → Actions):

| Secret | Required | Purpose |
|---|---|---|
| `LLM_API_KEY` | Yes | Anthropic API key |
| `CONTACT_EMAIL` | Yes | Contact address in the crawler's User-Agent and Crossref's `mailto` |
| `SITE_URL` | Recommended | Dashboard URL, for links in the newsletter (can also be a repository variable) |
| `VERCEL_DEPLOY_HOOK` | Optional | A Vercel deploy hook URL, if pushes from the Actions bot don't trigger a deployment |

The model names default to Claude Haiku 5.5 and Claude Sonnet 5.5. They can be changed with the repository variables `LLM_SCREEN_MODEL` and `LLM_EDITOR_MODEL`.

## Deploying the dashboard

The dashboard is a static Next.js export (`output: 'export'`) that reads the JSON and newsletter HTML committed under `web/public/`. On Vercel:

1. **Add New → Project**, and import this GitHub repository (private repositories work once the Vercel GitHub app has access).
2. Set **Root Directory** to `web`. The framework (Next.js), build command and output are detected automatically.
3. Deploy. Every push to `main`, including the data commits from GitHub Actions, rebuilds the site.

Then set `SITE_URL` to the deployment URL (in `.env` locally, and as a repository secret for Actions) so newsletters link back to the dashboard. To refresh links in an existing issue, run `uv run roundup build-issue --month YYYY-MM --render-only`.
