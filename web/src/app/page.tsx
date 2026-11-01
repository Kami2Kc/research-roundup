import Link from "next/link";
import { FocusBadge } from "@/components/focus-badge";
import { type Issue, formatMonth, getIssues } from "@/lib/data";

// One issue on the home page: the editor's note beside the list of headlines.
// The latest issue is a highlighted card; past issues sit one heading level lower under "Past issues".
function IssueSection({ issue, latest }: { issue: Issue; latest: boolean }) {
  const href = `/issues/${issue.month}/`;
  const listId = `papers-${issue.month}`;
  const MonthHeading = latest ? "h2" : "h3";
  const ListHeading = latest ? "h3" : "h4";
  return (
    <section
      className={
        latest
          ? "rounded-xl border border-l-4 border-l-[#0b2545] bg-[#0b2545]/4 p-6 lg:p-8"
          : "border-b py-4"
      }
    >
      <div className="grid gap-6 lg:grid-cols-5 lg:gap-10">
        <div className="space-y-4 lg:col-span-3">
          <div>
            {latest && (
              <p className="text-sm font-semibold uppercase tracking-wider text-[#0b2545]">
                Latest issue
              </p>
            )}
            <MonthHeading
              className={`flex items-center gap-2 mt-1 font-serif font-semibold tracking-tight ${latest ? "text-3xl" : "text-xl"}`}
            >
              <Link href={href} className="hover:underline">
                {formatMonth(issue.month)}
              </Link>
            </MonthHeading>
          </div>
          <p className="leading-relaxed">{issue.editor_note}</p>
          <p className="mt-3 text-sm text-muted-foreground">
            {issue.papers.length} papers chosen from {issue.pool_size}{" "}
            candidates; {issue.papers_screened} papers screened that month.
          </p>
          <Link
            href={href}
            className={`inline-block px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              latest
                ? "bg-[#0b2545] text-white hover:bg-[#103562]"
                : "border border-[#0b2545] text-[#0b2545] hover:bg-[#0b2545]/5"
            }`}
          >
            Read the newsletter
          </Link>
        </div>
        <div className="lg:col-span-2">
          <ListHeading
            id={listId}
            className="mb-3 font-serif text-lg font-semibold"
          >
            Papers included in this issue
          </ListHeading>
          <ol className="space-y-3" aria-labelledby={listId}>
            {issue.papers.map((ref) => (
              <li key={ref.slug} className="flex gap-3">
                <Link
                  href={`/papers/${ref.slug}/`}
                  className="flex-1 text-sm font-medium leading-snug hover:underline"
                >
                  {ref.headline}
                </Link>
                <span className="w-28 shrink-0">
                  <FocusBadge focus={ref.market_focus} />
                </span>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}

export default function Home() {
  const [latest, ...past] = getIssues(); // newest first

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-serif text-3xl font-semibold tracking-tight">
          Monthly issues
        </h1>
        <p className="mt-2 max-w-3xl text-muted-foreground">
          Each month an AI editor picks five to eight papers from the new
          economics research screened that month and explains why they matter
          for Global Markets. Newest first; you can also{" "}
          <Link href="/papers/" className="underline">
            explore every screened paper
          </Link>
          .
        </p>
      </div>

      {!latest ? (
        <p className="text-muted-foreground">
          No issues yet. Run the pipeline (<code>roundup build-issue</code>,
          then <code>roundup export</code>) to publish one.
        </p>
      ) : (
        <IssueSection issue={latest} latest />
      )}

      {past.length > 0 && (
        <section className="flex flex-col gap-4">
          <h2 className="font-serif text-2xl font-semibold tracking-tight">
            Past issues
          </h2>
          {past.map((issue) => (
            <IssueSection key={issue.month} issue={issue} latest={false} />
          ))}
        </section>
      )}
    </div>
  );
}
