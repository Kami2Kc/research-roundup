# Sources

Every source The Research Roundup monitors: how it's collected, whether it's paywalled, its status, and the fallback it needed. The configuration lives in [`config/sources.yaml`](../config/sources.yaml). Live status comes from `roundup sources-report`, and the dashboard's Sources page shows the same data.

> **Status as of 1 November 2026**, after collecting every enabled source back to 1 August 2026 and the first scheduled weekly and monthly runs (all 37 enabled sources ran without errors).
> - **Working:** collected successfully, and at least half its papers have abstracts.
> - **Partial:** collected successfully, but most papers lack an abstract (they are logged and skipped), or the source can't be fully dated.
> - **Not covered:** we don't collect it. The reason is given below.

## Summary

| Group | Sources | Working | Partial | Not covered |
|---|---:|---:|---:|---:|
| Journals | 5 | 4 | 1 (JPE) | – |
| NBER, BPEA, IMF, BIS | 4 | 3 | 1 (BPEA) | – |
| G10 central banks | 12 | 11 | 1 (Riksbank) | – |
| Fed regional banks | 12 | 12 | – | – |
| European NCBs: first priority | 11 | 2 | 1 (MNB) | 8 |
| European NCBs: rest of euro area | 11 | 1 | – | 10 |
| **Total** | **55** | **33** | **4** | **18** |

Every G10 central bank, every regional Fed, NBER, the IMF, the BIS and four of the five journals are fully covered. The gaps are among the smaller European central banks. Most of them have no feed and render their research lists with JavaScript, and four of them block our crawler.

## How we collect, and the rules we follow

- **Order of preference:** a scholarly metadata API (Crossref, then OpenAlex), then the publisher's RSS/Atom feed, then the HTML listing page. HTML is used only for important sources with no feed. Each source's method, URLs and CSS selectors live in the config, so adding a source needs no code.
- **Paywalls:** the five journals and NBER are treated as paywalled. We use **titles and abstracts only** and never fetch full text. Their summaries in the newsletter are labelled "Summary based on abstract".
- **No abstract, no screening:** a paper without an abstract (or with a teaser under 100 characters) is stored, logged and skipped that cycle. It is re-checked on later runs, because abstracts often appear in OpenAlex a few days after publication.
- **Politeness:** every request sends a descriptive User-Agent with a contact address. We check robots.txt before each request and honour any crawl delay (Banca d'Italia asks for 5 seconds). Otherwise we make at most one request per second per host. Requests retry with backoff on errors.
- **Blocked sites stay blocked:** when a site refuses our identified crawler (HTTP 403), we record it and **do not** try to get around it.
- **History for the backfill:** API sources (Crossref and OpenAlex) can be queried for any period, but feeds and listing pages only show recent items. When we first collected, on 31 October, these sources reached back only to September: BIS, ECB, Bank of Canada, Bundesbank, NBB, Banco de España, Norges Bank, Banca d'Italia, and the New York, Atlanta, Chicago and Dallas Feds (through Fed in Print). Their August papers are missing, so the August issue leans more on the journals, NBER and the IMF. Weekly runs keep everything from now on.

### APIs

| API | Use | Limits (checked 31 Oct 2026) |
|---|---|---|
| [Crossref REST API](https://api.crossref.org) | Journals and the IMF (by ISSN), NBER (by DOI prefix) | Polite pool (with `mailto`): 3 requests/second, 3 concurrent |
| [OpenAlex](https://docs.openalex.org) | Abstracts missing from Crossref, looked up by DOI in batches of 50 | Without a key: 10 requests/second and about 1,000 list requests a day, which is plenty. A free key raises the daily budget tenfold. |

**Collection window for Crossref sources:** we filter on the DOI registration date (`from-created-date`), not the publication date. Econometrica deposits year-only dates and AER deposits future issue dates, so a publication-date filter would miss or misdate their papers.

## Journals

All five are paywalled. Method: Crossref by ISSN, with OpenAlex as the fallback for abstracts.

| Source | ISSN | Status | Papers with abstracts (Aug–Oct 2026) | Notes |
|---|---|---|---|---|
| American Economic Review | 0002-8282 | Working | 30 / 30 | |
| Econometrica | 0012-9682 | Working | 12 / 12 | Year-only dates in Crossref, so the registration-date window is essential. Publishes every two months (nothing in October). |
| Journal of Political Economy | 0022-3808 | **Partial** | 4 / 25 | Crossref has no JPE abstracts, and OpenAlex has few for recent papers. The rest are logged and skipped each cycle, and picked up if OpenAlex adds an abstract later. |
| Quarterly Journal of Economics | 0033-5533 | Working | 13 / 13 | |
| Review of Economic Studies | 0034-6527 | Working | 36 / 36 | |

Journal housekeeping items (front matter, editors' reports, "turnaround times" and similar) are filtered out by title.

## NBER, BPEA, IMF and BIS

| Source | Method | Status | Papers with abstracts | Notes |
|---|---|---|---|---|
| NBER Working Papers | Crossref (prefix `10.3386`) + OpenAlex | Working | 388 / 423 | Paywalled. Crossref has dates and authors but no abstracts, so OpenAlex supplies them (the newest papers catch up within days). The RSS feed has abstracts but no dates and only a week of history. |
| Brookings Papers on Economic Activity | HTML | **Partial** | – | Crossref only has the JSTOR archive, and the full BPEA paper list is rendered by JavaScript. We read the "New and Noteworthy" papers on the BPEA page. They carry no dates, so new papers are dated when first seen; the Fall 2026 papers were already listed on our first run and stay undated (not backfilled). Abstracts are Brookings' summary of each paper. |
| IMF Working Papers | Crossref (ISSN `1018-5941`) | Working | 74 / 74 | The old IMF RSS endpoint now returns 404. Crossref has abstracts for all of them. |
| BIS | RSS | Working | 19 / 20 | The "Research papers" feed carries Working Papers, BIS Bulletins and BIS Papers. |

## G10 central banks

| Source | Method | Status | Papers with abstracts | Notes |
|---|---|---|---|---|
| Federal Reserve Board | RSS | Working | 36 / 36 | FEDS, IFDP and FEDS Notes feeds. Series prefixes are stripped from titles. |
| Bank of Canada | RSS | Working | 10 / 10 | Staff working papers, discussion papers and analytical notes |
| Bank of England | RSS + paper page | Working | 15 / 15 | Publications feed filtered to staff working papers. The feed's summaries are teasers, so the abstract comes from each paper's page. |
| Bank of Japan | HTML + paper page | Working | 7 / 7 | The year's list of reports and research papers (`rs_all_{year}`), filtered to Working Papers and the BoJ Review. The "What's new" feed was mostly data releases with no summaries, so we dropped it. |
| Swiss National Bank | RSS | Working | 7 / 7 | Working Papers, Economic Studies, Economic Notes |
| Sveriges Riksbank | HTML | **Partial** | 0 / 6 | No research feed. The working-paper listing gives titles and dates, but links straight to PDFs, so there is no abstract and the papers are logged and skipped. |
| Deutsche Bundesbank | RSS + paper page | Working | 10 / 10 | The Discussion Papers feed has no summaries, so the abstract comes from each paper's page, cut before the non-technical summary that follows it. Authors come from the feed title. |
| Banque de France | HTML + paper page | Working | 11 / 11 | No feed. The working-paper listing is in the page HTML (the general research page is rendered by JavaScript). |
| Banca d'Italia | HTML + paper page | Working | 6 / 6 | Feeds exist under `/util/`, but **robots.txt disallows that path**, so we use the working-paper listing (latest six) with the requested 5-second crawl delay. |
| De Nederlandsche Bank | RSS + paper page | Working | 10 / 10 | Working Papers and Occasional Studies feeds have no summaries, so abstracts come from each paper's page. |
| National Bank of Belgium | RSS + paper page | Working | 3 / 5 | All-publications feed (working papers, Economic Review, projections) |
| European Central Bank | RSS | Working | 17 / 17 | Working Papers and the Research Bulletin. The feeds carry no author names and link straight to PDFs, so ECB papers have no authors. |

## Federal Reserve regional banks

All 12 come through **[Fed in Print](https://www.fedinprint.org)**, the Federal Reserve System's own research catalogue. It has one RSS feed per bank, with abstracts, authors, dates, series names and often DOIs. Speeches, remarks and testimony are filtered out.

| Bank | Status | Papers with abstracts | | Bank | Status | Papers with abstracts |
|---|---|---|---|---|---|---|
| Boston | Working | 8 / 8 | | Chicago | Working | 4 / 4 |
| New York | Working | 20 / 20 | | St. Louis | Working | 20 / 21 |
| Philadelphia | Working | 13 / 13 | | Minneapolis | Working | 8 / 10 |
| Cleveland | Working | 24 / 24 | | Kansas City | Working | 24 / 24 |
| Richmond | Working | 23 / 23 | | Dallas | Working | 18 / 18 |
| Atlanta | Working | 7 / 7 | | San Francisco | Working | 20 / 20 |

**Limitation:** each feed holds the latest 25 items, so history is limited to what the feeds held when we first collected (31 October, back to 1 August). Boston's own research feed stopped updating in 2020, which is one reason we use Fed in Print for every bank.

## European national central banks: first priority

| Source | Method | Status | Notes |
|---|---|---|---|
| Banco de España | RSS + paper page | Working (18 / 18) | Publications feed filtered to Working and Occasional Papers. Abstracts come from each paper's page. |
| Norges Bank | RSS + paper page | Working (4 / 4) | Working Papers and Staff Memo feeds have no summaries, so abstracts come from each paper's page. |
| Magyar Nemzeti Bank | HTML + paper page | **Partial** | The working-paper listing has abstracts on each paper's page but **no publication dates**. New papers are dated when we first see them; the existing back catalogue (100 papers) stays undated and is not screened. |
| Bank of Finland | – | Not covered | Discussion Papers are listed only in the Bank's DSpace repository (`publications.bof.fi`), which sits behind Cloudflare and **returns 403** to our crawler. Its content signals also don't grant AI use. Not in OpenAlex. |
| BOFIT | – | Not covered | Same repository and same 403. This is the largest loss for EM coverage; the IMF and BIS supply most of our EM research instead. |
| Oesterreichische Nationalbank | – | Not covered | No feed, and we couldn't locate a server-rendered working-paper listing. |
| Central Bank of Ireland | – | Not covered | No feed. The Research Technical Papers listing is rendered by JavaScript. |
| Banco de Portugal | – | Not covered | **Returns 403** to our crawler |
| Danmarks Nationalbank | – | Not covered | No feed. The publications list is rendered by JavaScript. |
| Narodowy Bank Polski | – | Not covered | **Returns 403** to our crawler |
| Czech National Bank | – | Not covered | The feeds cover press releases and the cnBlog only, and the working-paper series page is rendered by JavaScript. |

None of the first-priority banks without a feed have their working-paper series in Crossref's journal registry or in OpenAlex (checked for each one), so no API fallback exists.

## European national central banks: rest of the euro area

These are covered only where there's a feed or a simple page, with no more than about 15 minutes per scraper.

| Source | Status | Reason |
|---|---|---|
| Hrvatska narodna banka | Working | HTML listing (month-only dates) with abstracts from each paper's page. Its latest paper is from July, so nothing has been collected since 1 August yet. |
| Bank of Greece | Not covered | **Returns 403** to our crawler |
| Lietuvos bankas | Not covered | **Returns 403** to our crawler |
| Národná banka Slovenska | Not covered | Abstracts appear inline, but the listing has no dates and no per-paper pages |
| Banka Slovenije | Not covered | No research listing separate from the blog |
| Latvijas Banka | Not covered | No feed. The yearly listing pages have no paper links in the HTML. |
| Eesti Pank | Not covered | A JavaScript app; its data is embedded as JSON and would need a custom parser |
| Banque centrale du Luxembourg | Not covered | Its only feed carries press releases, and the working-paper listing isn't in the HTML |
| Central Bank of Malta | Not covered | The listing links straight to PDFs with no abstracts |
| Central Bank of Cyprus | Not covered | No feed and no paper links on the publications page |
| Bulgarian National Bank | Not covered | Feeds are press-office categories in Bulgarian only |

## Fallback strategies

The hiring manager asked for every source that needed a fallback to be documented.

| Source | Problem | Fallback |
|---|---|---|
| All five journals | Crossref often lacks abstracts | OpenAlex abstract lookup by DOI |
| Econometrica, AER | Crossref dates are year-only, or are future issue dates | Collection window on DOI registration date; the published date is the earliest full date given |
| JPE | No Crossref abstracts, and few in OpenAlex | Papers without an abstract are skipped and logged each cycle, and re-checked later |
| NBER | No abstracts in Crossref; RSS has no dates or history | Crossref for discovery and dates, OpenAlex for abstracts |
| IMF | RSS endpoint gone (404) | Crossref by the Working Papers ISSN |
| BPEA | Not in Crossref; paper list rendered by JavaScript | "New and Noteworthy" block on the BPEA page, dated when first seen |
| Fed regional banks | Native feeds inconsistent (Boston's stopped in 2020) | Fed in Print feeds for all 12 |
| Bank of England, Banco de España | Mixed general feeds with teaser summaries | Feed filtered by URL; abstract from each paper's page |
| Bundesbank, DNB, Norges Bank, NBB | Feeds without summaries | Abstract from each paper's page |
| Bank of Japan | "What's new" feed is mostly data releases | The year's research-paper list (HTML), filtered to papers |
| Banca d'Italia | Feed path disallowed by robots.txt | HTML listing with a 5-second crawl delay |
| Banque de France, HNB | No feed | HTML listing; abstract from each paper's page |
| Riksbank | No feed; papers are PDFs only | HTML listing for titles and dates; no abstract, so logged and skipped |
| MNB | No feed; no dates | HTML listing; dated when first seen |
| Banco de Portugal, NBP, Bank of Greece, Lietuvos bankas, BoF/BOFIT repository | 403 to our crawler | None. Documented as not covered. |
