import Link from "next/link";
import { notFound } from "next/navigation";
import { ChevronDownIcon } from "lucide-react";
import { IssueFrame } from "@/components/issue-frame";
import { formatMonth, getIssues, newsletterUrl } from "@/lib/data";

// Native <details> toggles: no client JavaScript, and they work in the static export.
const SUMMARY =
  "flex cursor-pointer list-none items-center gap-1 font-medium text-muted-foreground hover:text-foreground [&::-webkit-details-marker]:hidden";
const CHEVRON = "size-4 shrink-0 transition-transform";

export function generateStaticParams() {
  return getIssues().map((issue) => ({ month: issue.month }));
}

export async function generateMetadata({
  params,
}: PageProps<"/issues/[month]">) {
  const { month } = await params;
  return { title: `${formatMonth(month)} · The Research Roundup` };
}

export default async function IssuePage({
  params,
}: PageProps<"/issues/[month]">) {
  const { month } = await params;
  const issue = getIssues().find((i) => i.month === month);
  if (!issue) notFound();

  return (
    <div className="space-y-8">
      <div>
        <Link
          href="/"
          className="text-sm text-muted-foreground hover:underline"
        >
          Back to all issues
        </Link>
        <h1 className="mt-2 font-serif text-3xl font-semibold tracking-tight">
          {formatMonth(issue.month)}
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          {issue.papers.length} papers chosen from {issue.pool_size} candidates
          · {issue.papers_screened} papers screened ·{" "}
          <a href={newsletterUrl(issue.month)} className="hover:underline">
            Open the email version
          </a>
        </p>
      </div>

      <div className="grid gap-8 grid-cols-3">
        <IssueFrame
          src={newsletterUrl(issue.month)}
          title={`The Research Roundup, ${formatMonth(issue.month)}`}
        />
        {/* Sticks beside the newsletter on wide screens; top-20 clears the sticky navbar. */}
        <aside className="space-y-6 lg:sticky lg:top-20 lg:self-start lg:overflow-y-auto">
          <section className="group/rationale">
            <h2 className="mb-2 text-lg font-semibold">How the editor chose</h2>
            {/* Clamped until the toggle below is opened; screen readers get the full text either way. */}
            <p className="line-clamp-4 text-sm leading-relaxed group-has-[details[open]]/rationale:line-clamp-none">
              {issue.selection_rationale}
            </p>
            <details className="group/toggle mt-1 text-sm">
              <summary className={SUMMARY}>
                <span className="group-open/toggle:hidden">
                  Read the full reasoning
                </span>
                <span className="hidden group-open/toggle:inline">
                  Show less
                </span>
                <ChevronDownIcon
                  className={`${CHEVRON} group-open/toggle:rotate-180`}
                />
              </summary>
            </details>
          </section>
          <details className="group/papers border-t pt-4">
            <summary className={`${SUMMARY} justify-between`}>
              <h2 className="text-lg font-semibold text-foreground">
                Why each paper was chosen
              </h2>
              <ChevronDownIcon
                className={`${CHEVRON} group-open/papers:rotate-180`}
              />
            </summary>
            <ol className="mt-3 list-decimal space-y-3 pl-5 text-sm marker:text-muted-foreground">
              {issue.papers.map((ref) => (
                <li key={ref.slug}>
                  <Link
                    href={`/papers/${ref.slug}/`}
                    className="font-medium leading-snug hover:underline"
                  >
                    {ref.headline}
                  </Link>
                  <p className="mt-0.5 leading-relaxed text-muted-foreground">
                    {ref.selection_reason}
                  </p>
                </li>
              ))}
            </ol>
          </details>
        </aside>
      </div>
    </div>
  );
}
