import Link from "next/link";
import { notFound } from "next/navigation";
import { FocusBadge } from "@/components/focus-badge";
import { SOURCE_GROUPS, formatDate, formatMonth, getFeatures, getPapers, getPapersBySlug } from "@/lib/data";

export function generateStaticParams() {
  return getPapers().map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({ params }: PageProps<"/papers/[slug]">) {
  const { slug } = await params;
  const paper = getPapersBySlug().get(slug);
  return { title: paper ? `${paper.title} · The Research Roundup` : "Paper not found" };
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</dt>
      <dd className="mt-1 text-sm">{children}</dd>
    </div>
  );
}

export default async function PaperPage({ params }: PageProps<"/papers/[slug]">) {
  const { slug } = await params;
  const paper = getPapersBySlug().get(slug);
  if (!paper) notFound();
  const features = getFeatures(slug);
  const doi = paper.id.startsWith("10.") ? paper.id : null;

  return (
    <article className="space-y-8">
      <div>
        <Link href="/papers/" className="text-sm text-muted-foreground hover:underline">
          ← Paper explorer
        </Link>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <FocusBadge focus={paper.market_focus} />
          <span>{paper.source_name}</span>
          <span>·</span>
          <span>{formatDate(paper.published_date)}</span>
          {paper.paywalled && <span className="rounded border px-1.5 py-0.5 text-xs">Paywalled: abstract only</span>}
        </div>
        <h1 className="mt-2 max-w-4xl text-2xl font-semibold leading-tight tracking-tight sm:text-3xl">{paper.title}</h1>
        {paper.authors.length > 0 && <p className="mt-2 text-muted-foreground">{paper.authors.join(", ")}</p>}
        <a
          href={paper.url}
          className="mt-4 inline-block rounded-md bg-foreground px-4 py-2 text-sm font-medium text-background"
        >
          Read the paper ↗
        </a>
      </div>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-8">
          <section>
            <h2 className="mb-2 text-lg font-semibold">Abstract</h2>
            <p className="leading-relaxed">{paper.abstract}</p>
          </section>

          {features.map(({ issue, entry }) => (
            <section key={issue.month} className="rounded-lg border p-5">
              <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Featured in{" "}
                <Link href={`/issues/${issue.month}/`} className="underline">
                  {formatMonth(issue.month)}
                </Link>
              </p>
              <h2 className="mt-2 text-lg font-semibold">{entry.headline}</h2>
              <p className="mt-2 leading-relaxed">{entry.summary}</p>
              <ul className="mt-3 list-disc space-y-1 pl-5 text-sm">
                {entry.takeaways.map((t) => <li key={t}>{t}</li>)}
              </ul>
              <p className="mt-3 text-sm">
                <span className="font-medium">Why it matters for markets.</span> {entry.why_it_matters}
              </p>
              <p className="mt-3 text-sm text-muted-foreground">
                <span className="font-medium">Why the editor chose it:</span> {entry.selection_reason}
              </p>
            </section>
          ))}
        </div>

        <aside>
          <dl className="space-y-4 rounded-lg border p-5">
            <Field label="Market focus">
              <FocusBadge focus={paper.market_focus} />
              <p className="mt-2 leading-relaxed">{paper.focus_rationale}</p>
            </Field>
            <Field label="Relevance to Global Markets">
              <div className="flex items-center gap-2">
                <div className="h-2 w-32 overflow-hidden rounded bg-muted">
                  <div className="h-full bg-foreground" style={{ width: `${paper.relevance_score * 10}%` }} />
                </div>
                <span className="tabular-nums">{paper.relevance_score}/10</span>
              </div>
            </Field>
            <Field label="Topics">{paper.topics.join(", ") || "–"}</Field>
            <Field label="Regions">{paper.regions.join(", ") || "None in particular"}</Field>
            <Field label="Source">
              <Link href="/sources/" className="hover:underline">
                {paper.source_name}
              </Link>
              {paper.source_group && <span className="text-muted-foreground"> · {SOURCE_GROUPS[paper.source_group]}</span>}
            </Field>
            {doi && <Field label="DOI"><a href={`https://doi.org/${doi}`} className="break-all hover:underline">{doi}</a></Field>}
            <Field label="Classified by">
              <span className="text-muted-foreground">
                {paper.model}, prompt {paper.prompt_version}
              </span>
            </Field>
          </dl>
        </aside>
      </div>
    </article>
  );
}
