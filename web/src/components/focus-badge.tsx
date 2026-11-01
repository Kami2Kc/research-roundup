import type { MarketFocus } from "@/lib/data";
import { TAG_COLOURS } from "@/lib/tags";

export function FocusBadge({ focus }: { focus: MarketFocus }) {
  const { bg, fg, label } = TAG_COLOURS[focus];
  return (
    <span
      title={label}
      className="px-3 py-1 rounded-lg text-center inline-block text-xs font-semibold tracking-wide"
      style={{ backgroundColor: bg, color: fg }}
    >
      {focus}
    </span>
  );
}
