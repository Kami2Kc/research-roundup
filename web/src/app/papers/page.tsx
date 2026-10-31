import type { Metadata } from "next";
import { PapersExplorer, type PaperRow } from "@/components/papers-explorer";
import { getPapers } from "@/lib/data";

export const metadata: Metadata = { title: "Paper explorer · The Research Roundup" };

export default function PapersPage() {
  const rows: PaperRow[] = getPapers().map((p) => ({
    slug: p.slug,
    title: p.title,
    authors: p.authors.slice(0, 4).join(", ") + (p.authors.length > 4 ? " et al." : ""),
    published_date: p.published_date,
    source_name: p.source_name,
    source_group: p.source_group ?? "",
    market_focus: p.market_focus,
    relevance_score: p.relevance_score,
    topics: p.topics,
    issues: p.issues,
    paywalled: p.paywalled,
  }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Paper explorer</h1>
        <p className="mt-2 max-w-3xl text-muted-foreground">
          Every paper the pipeline has screened, with its market focus and relevance score. Open a paper for its
          abstract and the reasoning behind its classification.
        </p>
      </div>
      <PapersExplorer rows={rows} />
    </div>
  );
}
