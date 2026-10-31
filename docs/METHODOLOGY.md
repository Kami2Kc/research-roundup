# Methodology

How The Research Roundup decides what a paper is about, whether it matters to a Global Markets audience, and which papers make the monthly issue. The prompts below are copied from the code (`pipeline/src/roundup/screening.py` and `editor.py`). Every stored result records the model and prompt version that produced it.

## Pipeline at a glance

| Step | When | Model | What it does |
|---|---|---|---|
| Collect | Weekly | – | Fetch new papers from every enabled source (see [SOURCES.md](SOURCES.md)) |
| Screen | Weekly | Claude Haiku 5.5, effort `low` | Score relevance 0–10, classify market focus, assign topics and regions |
| Edit | Monthly | Claude Sonnet 5.5, effort `high` | Choose 5–8 papers, justify the selection, write the summaries and the editor's note |
| Publish | Monthly | – | Render email-safe HTML and export JSON for the dashboard |

Model names come from environment variables (`LLM_SCREEN_MODEL`, `LLM_EDITOR_MODEL`); nothing in the code picks a model.

## Market focus

Every screened paper gets exactly one tag:

- **DM**: mainly about advanced economies, such as the US, the euro area, the UK, Japan, Canada, Switzerland, the Nordics, Australia and New Zealand. Every euro area member is DM, including the periphery (Italy, Spain, Portugal, Greece, Ireland). A study of several advanced economies is still DM.
- **EM**: mainly about emerging or developing economies, such as China, India, Brazil, Mexico, Turkey, South Africa, the Gulf states, and Central and Eastern European economies outside the euro area (such as Poland, Czechia, Hungary and Romania).
- **Transversal**: covers both groups, or is global, cross-country, theoretical or methodological with no particular focus on either.

The tag depends on the economies a paper studies, not on who published it: an ECB paper about Chinese exports is EM. The model also writes a one- or two-sentence rationale naming those economies, and the dashboard shows it next to the tag.

## Relevance

A 0–10 score for how useful the paper is to a sell-side research team covering rates, FX, credit, macro, emerging markets, and sectors (industrials, autos, retail, ESG):

| Score | Meaning |
|---|---|
| 9–10 | Directly about market pricing, monetary or fiscal policy and its transmission, inflation, rates, FX, credit, sovereign risk, capital flows or financial stability, with implications a strategist could use now |
| 6–8 | A macro or financial topic with a clear indirect link to markets (labour markets, productivity, trade, housing, banking, energy, equities, the climate transition, sector dynamics), plus applicable forecasting and nowcasting methods |
| 3–5 | Economics with a weak link to markets (most applied microeconomics, public-finance details, general econometric theory, development without a macro angle) |
| 0–2 | No meaningful link (health, education, history, pure theory with no application, non-research items) |

Papers scoring **6 or more** enter the monthly candidate pool. The threshold can be changed with `RELEVANCE_THRESHOLD`.

## Topics and regions

Topics come from a fixed list, so the dashboard can filter on them. Each paper gets one to three topics, the main one first: monetary policy; inflation; interest rates and bonds; FX and capital flows; credit and corporate finance; banking and financial stability; fiscal policy and sovereign debt; growth and productivity; labour markets; trade and supply chains; housing and real estate; energy and commodities; climate and ESG; equities and asset pricing; households and consumption; payments and digital money; AI and technology; industrials, autos and retail; development; econometrics and forecasting; health, education and social policy; other.

Regions are the economies studied, using short common names ("US", "euro area", "China", "Latin America"), with "global" for worldwide or broad cross-country samples.

## Rules on abstracts and dates

- **Titles and abstracts only.** We never fetch full text for anything, so summaries of paywalled journal and NBER papers carry the label "Summary based on abstract".
- **Screening needs an abstract** of at least 100 characters. Anything shorter is a feed teaser. Papers without one get the status `no_abstract`, are logged, and are re-checked on later runs, because abstracts often reach OpenAlex a few days after publication.
- **The editor needs at least 400 characters of abstract.** A thinner abstract cannot support a 120-word summary without padding. We added this rule after an early draft summarised a 216-character abstract mostly by saying what the abstract didn't contain.
- **Publication date** decides which month's issue a paper belongs to.
  - Crossref sources: the earliest full date among online publication, print publication, issue date and DOI registration. Econometrica deposits year-only dates and AER deposits future issue dates; DOI registration is when a paper goes online.
  - Feeds and listings: the item's own date.
  - Listings without dates (MNB, BPEA): the date we first saw the paper.
- **Never re-screened.** A paper's screening is stored with the model name and prompt version, and the weekly run never sends it again. During development we deliberately replaced early versions (`screen-v1` and `screen-v2`) with `screen-v3`, so every published classification uses one prompt.

## Screening prompt (`screen-v3`)

Each paper is sent as `Title`, `Source` and `Abstract`. The model returns JSON that must validate against this schema, or the call is retried up to twice:

```json
{
  "relevance_score": "integer 0-10",
  "market_focus": "EM | DM | Transversal",
  "focus_rationale": "1-2 sentences",
  "topics": ["1-3 values from the fixed list"],
  "regions": ["economies studied"]
}
```

System prompt:

```text
You screen new economics research for the Global Markets Research team of a European corporate and investment bank. The team covers rates, FX, credit, macro and emerging markets, plus sector research on industrials, autos, retail and ESG. Its readers are sell-side strategists and economists who want research that changes how they think about markets, policy or the economic outlook.

You get each paper's title, source and abstract (never the full text). Return:

relevance_score: an integer from 0 to 10 for how useful the paper is to this team.
- 9-10: directly about market pricing, monetary or fiscal policy and its transmission, inflation, interest rates, FX, credit, sovereign risk, capital flows or financial stability, with implications a strategist could use now.
- 6-8: a macro or financial topic with a clear indirect link to markets: labour markets, productivity, trade, housing, banking, energy, equities, the climate transition, or dynamics in industrials, autos or retail. Forecasting and nowcasting methods that macro economists can apply belong here too.
- 3-5: economics with a weak link to markets, such as most applied microeconomics, public-finance details, general econometric theory, or development topics without a macro or financial angle.
- 0-2: no meaningful link: health, education, history, pure theory with no application, or items that are not research.
Calibration examples:
- "Treasury issuance and dealer balance sheets" (repo and bond market functioning): 9.
- "Monetary policy transmission in Morocco after an exchange-rate reform": 8.
- "Pricing power in the US mortgage market": 7.
- "Clustered standard errors for regression with spatial data": 3.
- "Selective admissions in nursing homes": 2.

market_focus: exactly one of "EM", "DM" or "Transversal".
- DM: mainly about advanced economies, such as the US, the euro area, the UK, Japan, Canada, Switzerland, the Nordics, Australia and New Zealand. Every euro area member is DM, including the periphery (Italy, Spain, Portugal, Greece, Ireland). A study of several advanced economies is still DM.
- EM: mainly about emerging or developing economies, such as China, India, Brazil, Mexico, Turkey, South Africa, the Gulf states, and Central and Eastern European economies outside the euro area (such as Poland, Czechia, Hungary and Romania).
- Transversal: covers both groups, or is global, cross-country, theoretical or methodological with no particular focus on either.
Decide from the economies the paper studies, not from the institution that published it: an ECB paper about Chinese exports is EM, and a Federal Reserve paper with a purely theoretical model is Transversal.

focus_rationale: one or two sentences naming the economies studied, or why the paper is Transversal.
topics: one to three topics from the allowed list, most important first.
regions: the economies or regions studied, using short common names: "US", "euro area", "UK", "Japan", "China", "Germany", "Brazil", "Latin America", "sub-Saharan Africa". Use "global" for worldwide or broad cross-country samples. Use an empty list for theory with no particular place.
```

Version history: `screen-v1` was the first draft. `screen-v2` made the euro-area periphery explicitly DM, after the first test batch tagged a paper on Italian and Spanish banks EM, and placed non-euro CEE and the Gulf in EM. `screen-v3` introduced the fixed topic list and region naming, added sector and forecasting guidance, and added five calibration examples.

## The editor (`editor-v2`)

The editor is the agentic step. It reviews the month's candidates, makes and justifies a selection, and revises its work when the code finds a problem.

**1. Candidate pool.** These are the month's screened papers with relevance ≥ 6 and an abstract of at least 400 characters. Up to 8 places are reserved for each market focus, and the rest go to the highest scores, up to 40 candidates. Without the reserved places, October's pool would have been almost entirely DM: 148 DM papers scored 6 or more, against 57 Transversal and 18 EM.

**2. Selection.** The model chooses 5–8 papers, orders them, gives a reason for each, and writes a rationale for the issue that includes notable papers it left out. The code then checks the selection:

- between 5 and 8 papers, all from the candidate list, none repeated;
- at least one EM, one DM and one Transversal paper where the pool has them;
- no more than half the issue from one market focus (enforced when every focus has at least two candidates);
- at most two papers from the same source, and at most two sharing a main topic.

If any check fails, the model sees its own answer and the list of problems and tries again, up to twice. In October's first build, for example, the model mistyped a paper ID; the check caught it and the revised selection was valid.

**3. Write-up.** For each chosen paper, the model writes a headline, a summary of about 120 words, three takeaways, "Why it matters for markets", and the market focus with a rationale. It also writes the editor's note. The code checks word counts (headline 4–14 words, summary 80–170, "Why it matters" 25–90, editor's note 60–160) and that every chosen paper is written up exactly once. Problems go back for revision in the same way.

The selection rationale and each paper's reason are stored and shown on the dashboard's issue page. If the editor changes a paper's market focus from the screening result, this is logged. The newsletter shows the editor's tag, and the dashboard keeps the screening tag.

Selection system prompt:

```text
You are the editor of The Research Roundup, a monthly newsletter that brings the month's most useful new economics research to the Global Markets Research team of a European corporate and investment bank. The team covers rates, FX, credit, macro and emerging markets, plus sector research on industrials, autos, retail and ESG.

You receive the month's candidate papers. Each has been screened already: it has a relevance score out of 10, a market focus (EM, DM or Transversal) and topics. The pool deliberately includes the best EM and Transversal papers even when they score lower than the DM papers. Choose the papers for this month's issue:
- Choose between 5 and 8 papers.
- Prefer higher relevance. A lower-scored paper should beat a higher-scored one only when it adds something the issue would otherwise lack.
- Balance market focus: include at least one EM, one DM and one Transversal paper where the pool has them, and no more than half the issue from any one focus.
- Variety: at most 2 papers from the same source, and at most 2 papers whose main (first-listed) topic is the same. Never pick two papers on essentially the same question.
- When quality is similar, prefer a mix of source types (journals, central banks, international organisations).

Order the picks from most to least important and give a one-sentence reason for each. Then write a rationale of three to five sentences for the issue as a whole: what you prioritised, and which notable candidates you left out and why.
```

Write-up system prompt:

```text
You write The Research Roundup, a monthly newsletter of new economics research for the Global Markets Research team of a European corporate and investment bank (rates, FX, credit, macro, emerging markets, sectors). Readers are busy strategists and economists: write so they can grasp each paper in under a minute.

For each paper you receive its metadata, abstract and screening classification. You never see the full text, so base everything on the abstract: never invent data, numbers, methods or findings that it does not state, and keep any figures exactly as the abstract gives them.

For each paper, write:
- headline: a plain, specific headline of at most 12 words that states the finding. No hype, no puns, no question marks.
- summary: about 120 words (between 90 and 150) in plain language: the question, how the authors answer it, and what they find. Spell out acronyms on first use (except US, UK, GDP, ECB, IMF).
- takeaways: exactly three key takeaways, one sentence of at most 25 words each, none repeating the headline.
- why_it_matters: two or three sentences (40 to 80 words) on what the paper means for views on rates, FX, credit, macro, emerging markets or the sectors the team covers. Be concrete about the channel or asset class, but do not overclaim or give investment advice.
- market_focus: keep the screening classification unless it is clearly wrong.
- focus_rationale: one sentence for readers explaining the market focus.

Then write editor_note: 80 to 130 words introducing the issue: the month's main themes and how the papers connect. Do not list every paper.

Use British English and plain text (no markdown, no bullet characters).
```

Version history: `editor-v1` chose 5–8 papers from the top 40 by score and checked only the count, the IDs and the presence of each market focus. `editor-v2` added the reserved places in the pool, the balance and variety rules, the word limits, and the 400-character abstract minimum.

## Evaluation

`eval/labels.csv` holds 25 October 2026 papers, labelled by hand for market focus (and optionally relevance) without seeing the model's answers. The papers are stratified across the model's earlier EM, DM and Transversal predictions and span six source types. `roundup eval` runs the current screening prompt on them and reports agreement, a confusion matrix and Cohen's kappa (agreement corrected for chance).

**Result (prompt `screen-v3`, Claude Haiku 5.5, 1 November 2026): the model's market focus matched the human label on 22 of 25 papers (88%), with a Cohen's kappa of 0.82.** With 25 papers, the 95% confidence interval for agreement is roughly 70% to 96%.

| Label \ model | EM | DM | Transversal |
|---|---:|---:|---:|
| **EM** | 7 | 0 | 0 |
| **DM** | 0 | 8 | 1 |
| **Transversal** | 1 | 1 | 7 |

The model never confused EM with DM. All three disagreements sit on the boundary with Transversal:

- *US monetary policy spillovers through global commercial real estate*: labelled DM, model said Transversal. A cross-country panel of property markets, which is a borderline call.
- *Fiscal integration as a Pareto improvement*: labelled Transversal, model said EM. A theoretical model of a generic currency union with a "risky" and a "safe" member. Under our rules this is Transversal, and the model's own rationale admitted Transversal was defensible. This is a genuine error.
- *Beyond valuations: long-term financial risks from the AI build-out*: labelled Transversal, model said DM. The model inferred a US focus that the abstract does not state.

A future prompt version could say explicitly that theory about a generic economy is Transversal even when a region motivates it, and that the model should not infer countries the abstract doesn't name. We have not made that change: tuning the prompt on these 25 papers would inflate the figure, so it would need a fresh labelled set to measure honestly.

To reproduce: `cd pipeline && uv run roundup eval` (under one cent). Per-paper results are written to `eval/results.csv`.

## Cost

Prices were checked on 31 October 2026: Claude Haiku 5.5 costs $0.10 per million input tokens and $0.50 per million output tokens; Claude Sonnet 5.5 costs $2 and $10.

| Step | Measured (October 2026) |
|---|---|
| Screening | 349 papers, about 2,100 input and 150 output tokens each: **$0.10 a month** |
| Editor | About 27,000 input and 13,000 output tokens per issue, including any revisions: **about $0.20 an issue** |

A full year of weekly screening and monthly issues costs under $5. Each run caps screening at `SCREEN_LIMIT` papers (default 300) and prints the tokens used and the estimated cost.

## Limitations

- **Abstract-only.** Summaries can't go beyond what the abstract says, and some papers (especially JPE) have no abstract we can use.
- **Coverage gaps.** Eighteen smaller European central banks aren't covered, including BOFIT, Czechia and Poland, so EM research comes mostly from the IMF and BIS. EM papers were about 10% of October's screened papers.
- **Model judgement.** Market focus and relevance are model outputs. The evaluation (88% agreement on market focus) uses one labeller and 25 papers, and relevance scores have not been evaluated against human judgement yet. The rationale is always shown, so readers can judge for themselves.
- **No cross-source deduplication yet.** An NBER paper that later appears in a journal would be treated as two papers.
