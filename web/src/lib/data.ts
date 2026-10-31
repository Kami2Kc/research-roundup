// Build-time loaders for the JSON the pipeline writes into public/data/ (see pipeline/src/roundup/export.py).
// They run during `next build` only; the exported site is fully static.
import fs from "node:fs";
import path from "node:path";

export { SOURCE_GROUPS, formatDate, formatMonth } from "./labels";

export type MarketFocus = "EM" | "DM" | "Transversal";

export interface IssuePaperRef {
  slug: string;
  position: number;
  headline: string;
  selection_reason: string;
  market_focus: MarketFocus;
  focus_rationale: string;
  summary: string;
  takeaways: string[];
  why_it_matters: string;
}

export interface Issue {
  month: string; // YYYY-MM
  editor_note: string;
  selection_rationale: string;
  newsletter: string; // path under public/
  pool_size: number;
  papers_screened: number;
  built_at: string;
  papers: IssuePaperRef[];
}

export interface Paper {
  id: string;
  slug: string;
  title: string;
  authors: string[];
  abstract: string;
  url: string;
  published_date: string;
  paywalled: boolean;
  source_id: string;
  source_name: string;
  source_group: string | null;
  relevance_score: number;
  market_focus: MarketFocus;
  focus_rationale: string;
  topics: string[];
  regions: string[];
  model: string;
  prompt_version: string;
  issues: string[];
}

export type SourceStatus = "working" | "partial" | "failing" | "not run" | "not covered";

export interface SourceRow {
  id: string;
  name: string;
  group: string;
  country_or_region: string;
  method: string;
  fallback: string | null;
  paywalled: boolean;
  enabled: boolean;
  url: string | null;
  notes: string;
  status: SourceStatus;
  paper_count: number;
  papers_with_abstract: number;
  last_success: string | null;
  last_run: {
    started_at: string;
    status: string;
    items_found: number;
    items_new: number;
    error: string | null;
    duration_s: number;
  } | null;
}

export interface Meta {
  generated_at: string;
  papers_collected: number;
  papers_screened: number;
  sources_enabled: number;
  sources_total: number;
}

function readJson<T>(name: string, fallback: T): T {
  const file = path.join(process.cwd(), "public", "data", `${name}.json`);
  return fs.existsSync(file) ? (JSON.parse(fs.readFileSync(file, "utf-8")) as T) : fallback;
}

export function getIssues(): Issue[] {
  return readJson<Issue[]>("issues", []); // newest first
}

export function getPapers(): Paper[] {
  return readJson<Paper[]>("papers", []);
}

export function getPapersBySlug(): Map<string, Paper> {
  return new Map(getPapers().map((p) => [p.slug, p]));
}

export function getSources(): SourceRow[] {
  return readJson<SourceRow[]>("sources", []);
}

export function getMeta(): Meta | null {
  return readJson<Meta | null>("meta", null);
}

/**
 * Where a newsletter is served. Vercel serves .html files from public/ only at clean URLs
 * (/newsletters/2026-10/) and returns 404 for the .html path, so builds on Vercel link there;
 * every other host (next dev, GitHub Pages, any static server) serves the file itself.
 */
export function newsletterUrl(month: string): string {
  return process.env.VERCEL ? `/newsletters/${month}/` : `/newsletters/${month}.html`;
}

/** The issue write-ups that featured a paper, newest issue first. */
export function getFeatures(slug: string): { issue: Issue; entry: IssuePaperRef }[] {
  return getIssues().flatMap((issue) =>
    issue.papers.filter((entry) => entry.slug === slug).map((entry) => ({ issue, entry })),
  );
}
