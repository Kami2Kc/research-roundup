import Link from "next/link";
import { IssuePaperList } from "@/components/issue-paper-list";
import { formatMonth, getIssues, getPapersBySlug } from "@/lib/data";

export default function Home() {
  const issues = getIssues();
  const [latest, ...past] = issues;

  if (!latest) {
    return (
      <p className="text-muted-foreground">
        No issues yet. Run the pipeline (<code>roundup build-issue</code>, then <code>roundup export</code>) to publish one.
      </p>
    );
  }

  return (
    <div className="space-y-10">
      <section>
        <p className="text-sm uppercase tracking-wider text-muted-foreground">Latest issue</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight">{formatMonth(latest.month)}</h1>
        <p className="mt-4 max-w-3xl leading-relaxed">{latest.editor_note}</p>
        <p className="mt-2 text-sm text-muted-foreground">
          {latest.papers.length} papers chosen from {latest.pool_size} candidates; {latest.papers_screened} papers
          screened this month.
        </p>
        <Link
          href={`/issues/${latest.month}/`}
          className="mt-4 inline-block rounded-md bg-foreground px-4 py-2 text-sm font-medium text-background"
        >
          Read the newsletter
        </Link>
      </section>

      <section>
        <h2 className="mb-4 text-xl font-semibold">In this issue</h2>
        <IssuePaperList issue={latest} papers={getPapersBySlug()} />
      </section>

      {past.length > 0 && (
        <section>
          <h2 className="mb-4 text-xl font-semibold">Past issues</h2>
          <ul className="space-y-2">
            {past.map((issue) => (
              <li key={issue.month}>
                <Link href={`/issues/${issue.month}/`} className="hover:underline">
                  {formatMonth(issue.month)}
                </Link>
                <span className="text-sm text-muted-foreground"> · {issue.papers.length} papers</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
