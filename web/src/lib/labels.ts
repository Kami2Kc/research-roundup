// Pure labels and formatters, safe to use in client components (data.ts reads files at build time).

// Order and labels for source groups, used across the dashboard.
export const SOURCE_GROUPS: Record<string, string> = {
  journal: "Journals",
  nber: "NBER",
  bpea: "Brookings (BPEA)",
  intl_org: "IMF and BIS",
  g10_cb: "G10 central banks",
  fed_regional: "Regional Federal Reserve Banks",
  european_ncb: "European central banks",
};

export function formatMonth(month: string): string {
  const [year, m] = month.split("-").map(Number);
  return new Date(Date.UTC(year, m - 1, 1)).toLocaleDateString("en-GB", { month: "long", year: "numeric", timeZone: "UTC" });
}

export function formatDate(isoDate: string): string {
  return new Date(`${isoDate}T00:00:00Z`).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
}
