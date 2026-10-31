"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  type ColumnDef,
  type ColumnFiltersState,
  type FilterFn,
  type SortingState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { FocusBadge } from "@/components/focus-badge";
import type { MarketFocus } from "@/lib/data";
import { SOURCE_GROUPS, formatDate, formatMonth } from "@/lib/labels";
import { TAG_COLOURS } from "@/lib/tags";

// A slim version of each paper (no abstract), passed from the server page.
export interface PaperRow {
  slug: string;
  title: string;
  authors: string;
  published_date: string;
  source_name: string;
  source_group: string;
  market_focus: MarketFocus;
  relevance_score: number;
  topics: string[];
  issues: string[];
  paywalled: boolean;
}

const FOCUSES: MarketFocus[] = ["EM", "DM", "Transversal"];
const ALL = "all";

// Filter functions for TanStack Table; each receives the column value and the current filter value.
const oneOf: FilterFn<PaperRow> = (row, id, values: string[]) => values.includes(row.getValue<string>(id));
const atLeast: FilterFn<PaperRow> = (row, id, min: number) => row.getValue<number>(id) >= min;
const inDateRange: FilterFn<PaperRow> = (row, id, [from, to]: [string, string]) => {
  const date = row.getValue<string>(id);
  return (!from || date >= from) && (!to || date <= to);
};
const featured: FilterFn<PaperRow> = (row, id) => row.getValue<string[]>(id).length > 0;
const matchesSearch: FilterFn<PaperRow> = (row, _id, query: string) => {
  const p = row.original;
  const haystack = `${p.title} ${p.authors} ${p.source_name} ${p.topics.join(" ")}`.toLowerCase();
  return query.toLowerCase().split(/\s+/).every((word) => haystack.includes(word));
};

function sortIndicator(direction: false | "asc" | "desc") {
  return direction === "asc" ? " ↑" : direction === "desc" ? " ↓" : "";
}

const columns: ColumnDef<PaperRow>[] = [
  {
    accessorKey: "published_date",
    header: "Date",
    cell: ({ getValue }) => <span className="whitespace-nowrap">{formatDate(getValue<string>())}</span>,
    filterFn: inDateRange,
    meta: { className: "w-28" },
  },
  {
    accessorKey: "title",
    header: "Paper",
    cell: ({ row }) => {
      const p = row.original;
      return (
        <div className="min-w-64 max-w-xl whitespace-normal">
          <Link href={`/papers/${p.slug}/`} className="font-medium leading-snug hover:underline">
            {p.title}
          </Link>
          {p.authors && <p className="mt-0.5 text-xs text-muted-foreground">{p.authors}</p>}
          <p className="mt-1 text-xs text-muted-foreground md:hidden">{p.source_name}</p>
          {p.topics.length > 0 && (
            <p className="mt-1 flex flex-wrap gap-1">
              {p.topics.map((t) => (
                <span key={t} className="rounded bg-muted px-1.5 py-0.5 text-[11px] text-muted-foreground">{t}</span>
              ))}
            </p>
          )}
        </div>
      );
    },
  },
  {
    accessorKey: "source_name",
    header: "Source",
    filterFn: "equalsString",
    meta: { className: "hidden md:table-cell" },
    cell: ({ getValue }) => <span className="block max-w-48 whitespace-normal text-sm">{getValue<string>()}</span>,
  },
  { accessorKey: "source_group", filterFn: "equalsString" },
  {
    accessorKey: "market_focus",
    header: "Focus",
    cell: ({ getValue }) => <FocusBadge focus={getValue<MarketFocus>()} />,
    filterFn: oneOf,
  },
  {
    accessorKey: "relevance_score",
    header: "Relevance",
    cell: ({ getValue }) => <span className="tabular-nums">{getValue<number>()}/10</span>,
    filterFn: atLeast,
    sortDescFirst: true,
    meta: { className: "hidden sm:table-cell text-right" },
  },
  {
    accessorKey: "issues",
    header: "Issue",
    enableSorting: false,
    filterFn: featured,
    cell: ({ getValue }) =>
      getValue<string[]>().map((month) => (
        <Link key={month} href={`/issues/${month}/`} className="block whitespace-nowrap text-sm hover:underline">
          {formatMonth(month)}
        </Link>
      )),
    meta: { className: "hidden lg:table-cell" },
  },
];

interface Props {
  rows: PaperRow[];
}

export function PapersExplorer({ rows }: Props) {
  "use no memo"; // TanStack Table's hook returns functions that React Compiler can't memoise safely
  const [search, setSearch] = useState("");
  const [focus, setFocus] = useState<MarketFocus[]>(FOCUSES);
  const [group, setGroup] = useState(ALL);
  const [source, setSource] = useState(ALL);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [minRelevance, setMinRelevance] = useState("0");
  const [onlyFeatured, setOnlyFeatured] = useState(false);
  const [sorting, setSorting] = useState<SortingState>([{ id: "published_date", desc: true }]);

  // The filter controls drive TanStack's column filters; the table does the filtering itself.
  const columnFilters: ColumnFiltersState = useMemo(() => {
    const filters: ColumnFiltersState = [{ id: "market_focus", value: focus }];
    if (group !== ALL) filters.push({ id: "source_group", value: group });
    if (source !== ALL) filters.push({ id: "source_name", value: source });
    if (from || to) filters.push({ id: "published_date", value: [from, to] });
    if (minRelevance !== "0") filters.push({ id: "relevance_score", value: Number(minRelevance) });
    if (onlyFeatured) filters.push({ id: "issues", value: true });
    return filters;
  }, [focus, group, source, from, to, minRelevance, onlyFeatured]);

  // eslint-disable-next-line react-hooks/incompatible-library -- handled by "use no memo" above
  const table = useReactTable({
    data: rows,
    columns,
    state: { sorting, columnFilters, globalFilter: search, columnVisibility: { source_group: false } },
    onSortingChange: setSorting,
    globalFilterFn: matchesSearch,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 25 } },
  });

  const groupItems = [{ value: ALL, label: "All source types" }].concat(
    Object.entries(SOURCE_GROUPS)
      .filter(([key]) => rows.some((r) => r.source_group === key))
      .map(([value, label]) => ({ value, label })),
  );
  const sourceItems = [{ value: ALL, label: "All sources" }].concat(
    [...new Set(rows.filter((r) => group === ALL || r.source_group === group).map((r) => r.source_name))]
      .sort()
      .map((name) => ({ value: name, label: name })),
  );
  const relevanceItems = [{ value: "0", label: "Any relevance" }].concat(
    [5, 6, 7, 8, 9].map((n) => ({ value: String(n), label: `Relevance ${n}+` })),
  );

  function toggleFocus(f: MarketFocus) {
    setFocus((current) => (current.includes(f) ? current.filter((x) => x !== f) : [...current, f]));
  }

  function reset() {
    setSearch("");
    setFocus(FOCUSES);
    setGroup(ALL);
    setSource(ALL);
    setFrom("");
    setTo("");
    setMinRelevance("0");
    setOnlyFeatured(false);
  }

  const filteredCount = table.getFilteredRowModel().rows.length;
  const { pageIndex } = table.getState().pagination;

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 rounded-lg border p-4">
        <Input
          type="search"
          placeholder="Search titles, authors, sources and topics"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search papers"
        />
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-muted-foreground">Market focus:</span>
          {FOCUSES.map((f) => {
            const on = focus.includes(f);
            const { bg, fg } = TAG_COLOURS[f];
            return (
              <button
                key={f}
                type="button"
                aria-pressed={on}
                onClick={() => toggleFocus(f)}
                className="rounded px-2.5 py-1 text-xs font-semibold tracking-wide transition-opacity"
                style={on ? { backgroundColor: bg, color: fg } : { backgroundColor: "transparent", color: fg, opacity: 0.5, outline: `1px dashed ${fg}` }}
              >
                {f}
              </button>
            );
          })}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Select items={groupItems} value={group} onValueChange={(v) => { setGroup(v ?? ALL); setSource(ALL); }}>
            <SelectTrigger className="w-56" aria-label="Source type"><SelectValue /></SelectTrigger>
            <SelectContent>
              {groupItems.map((item) => <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select items={sourceItems} value={source} onValueChange={(v) => setSource(v ?? ALL)}>
            <SelectTrigger className="w-64" aria-label="Source"><SelectValue /></SelectTrigger>
            <SelectContent>
              {sourceItems.map((item) => <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select items={relevanceItems} value={minRelevance} onValueChange={(v) => setMinRelevance(v ?? "0")}>
            <SelectTrigger className="w-40" aria-label="Minimum relevance"><SelectValue /></SelectTrigger>
            <SelectContent>
              {relevanceItems.map((item) => <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
          <label className="flex items-center gap-2">
            From <Input type="date" className="w-40" value={from} onChange={(e) => setFrom(e.target.value)} />
          </label>
          <label className="flex items-center gap-2">
            To <Input type="date" className="w-40" value={to} onChange={(e) => setTo(e.target.value)} />
          </label>
          <label className="flex items-center gap-2">
            <Checkbox checked={onlyFeatured} onCheckedChange={(checked) => setOnlyFeatured(checked)} />
            Featured in an issue
          </label>
          <Button variant="ghost" size="sm" onClick={reset} className="ml-auto">
            Reset filters
          </Button>
        </div>
      </div>

      <p className="text-sm text-muted-foreground" aria-live="polite">
        {filteredCount} of {rows.length} screened papers
      </p>

      <div className="overflow-x-auto rounded-lg border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const className = (header.column.columnDef.meta as { className?: string } | undefined)?.className;
                  return (
                    <TableHead key={header.id} className={className}>
                      {header.column.getCanSort() ? (
                        <button type="button" onClick={header.column.getToggleSortingHandler()} className="font-medium hover:underline">
                          {flexRender(header.column.columnDef.header, header.getContext())}
                          {sortIndicator(header.column.getIsSorted())}
                        </button>
                      ) : (
                        flexRender(header.column.columnDef.header, header.getContext())
                      )}
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.map((row) => (
              <TableRow key={row.id}>
                {row.getVisibleCells().map((cell) => {
                  const className = (cell.column.columnDef.meta as { className?: string } | undefined)?.className;
                  return (
                    <TableCell key={cell.id} className={`align-top ${className ?? ""}`}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
            {filteredCount === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-muted-foreground">
                  No papers match these filters.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {table.getPageCount() > 1 && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            Page {pageIndex + 1} of {table.getPageCount()}
          </span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()}>
              Previous
            </Button>
            <Button variant="outline" size="sm" onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}>
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
