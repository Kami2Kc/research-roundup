# The Research Roundup: build plan

This is the plan for the Crédit Agricole CIB technical assessment. Read it in full before starting. Then work through it **one milestone at a time**, in order.

## 1. Context

The task is to build a fully automated Python application that:

1. **Collects** new publications every week from:
   - **Journals:** American Economic Review, Econometrica, Journal of Political Economy, Quarterly Journal of Economics, Review of Economic Studies.
   - **G10 central banks:** the Fed, Bank of Canada, Bank of England, Bank of Japan, Swiss National Bank, Sveriges Riksbank, Bundesbank, Banque de France, Banca d'Italia, De Nederlandsche Bank, National Bank of Belgium, and the ECB.
   - **The 12 Federal Reserve regional banks.**
   - **European national central banks.**
     - First priority: Banco de España, Bank of Finland (including BOFIT, its emerging-economies research unit), OeNB (Austria), Central Bank of Ireland, Banco de Portugal, Norges Bank, Danmarks Nationalbank, NBP (Poland), CNB (Czechia) and MNB (Hungary).
     - The rest of the euro area (Greece, Slovakia, Slovenia, Lithuania, Latvia, Estonia, Luxembourg, Malta, Cyprus, Croatia and Bulgaria): cover them if they have a feed or a simple page. Otherwise list them in `SOURCES.md` as not covered, with the reason. Spend no more than about 15 minutes on any one scraper.
   - **NBER, BPEA (Brookings), the IMF and the BIS.**
2. **Screens and classifies** each paper:
   - Relevance to a Global Markets Research audience (rates, FX, credit, macro, emerging markets).
   - Primary market focus: **EM**, **DM** or **Transversal**, with a short rationale.
3. **Publishes a monthly newsletter, "The Research Roundup".** Each issue features 5–8 curated papers, each with a plain-language summary, key takeaways and an analysis of its relevance. The output is responsive, email-ready HTML.
4. **Offers a web interface** where reviewers can:
   - view the current and past newsletters;
   - explore the papers used in each issue;
   - see each paper's classification tag and metadata.

**Deadline:** Friday 6 November 2026. **Target submission:** Thursday 5 November.

**Submission:** a GitHub repository link with deployment instructions and URLs for the live newsletter and dashboard.

**Assessed equally on:**
- source coverage;
- analytical quality (classification and summaries);
- newsletter presentation;
- the interactive interface.

### Rules from the hiring manager

- **Paywalled sources** are the five journals and recent NBER papers. For these, use titles and abstracts only.
- If a paper has no abstract available, leave it out of that cycle and log it.
- **Document every source that needed a fallback strategy.**
- Never bypass a paywall. Respect robots.txt and each site's terms.

## 2. Architecture

```
GitHub Actions (cron)                       Vercel or GitHub Pages
  weekly:  collect -> screen -> export ─┐
  monthly: build issue -> export ───────┼──> git commit ──> Next.js static site
                                        │                    - newsletter archive
  Python pipeline (`roundup` package)   │                    - paper explorer
    sources.yaml -> collectors          │                    - sources/coverage page
    -> SQLite (data/roundup.db)         │
    -> LLM screening -> editor          │
    -> Jinja2 newsletter HTML ──────────┘
    -> JSON export to web/public/data
```

- **Python does all the real work.** The brief asks for "a Python application that outputs the HTML newsletter". There is **no always-on backend server**. The pipeline runs as scheduled jobs.
- **Next.js (TypeScript, App Router) is a static dashboard.**
  - It uses `output: 'export'` and reads the JSON and HTML files that the pipeline writes into `web/public/`.
  - All filtering happens on the client side.
  - There is no database at runtime and no API server to host.
- **SQLite is the pipeline's source of truth** and is committed to the repository. The JSON export is just what the frontend reads.
- **Deployment:**
  - The site deploys to Vercel, with the project's root directory set to `web/`. GitHub Pages is the fallback.
  - Every data commit from Actions triggers a rebuild.

## 3. Repository layout

```
/config/sources.yaml          # every source, its access method and its settings
/pipeline/
  pyproject.toml              # uv-managed, Python 3.12+
  src/roundup/
    cli.py                    # entry point (Typer)
    config.py  models.py  db.py  llm.py
    collectors/  base.py crossref.py openalex.py rss.py html.py
    screening.py  editor.py  newsletter.py  export.py  health.py  eval.py
  templates/newsletter.html.j2
  tests/  fixtures/           # saved feed and API responses for offline tests
/data/roundup.db
/web/                         # Next.js app
  public/data/*.json          # written by `roundup export`
  public/newsletters/YYYY-MM.html
/docs/  PLAN.md  SOURCES.md  METHODOLOGY.md
/eval/labels.csv              # about 25 hand-labelled papers
/.github/workflows/ weekly.yml monthly.yml
README.md
```

## 4. Pipeline specification

### 4.1 Source configuration (`config/sources.yaml`)

Each source entry has these fields:

- `id`, `name`
- `group`: one of `journal`, `g10_cb`, `fed_regional`, `european_ncb`, `intl_org`, `nber`, `bpea`
- `country_or_region`
- `method`, in order of preference: `crossref` or `openalex`, then `rss`, then `html`; `none` for sources listed for coverage but not collected
- `url` (the source's listing page) and `feed_urls` (a list, because some sources publish one feed per series)
- `issns` or `doi_prefix`: only for the `crossref` and `openalex` methods
- `link_pattern` / `exclude_pattern`: optional regexes to keep or drop feed items (for mixed feeds)
- `selectors`: only for the `html` method
- `fallback`: the secondary method, if any (for example `openalex` for missing journal abstracts)
- `paywalled`: true or false
- `enabled`
- `notes`

**Adding a source must only require a config change.**

### 4.2 Collectors

- **Journals:** use the Crossref REST API, filtered by ISSN and publication date. Include a `mailto` parameter so requests go to Crossref's polite pool.
  - Crossref often has no abstract. If so, try OpenAlex.
  - **Check both APIs' current documentation and limits before building.**
- **RSS/Atom feeds:** use `feedparser`. Many central banks, the IMF, the BIS and NBER publish feeds. **Verify each feed URL rather than guessing.**
- **HTML pages:** use `httpx` with BeautifulSoup, driven by the selectors in the config. Use this only for important sources that have no feed.
- **Behaviour for every collector:**
  - a descriptive User-Agent that includes a contact email, read from the `CONTACT_EMAIL` environment variable (never hard-coded, because the repository will be public);
  - timeouts;
  - retries with exponential backoff;
  - at most about 1 request per second per host;
  - a robots.txt check;
  - **one source failing must never stop the whole run.**
- **The `Paper` model** has these fields:
  - `id`: the DOI if there is one, otherwise a hash of the normalised URL
  - `source_id`, `title`, `authors`, `abstract`, `url`, `published_date`
  - `paywalled`, `fetched_at`, `raw_meta` (JSON)
- **Deduplication:** an upsert on `id`, so re-running a collection adds nothing new.
  - Nice to have: match the same paper appearing under two sources, such as an NBER working paper that later appears in a journal, by comparing normalised titles.
- **Source health:** record the outcome of every run for every source:
  - status, items found, items new, the error if any, and the time taken.

### 4.3 Screening (weekly)

- Screen every new paper that has an abstract. Papers without one get `status = 'no_abstract'` and are excluded.
- Results go in a separate `screenings` table (paper ID, status, model, `prompt_version`, result JSON, tokens), not on `Paper`.
- **Never re-screen a paper.** Store the model name and `prompt_version` with each result.
- Use a **cheap, fast model** for this step.
- Ask for structured JSON output and validate it with Pydantic. If the output is invalid, retry up to twice.

```json
{
  "relevance_score": 0-10,
  "market_focus": "EM | DM | Transversal",
  "focus_rationale": "1-2 sentences",
  "topics": ["monetary policy", "FX", ...],
  "regions": ["euro area", "Brazil", ...]
}
```

- **Classification rules:** write these into the prompt and into `METHODOLOGY.md`.
  - **DM:** mainly about advanced economies, such as the US, the euro area, the UK, Japan, Canada, Switzerland, the Nordics, Australia and New Zealand.
  - **EM:** mainly about emerging or developing economies, such as China, India, Brazil, Mexico, Turkey, South Africa and Central and Eastern Europe.
  - **Transversal:** covers both groups, or is global, cross-country, theoretical or methodological with no particular focus on either.
- **Relevance:** score how useful the paper is to a sell-side markets research team covering rates, FX, credit, macro, EM, and sectors such as industrials, autos, retail and ESG.
- **Cost guards:**
  - cap the number of papers per run;
  - log the tokens used and the estimated cost.

### 4.4 Editor (monthly)

- **Candidate pool:** papers published in the target month with a relevance score of at least the configured threshold.
  - "Published" means the earliest online date (for journals, Crossref's `published-online`, falling back to `published-print` or `issued`). Document this in `METHODOLOGY.md`.
- A **stronger model** chooses **5–8** papers. It should:
  - prefer high relevance;
  - balance EM, DM and Transversal where the pool allows;
  - avoid near-duplicate topics.
- For each chosen paper, it writes:
  - a headline;
  - a plain-language summary of about 120 words;
  - 3 key takeaways;
  - "Why it matters for markets";
  - the market focus tag and rationale.
- It also writes a short editor's note for the top of the issue.
- Paywalled papers carry the label **"Summary based on abstract"**.
- **The editor is the genuinely agentic step.** It reviews the pool and justifies its choices. Store its selection rationale.

### 4.5 Newsletter (`newsletter.py` and the Jinja2 template)

- Email-safe HTML:
  - table-based layout, maximum width 600px;
  - CSS inlined with `css-inline`;
  - no JavaScript;
  - mobile-friendly.
- Structure:
  - a header reading "The Research Roundup" with the month;
  - the editor's note;
  - a card for each paper: tag badge, source, authors, date, summary, takeaways, why it matters and a link;
  - a footer with methodology, the number of sources monitored and the number of papers screened.
- Output: `web/public/newsletters/YYYY-MM.html`.

### 4.6 Export

Write the following to `web/public/data/`:

- `issues.json`: a list of issues with their dates and paper IDs;
- `papers.json`: every screened paper with its metadata, classification and issue membership;
- `sources.json`: coverage and the latest health results.

### 4.7 Command-line interface

| Command | What it does |
|---|---|
| `roundup collect [--since DATE] [--source ID]` | Fetch new publications |
| `roundup screen` | Classify papers that haven't been screened yet |
| `roundup build-issue --month YYYY-MM` | Build the newsletter for a month |
| `roundup export` | Write the JSON files for the dashboard |
| `roundup run-weekly` | `collect`, then `screen`, then `export` |
| `roundup run-monthly` | `collect`, `screen`, `build-issue` for the previous month, then `export` (collecting first catches papers from the last days of the month) |
| `roundup backfill --from 2026-08-01 --to 2026-10-31` | Collect, screen and build issues for past months |
| `roundup sources-report` | Print the coverage and health table |
| `roundup eval` | Compare the model's market focus with `eval/labels.csv` |

### 4.8 LLM layer (`llm.py`)

- One small interface with two methods: `complete_json(schema, prompt, model)` and `complete_text(...)`.
- One real provider, chosen with the `LLM_PROVIDER` environment variable (`anthropic`). The key comes from `LLM_API_KEY`.
  - Screening uses Claude Haiku 5.5 and the editor uses Claude Sonnet 5.5, set through `LLM_SCREEN_MODEL` and `LLM_EDITOR_MODEL`.
  - Development budget: about £15 in total. Check current pricing before setting the cost guards.
- A `FakeLLM` for tests, so they run offline and at no cost.
- Model names are configured through the environment, never hard-coded.

## 5. Dashboard (`web/`)

- Next.js App Router with TypeScript, Tailwind, shadcn/ui and TanStack Table (for sorting and filtering, rather than hand-written logic), using `output: 'export'`.
- **Pages:**

| Page | Shows |
|---|---|
| `/` | The latest issue, with links to past issues |
| `/issues/[month]` | The newsletter in an iframe, plus a list of the papers in that issue |
| `/papers` | A searchable, sortable table, with filters for market focus, source group, source, date range, "used in an issue" and relevance |
| `/papers/[id]` | Full metadata, abstract, classification and rationale, topics, regions, and a link |
| `/sources` | A coverage table: method, fallback, paywalled, last run status and paper count |

- Tag colours must be consistent everywhere: EM, DM and Transversal each always use the same colour.
- It must be responsive and clean. No authentication.

## 6. Automation and deployment

- **`weekly.yml`:** a cron job on Mondays at 06:00 UTC, plus `workflow_dispatch` so it can be run by hand. It:
  1. sets up Python with uv;
  2. runs `roundup run-weekly`;
  3. commits the database and the JSON files.
- **`monthly.yml`:** a cron job on the 1st of each month at 07:00 UTC, which runs `roundup run-monthly` and commits the results.
- Both workflows use `permissions: contents: write`, a `concurrency` group so they never overlap, and the `LLM_API_KEY` and `CONTACT_EMAIL` repository secrets.
- The repository stays private until just before submission. Vercel and Actions both work with private repositories.
- **Vercel:** import the repository with the root directory set to `web/`. Every push rebuilds the site.

## 7. Quality and documentation

- **Tests (pytest):**
  - parsers tested against saved fixtures;
  - idempotent upserts;
  - Pydantic validation of LLM output;
  - the template renders;
  - an end-to-end run with `FakeLLM`.
- **Evaluation:**
  - `eval/labels.csv` holds about 25 papers labelled by hand.
  - `roundup eval` reports how often the model's market focus agrees with the labels.
  - Put the figure in `METHODOLOGY.md`.
- **README:**
  - overview and an architecture diagram (Mermaid);
  - live URLs;
  - quickstart (local run, then backfill, then viewing the site);
  - configuration and how to add a source;
  - deployment;
  - costs;
  - limitations and next steps;
  - **Design choices:** scheduled batch jobs, data committed to git (the "git scraping" pattern) and a static Next.js dashboard. Explain why this suits a one-week prototype: no servers to keep running, free, and every run is visible in Actions.
  - **Production path:** ideally this would run as an extension of an existing Python backend or orchestrator (for example, scheduled jobs in the team's current service or in Airflow), with Postgres instead of SQLite in git, the dashboard served from the internal web stack, plus authentication, monitoring and alerting. The pipeline is plain CLI steps, so moving it is straightforward.
- **`docs/SOURCES.md`:** every source with its method, status (working, partial or not covered), whether it's paywalled, and the fallback used. The manager asked for this explicitly.
- **`docs/METHODOLOGY.md`:** the classification definitions, the prompts (with version numbers), the editor's selection logic and the evaluation result.

## 8. Milestones

**Work on a thin end-to-end slice first, then widen it.** There must always be a working end-to-end path.

| # | Milestone | Done when |
|---|---|---|
| **M0** | Scaffold the repository, uv project, Next.js app and config loader. **Draft `docs/SOURCES.md`** by checking each source for an API or RSS feed. Mark anything unverified. | The source inventory is complete. `roundup --help` works. |
| **M1** | **The thin slice:** the journals via Crossref/OpenAlex, plus 3–4 RSS sources (such as the IMF, BIS, ECB and one Fed bank), stored in SQLite, screened, with one newsletter built for October 2026 and a basic dashboard reading the JSON. | The October issue HTML exists and appears on the local dashboard. |
| **M2** | **Coverage:** every remaining source with a feed, HTML collectors for important sources without one, and the source health report. | The coverage table shows the status of every source. |
| **M3** | **Quality:** refine the prompts, add the editor's balancing logic, polish the newsletter design, and complete the evaluation. | The issues read professionally, and the evaluation figure is recorded. |
| **M4** | **Dashboard:** the full explorer, filters, paper pages and sources page. Deploy to Vercel. | Live URLs work. |
| **M5** | **Backfill and automation:** issues for August, September and October, and both workflows tested with `workflow_dispatch`. | Three issues are live, and a manual workflow run succeeds. |
| **M6** | **Documentation and final checks:** README, METHODOLOGY and SOURCES complete; test a fresh clone. | Ready to submit. |

**Schedule:**
- Saturday: M0 and M1.
- Sunday: M2 to M4.
- Monday to Wednesday evenings, about 1 hour each: M5, M6 and fixes.
- Thursday: submit.

**If time runs short, cut in this order:**
1. the nice-to-have deduplication across sources;
2. HTML scrapers for minor European central banks (document them as not covered instead);
3. dashboard polish.

**Never cut:** the end-to-end automation, the classification rationale, the paywall and fallback documentation, or the README.

## 9. Working agreement for Claude Code

- Work on one milestone at a time. At the end of each, summarise what changed and how to verify it, then commit with a clear message.
- **Ask before adding a dependency** that isn't named in this plan. Approved: PyYAML, pydantic, the `anthropic` SDK, python-dotenv, Typer, httpx, feedparser, BeautifulSoup, Jinja2, css-inline, pytest; shadcn/ui and TanStack Table on the web side. Retries are hand-written and the database uses plain `sqlite3` with no ORM.
- Never hard-code secrets. Use a `.env` file (git-ignored) locally and Actions secrets in CI. Provide `.env.example`.
- **Do not invent feed URLs or API details.** Fetch the real page or documentation to check. If something can't be checked, mark it as unverified in `SOURCES.md`.
- Prefer simple, readable code over clever abstractions.
- Keep the LLM costs of development runs low: use `FakeLLM` or small `--limit` values until the prompts are stable.
