// Build-time loaders for the JSON the pipeline writes into public/data/ (see pipeline/src/roundup/export.py).
// They run during `next build` only; the exported site is fully static.
import fs from "node:fs";
import path from "node:path";

export type MarketFocus = "EM" | "DM" | "Transversal";

export interface IssuePaperRef {
  slug: string;
  position: number;
  headline: string;
  selection_reason: string;
  market_focus: MarketFocus;
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

export function formatMonth(month: string): string {
  const [year, m] = month.split("-").map(Number);
  return new Date(Date.UTC(year, m - 1, 1)).toLocaleDateString("en-GB", { month: "long", year: "numeric", timeZone: "UTC" });
}

export function formatDate(isoDate: string): string {
  return new Date(`${isoDate}T00:00:00Z`).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
}
