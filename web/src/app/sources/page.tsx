import type { Metadata } from "next";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { SOURCE_GROUPS, formatDate, getSources, type SourceStatus } from "@/lib/data";

export const metadata: Metadata = { title: "Sources and coverage · The Research Roundup" };

const STATUS_STYLES: Record<SourceStatus, string> = {
  working: "bg-emerald-50 text-emerald-800 border-emerald-200",
  partial: "bg-amber-50 text-amber-800 border-amber-200",
  failing: "bg-red-50 text-red-800 border-red-200",
  "not run": "bg-slate-50 text-slate-700 border-slate-200",
  "not covered": "bg-slate-50 text-slate-500 border-slate-200",
};

const METHOD_LABELS: Record<string, string> = {
  crossref: "Crossref API",
  openalex: "OpenAlex API",
  rss: "RSS feed",
  html: "Web page",
  none: "–",
};

function StatusBadge({ status }: { status: SourceStatus }) {
  return <span className={`inline-block whitespace-nowrap rounded border px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[status]}`}>{status}</span>;
}

export default function SourcesPage() {
  const sources = getSources();
  const counts = sources.reduce<Record<string, number>>((acc, s) => ({ ...acc, [s.status]: (acc[s.status] ?? 0) + 1 }), {});

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Sources and coverage</h1>
        <p className="mt-2 max-w-3xl text-muted-foreground">
          Every source the pipeline monitors, how it is collected and how the latest run went. A source is{" "}
          <em>partial</em> when most of its papers have no usable abstract (they are logged and skipped) or it
          cannot be dated reliably; <em>not covered</em> sources are explained in the notes.
        </p>
        <div className="mt-4 flex flex-wrap gap-3 text-sm">
          {(["working", "partial", "failing", "not covered"] as SourceStatus[])
            .filter((s) => counts[s])
            .map((s) => (
              <span key={s} className="flex items-center gap-2">
                <StatusBadge status={s} /> {counts[s]}
              </span>
            ))}
        </div>
      </div>

      {Object.entries(SOURCE_GROUPS).map(([group, label]) => {
        const rows = sources.filter((s) => s.group === group);
        if (rows.length === 0) return null;
        return (
          <section key={group}>
            <h2 className="mb-3 text-xl font-semibold">{label}</h2>
            <div className="overflow-x-auto rounded-lg border">
              <Table className="table-fixed min-w-[640px]">
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[30%]">Source</TableHead>
                    <TableHead className="w-28">Status</TableHead>
                    <TableHead className="hidden w-44 md:table-cell">Method</TableHead>
                    <TableHead className="w-20 text-right">Papers</TableHead>
                    <TableHead className="hidden w-28 sm:table-cell">Last run</TableHead>
                    <TableHead className="hidden lg:table-cell">Notes</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((s) => (
                    <TableRow key={s.id}>
                      <TableCell className="align-top">
                        <div className="whitespace-normal font-medium">{s.url ? <a href={s.url} className="hover:underline">{s.name}</a> : s.name}</div>
                        <div className="text-xs text-muted-foreground">
                          {s.country_or_region}
                          {s.paywalled && " · paywalled"}
                        </div>
                      </TableCell>
                      <TableCell className="align-top"><StatusBadge status={s.status} /></TableCell>
                      <TableCell className="hidden whitespace-normal align-top text-sm md:table-cell">
                        {METHOD_LABELS[s.method] ?? s.method}
                        {s.fallback && <span className="text-muted-foreground"> + {METHOD_LABELS[s.fallback] ?? s.fallback}</span>}
                      </TableCell>
                      <TableCell className="align-top text-right text-sm tabular-nums">
                        {s.paper_count > 0 ? (
                          <span title="Papers with a usable abstract / papers collected">
                            {s.papers_with_abstract}/{s.paper_count}
                          </span>
                        ) : (
                          "–"
                        )}
                      </TableCell>
                      <TableCell className="hidden align-top text-sm sm:table-cell">
                        {s.last_run ? (
                          <span className={s.last_run.status === "ok" ? "" : "text-red-700"}>
                            {formatDate(s.last_run.started_at.slice(0, 10))}
                            {s.last_run.status !== "ok" && ` · ${s.last_run.error}`}
                          </span>
                        ) : (
                          "–"
                        )}
                      </TableCell>
                      <TableCell className="hidden max-w-md align-top text-xs leading-relaxed text-muted-foreground whitespace-normal lg:table-cell">
                        {s.notes}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </section>
        );
      })}
    </div>
  );
}
