import React from "react";
import { formatDate, getMeta } from "@/lib/data";

const Footer = () => {
  const meta = getMeta();
  return (
    <footer className="bg-[#0b2545]">
      <div className="mx-auto flex w-full max-w-6xl flex-wrap justify-between gap-2 px-4 py-6 text-xs text-white">
        <span>
          New economics research for Global Markets, screened and summarised
          automatically from titles and abstracts.
        </span>
        {meta && (
          <span>
            {meta.papers_screened} papers screened from {meta.sources_enabled}{" "}
            active sources ({meta.sources_total} tracked) · data updated{" "}
            {formatDate(meta.generated_at.slice(0, 10))}
          </span>
        )}
      </div>
    </footer>
  );
};

export default Footer;
