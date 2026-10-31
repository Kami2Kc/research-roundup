import type { MarketFocus } from "./data";

// Same colours as the newsletter (pipeline/src/roundup/newsletter.py): each tag always looks the same.
export const TAG_COLOURS: Record<MarketFocus, { bg: string; fg: string; label: string }> = {
  EM: { bg: "#fef3c7", fg: "#92400e", label: "Emerging markets" },
  DM: { bg: "#dbeafe", fg: "#1e40af", label: "Developed markets" },
  Transversal: { bg: "#ede9fe", fg: "#5b21b6", label: "Global, cross-country or methodological" },
};
