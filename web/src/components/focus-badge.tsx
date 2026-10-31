import type { MarketFocus } from "@/lib/data";
import { TAG_COLOURS } from "@/lib/tags";

export function FocusBadge({ focus }: { focus: MarketFocus }) {
  const { bg, fg, label } = TAG_COLOURS[focus];
  return (
    <span
      title={label}
      className="inline-block rounded px-2 py-0.5 text-xs font-semibold tracking-wide"
      style={{ backgroundColor: bg, color: fg }}
    >
      {focus}
    </span>
  );
}
