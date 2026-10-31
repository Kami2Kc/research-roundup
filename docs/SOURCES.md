# Sources

Every source The Research Roundup monitors: how it's collected, whether it's paywalled, and what fallback it needs. The configuration lives in [`config/sources.yaml`](../config/sources.yaml); this page explains it.

> **Status: draft inventory (M0), checked on 31 October 2026.** Each endpoint below was fetched and parsed, not guessed. "Verified" means the API or feed responded, parsed, and had current items. Status changes to *working*, *partial* or *not covered* once the collectors run (M2). Anything we couldn't confirm is marked **unverified**.

## Summary

| Group | Sources | Verified API / feed | HTML to build | Blocked | Unresolved |
|---|---:|---:|---:|---:|---:|
| Journals | 5 | 5 | – | – | – |
| NBER, BPEA, IMF, BIS | 4 | 3 | – | – | 1 (BPEA) |
| G10 central banks | 12 | 9 | 3 | – | – |
| Fed regional banks | 12 | 12 | – | – | – |
| European NCBs (first priority) | 11 | 2 | 4 | 2 | 3 |
| European NCBs (rest of euro area) | 11 | – | 7 | 2 | 2 |
| **Total** | **55** | **31** | **14** | **4** | **6** |

## How we collect, and the rules we follow

- **Order of preference:** a scholarly metadata API (Crossref, then OpenAlex), then the publisher's own RSS/Atom feed, then the HTML listing page. HTML is used only for important sources with no feed.
- **Paywalls:** the five journals and NBER are treated as paywalled. We use **titles and abstracts only** and never fetch full text. A paper with no abstract is skipped for that cycle and logged.
- **Politeness:** every request sends a descriptive User-Agent with a contact address, checks robots.txt (including any crawl delay), and stays at about one request per second per host. When a site refuses our identified crawler (HTTP 403), we record it as blocked and **do not** try to get around it.

### APIs

| API | Use | Limits (checked 31 Oct 2026) |
|---|---|---|
| [Crossref REST API](https://api.crossref.org) | Journal and working-paper metadata by ISSN or DOI prefix | Polite pool (with `mailto`): 3 requests/second, 3 concurrent (from the API's `x-rate-limit-*` headers) |
| [OpenAlex](https://docs.openalex.org) | Abstracts missing from Crossref, looked up by DOI in batches of up to 50 | Without a key: 10 requests/second and about 1,000 list requests a day. A free key raises the daily budget tenfold (optional `OPENALEX_API_KEY`). Abstracts come as an inverted index and are rebuilt locally. |

**Collection window for Crossref sources:** we filter on the DOI *registration* date (`from-created-date`), not the publication date. Econometrica's records carry only the year (`2026`), and AER's carry the issue date, so a publication-date filter would miss or misdate papers. Registration happens when a paper goes online.

## Journals

All five are paywalled. Method: Crossref by ISSN, with OpenAlex as the fallback for abstracts. Abstract coverage was measured on articles registered between July and October 2026.

| Source | ISSNs | Crossref abstracts | OpenAlex abstracts | Status | Notes |
|---|---|---|---|---|---|
| American Economic Review | 0002-8282, 1944-7981 | 42 / 49 | 41 / 48 | Verified | Issue date only; no separate online date |
| Econometrica | 0012-9682, 1468-0262 | 12 / 14 | – | Verified | Year-only dates, so the registration-date window is essential |
| Journal of Political Economy | 0022-3808, 1537-534X | 0 / 73 | 18 / 50 | Verified, **partial abstracts** | About two-thirds of JPE papers will have no abstract and will be skipped and logged. The publisher's own table-of-contents feed is **unverified** as a second fallback. |
| Quarterly Journal of Economics | 0033-5533, 1531-4650 | 19 / 20 | 19 / 20 | Verified | Has separate online and print dates |
| Review of Economic Studies | 0034-6527, 1467-937X | 47 / 47 | 46 / 47 | Verified | |

Non-research items (front matter, editors' reports, "turnaround times") will be filtered out by title so they aren't logged as missing abstracts.

## NBER, BPEA, IMF and BIS

| Source | Method | Endpoint | Abstracts | Paywalled | Status | Notes |
|---|---|---|---|---|---|---|
| NBER Working Papers | Crossref (DOI prefix `10.3386`) + OpenAlex | `api.crossref.org/works?filter=prefix:10.3386` | OpenAlex 47 / 50 | Yes | Verified | 423 papers registered since 1 August. The RSS feed (`back.nber.org/rss/new.xml`) has abstracts but no dates and only about a week of papers, so it can't support a backfill. It remains a fallback. |
| Brookings Papers on Economic Activity | – | – | – | No | **Unverified** | Crossref only holds the JSTOR archive (nothing since 2006). The BPEA paper list is loaded by JavaScript, and Brookings' WordPress feeds returned no items. BPEA publishes twice a year (spring and fall). To try in M2: the conference pages. |
| IMF Working Papers | Crossref (ISSN `1018-5941`) | `api.crossref.org/journals/1018-5941/works` | Crossref 50 / 50 | No | Verified | 53 papers since 1 September. The old IMF RSS endpoint now returns 404. |
| BIS | RSS | `bis.org/doclist/bis_fsi_publs.rss` | Yes (about 300 characters) | No | Verified | The "Research papers" feed mixes working papers, BIS Bulletins and BIS Papers. It isn't listed under that name in the BIS feed index, but it carries all three. |

## G10 central banks

| Source | Method | Feed / page | Summaries in feed | Status | Notes |
|---|---|---|---|---|---|
| Federal Reserve Board | RSS | `federalreserve.gov/feeds/` `feds.xml`, `ifdp.xml`, `feds_notes.xml` | Yes (about 1,000 characters) | Verified | FEDS, IFDP and FEDS Notes |
| Bank of Canada | RSS | `bankofcanada.ca/content_type/` `working-papers`, `discussion-papers`, `staff-analytical-notes` `/feed/` | Yes (about 300) | Verified | |
| Bank of England | RSS (filtered) | `bankofengland.co.uk/rss/publications` | Short (about 120) | Verified | General publications feed, filtered by URL to staff working papers (15 of 50 items). May need each paper's page for the full abstract. |
| Bank of Japan | RSS (filtered) | `boj.or.jp/en/rss/whatsnew.xml` | **None** | Verified, **partial** | "What's new" feed filtered to `/en/research/` (9 of 51 items). Many links go straight to PDFs, so abstracts will often be missing. |
| Swiss National Bank | RSS | `snb.ch/public/rss/en/papers` | Yes (about 800) | Verified | Working Papers, Economic Studies, Economic Notes |
| Sveriges Riksbank | HTML (to build) | `riksbank.se/en-gb/press-and-published/publications/working-paper-series/` | – | No feed | The Riksbank's feeds cover only press releases, notices, speeches, minutes and the calendar |
| Deutsche Bundesbank | RSS | `bundesbank.de/service/rss/en/633292/feed.rss` | **None** | Verified | Discussion Papers. Abstracts must come from each paper's page. |
| Banque de France | HTML (to build) | `banque-france.fr/en/publications-and-research/research-publications` | – | No feed, **unverified** | No feed found. The listing page has no paper links in its HTML and is probably rendered by JavaScript. |
| Banca d'Italia | HTML (to build) | `bancaditalia.it/pubblicazioni/temi-discussione/` | – | Feed disallowed | Feeds exist under `/util/`, but **robots.txt disallows `/util/`**, so we don't use them. The working-paper listing is allowed, with a 5-second crawl delay. |
| De Nederlandsche Bank | RSS | `dnb.nl/en/rss/16455/4614/Working%20Papers` and `…/Occasional%20Studies` | **None** | Verified | Abstracts must come from each paper's page |
| National Bank of Belgium | RSS | `nbb.be/en/publication_rss.xml` | Short (about 130) | Verified | All-publications feed; screening sorts out the research items |
| European Central Bank | RSS | `ecb.europa.eu/rss/wppub.html`, `…/rbu.html` | Yes (about 1,000) | Verified | Working Papers and the Research Bulletin |

## Federal Reserve regional banks

All 12 use **[Fed in Print](https://www.fedinprint.org)**, the Federal Reserve System's own research catalogue. It publishes one RSS feed per bank (`fedinprint.org/rss/<bank>.rss`) with abstracts (350 to 1,000 characters), authors, dates, the series name and often a DOI. One collector covers the whole System consistently. Speeches and remarks are filtered out by series and title.

| Bank | Fed in Print feed | Status | Notes |
|---|---|---|---|
| Boston | `boston.rss` | Verified | The bank's own research feed stopped updating in 2020 |
| New York | `newyork.rss` | Verified | Staff Reports, Liberty Street Economics |
| Philadelphia | `philadelphia.rss` | Verified | |
| Cleveland | `cleveland.rss` | Verified | |
| Richmond | `richmond.rss` | Verified | |
| Atlanta | `atlanta.rss` | Verified | Own feed `atlantafed.org/rss/wps` also works (alternative) |
| Chicago | `chicago.rss` | Verified | |
| St. Louis | `stlouis.rss` | Verified | |
| Minneapolis | `minneapolis.rss` | Verified | |
| Kansas City | `kansascity.rss` | Verified | |
| Dallas | `dallas.rss` | Verified | |
| San Francisco | `sanfrancisco.rss` | Verified | |

**Limitation:** each feed holds the latest 25 items. That covers one to three months for most banks, but a full August–October backfill may not reach the earliest weeks for the busiest banks (New York's feed currently goes back to 1 September).

## European national central banks: first priority

| Source | Method | Feed / page | Status | Notes |
|---|---|---|---|---|
| Banco de España | RSS (filtered) | `bde.es/wbe/en/inicio/rss/rss-estudios-publicaciones/` | Verified | Filtered to Working and Occasional Papers. Short summaries. Papers also have Crossref DOIs (prefix `10.53479`) with abstracts for about 60%, a possible fallback. |
| Bank of Finland | HTML (to build) | `suomenpankki.fi/en/publications/research-publications/discussion-papers/` | No feed | The BoF Bulletin has a feed (`bofbulletin.fi/rss/articles/`), but it carries policy articles rather than research papers |
| BOFIT (Bank of Finland) | HTML (to build) | `bofit.fi/en/publications/discussion-papers/` | No feed, **unverified** | No paper links in the HTML; needs a closer look. An important EM source. |
| Oesterreichische Nationalbank | – | – | **Unverified** | No feed found, and the working-paper listing URL is not yet located |
| Central Bank of Ireland | HTML (to build) | `centralbank.ie/publication/research-publications/research-technical-papers` | No feed | Listing page loads and robots.txt allows it |
| Banco de Portugal | – | – | **Blocked** | Returns 403 to our identified crawler |
| Norges Bank | RSS | `norges-bank.no/en/rss-feeds/Working-papers---Norges-Bank/`, `…/Staff-Memo---Norges-Bank/` | Verified | No summaries. Abstracts must come from each paper's page. |
| Danmarks Nationalbank | – | – | **Unverified** | No feed found; the site appears to render with JavaScript |
| Narodowy Bank Polski | – | – | **Blocked** | Returns 403 to our identified crawler |
| Czech National Bank | HTML (to build) | `cnb.cz/en/economic-research/research-publications/` | No feed, **unverified** | Feeds cover only press releases and the cnBlog. No paper links in the HTML. |
| Magyar Nemzeti Bank | – | – | **Unverified** | No feed found, and the working-paper listing URL is not yet located |

## European national central banks: rest of the euro area

Covered only if there's a feed or a simple page. No scraper gets more than about 15 minutes.

| Source | Method | Page | Status | Notes |
|---|---|---|---|---|
| Bank of Greece | – | – | **Blocked** | Returns 403 to our identified crawler |
| Národná banka Slovenska | HTML (to build) | `nbs.sk/en/publications/research-papers-working-and-occasional-papers-wp-op/` | No feed | |
| Banka Slovenije | HTML (to build) | `bsi.si/en/blog-and-research-publications` | No feed | Posts are linked in the HTML |
| Lietuvos bankas | – | – | **Blocked** | Returns 403 to our identified crawler |
| Latvijas Banka | HTML (to build) | `bank.lv/en/news-and-events/working-papers/2026` | No feed, **unverified** | One listing page per year; no paper links in the HTML |
| Eesti Pank | HTML (to build) | `eestipank.ee/en/publications/working-papers` | No feed | The homepage links recent working papers in its HTML |
| Banque centrale du Luxembourg | HTML (to build) | `bcl.lu/en/publications/Working-papers/index.html` | No research feed | The general feed (`bcl.lu/en/support/rss/00_rssfeed.rss`) carries press releases |
| Central Bank of Malta | HTML (to build) | `centralbankmalta.org/en/all-pubs-res` | No feed | Items link straight to PDFs with no abstract, so they would mostly be skipped |
| Central Bank of Cyprus | – | – | **Unverified** | No feed, and no paper links on the publications page |
| Hrvatska narodna banka | HTML (to build) | `hnb.hr/en/analyses-and-publications/occasional-publications/working-papers` | No feed, **unverified** | No paper links in the HTML |
| Bulgarian National Bank | – | – | **Unverified** | RSS covers press-office categories in Bulgarian only |

## Fallback strategies

The hiring manager asked for every source that needed a fallback to be documented.

| Source | Problem | Fallback |
|---|---|---|
| All five journals | Crossref often lacks abstracts | OpenAlex abstract lookup by DOI |
| Econometrica, AER | Crossref dates are year-only or issue dates | Collection window on DOI registration date |
| JPE | No Crossref abstracts; OpenAlex covers about a third | Papers without an abstract are skipped and logged each cycle |
| NBER | Crossref has no abstracts; RSS has no dates or history | Crossref for discovery and dates, OpenAlex for abstracts |
| IMF | RSS endpoint gone (404) | Crossref by the Working Papers ISSN |
| Fed regional banks | Native feeds are inconsistent (Boston's stopped in 2020) | Fed in Print feeds for all 12 |
| Bank of England, Bank of Japan, Banco de España | Mixed general feeds | Feed items filtered by URL pattern |
| Bundesbank, DNB, Norges Bank, BoJ | Feeds have no summaries | Abstract taken from each paper's page (to build in M1/M2) |
| Banca d'Italia | Feed path disallowed by robots.txt | HTML listing page, with a 5-second crawl delay |
| Riksbank, Bank of Finland, CBI and others | No feed | HTML listing page (M2) |
| Banco de Portugal, NBP, Bank of Greece, Lietuvos bankas | 403 to our crawler | None. Documented as not covered. |
