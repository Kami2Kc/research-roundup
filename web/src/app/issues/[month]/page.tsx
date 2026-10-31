import Link from "next/link";
import { notFound } from "next/navigation";
import { IssueFrame } from "@/components/issue-frame";
import { IssuePaperList } from "@/components/issue-paper-list";
import { formatMonth, getIssues, getPapersBySlug } from "@/lib/data";

export function generateStaticParams() {
  return getIssues().map((issue) => ({ month: issue.month }));
}

export async function generateMetadata({ params }: PageProps<"/issues/[month]">) {
  const { month } = await params;
  return { title: `${formatMonth(month)} · The Research Roundup` };
}

export default async function IssuePage({ params }: PageProps<"/issues/[month]">) {
  const { month } = await params;
  const issue = getIssues().find((i) => i.month === month);
  if (!issue) notFound();

  return (
    <div className="space-y-8">
      <div>
        <Link href="/" className="text-sm text-muted-foreground hover:underline">
          ← All issues
        </Link>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">{formatMonth(issue.month)}</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          {issue.papers.length} papers chosen from {issue.pool_size} candidates · {issue.papers_screened} papers
          screened ·{" "}
          <a href={issue.newsletter} className="hover:underline">
            Open the email version
          </a>
        </p>
      </div>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,640px)_1fr]">
        <IssueFrame src={issue.newsletter} title={`The Research Roundup, ${formatMonth(issue.month)}`} />
        <aside className="space-y-6">
          <section>
            <h2 className="mb-2 text-lg font-semibold">How the editor chose</h2>
            <p className="text-sm leading-relaxed">{issue.selection_rationale}</p>
          </section>
          <section>
            <h2 className="mb-3 text-lg font-semibold">Papers in this issue</h2>
            <IssuePaperList issue={issue} papers={getPapersBySlug()} />
          </section>
        </aside>
      </div>
    </div>
  );
}
