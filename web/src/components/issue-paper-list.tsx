import Link from "next/link";
import type { Issue, Paper } from "@/lib/data";
import { formatDate } from "@/lib/data";
import { FocusBadge } from "./focus-badge";

// The papers chosen for an issue, in issue order, with their metadata.
export function IssuePaperList({ issue, papers }: { issue: Issue; papers: Map<string, Paper> }) {
  return (
    <ol className="space-y-4">
      {issue.papers.map((ref) => {
        const paper = papers.get(ref.slug);
        return (
          <li key={ref.slug} className="rounded-lg border p-4">
            <div className="mb-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <FocusBadge focus={ref.market_focus} />
              {paper && (
                <span>
                  {paper.source_name} · {formatDate(paper.published_date)} · relevance {paper.relevance_score}/10
                </span>
              )}
            </div>
            <Link href={`/papers/${ref.slug}/`} className="font-semibold leading-snug hover:underline">
              {ref.headline}
            </Link>
            {paper && (
              <a href={paper.url} className="mt-1 block text-sm text-muted-foreground hover:underline">
                {paper.title} ↗
              </a>
            )}
            <p className="mt-2 text-sm">
              <span className="font-medium">Why it was chosen:</span> {ref.selection_reason}
            </p>
          </li>
        );
      })}
    </ol>
  );
}
