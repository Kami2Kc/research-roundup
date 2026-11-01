import type { Metadata } from "next";
import { FocusBadge } from "@/components/focus-badge";

export const metadata: Metadata = {
  title: "Methodology · The Research Roundup",
};

const REPO = "https://github.com/Kami2Kc/research-roundup";

export default function MethodologyPage() {
  return (
    <div className="max-w-3xl space-y-8 leading-relaxed">
      <div>
        <h1 className="font-serif text-3xl font-semibold tracking-tight">
          How it works
        </h1>
        <p className="mt-2 text-muted-foreground">
          A short version of the methodology. The full document, including the
          exact prompts, is{" "}
          <a
            href={`${REPO}/blob/main/docs/METHODOLOGY.md`}
            className="underline"
          >
            in the repository
          </a>
          .
        </p>
      </div>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Every week</h2>
        <p>
          The pipeline collects new papers from the top five economics journals,
          G10 and European central banks, the twelve regional Federal Reserve
          Banks, NBER, Brookings, the IMF and the BIS, using APIs (Crossref,
          OpenAlex), RSS feeds and, where neither exists, the institution&apos;s
          own listing pages. It respects robots.txt, limits its request rate and
          never bypasses a paywall: for journals and NBER it uses titles and
          abstracts only.
        </p>
        <p>
          A language model (Claude Haiku 5.5) reads each new title and abstract
          and returns a relevance score from 0 to 10, a market focus with a
          short rationale, topics and regions. Papers without a usable abstract
          are logged and skipped. A paper is never re-screened.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Market focus</h2>
        <ul className="space-y-2">
          <li className="flex items-center gap-3">
            <span className="w-24 flex justify-center shrink-0">
              <FocusBadge focus="DM" />
            </span>
            <span>
              Mainly about advanced economies: the US, the euro area (including
              its periphery), the UK, Japan, Canada, Switzerland, the Nordics,
              Australia and New Zealand.
            </span>
          </li>
          <li className="flex items-center gap-3">
            <span className="w-24 flex justify-center shrink-0">
              <FocusBadge focus="EM" />
            </span>
            <span>
              Mainly about emerging or developing economies: China, India,
              Brazil, Mexico, Turkey, South Africa, the Gulf, and Central and
              Eastern Europe outside the euro area.
            </span>
          </li>
          <li className="flex items-center gap-3">
            <span className="w-24 flex justify-center shrink-0">
              <FocusBadge focus="Transversal" />
            </span>
            <span>
              Covers both groups, or is global, cross-country, theoretical or
              methodological.
            </span>
          </li>
        </ul>
        <p className="text-xs text-muted-foreground">
          The tag follows the economies a paper studies, not the institution
          that published it.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Every month</h2>
        <p>
          An AI editor (Claude Sonnet 5.5) reviews up to 40 of the month&apos;s
          strongest papers (relevance 6 or more, with places reserved for each
          market focus) and chooses five to eight. The code checks the selection
          against the house rules: a balance of EM, DM and Transversal papers,
          no more than two papers from one source or on one main topic, and
          length limits on every summary. Anything that breaks a rule goes back
          to the editor to revise. The editor&apos;s reasoning is published with
          each issue.
        </p>
        <p>
          Summaries are based on abstracts only, and the newsletter says so for
          paywalled papers. Always check the original paper before citing it.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Source code and data</h2>
        <p>
          Everything is open: the{" "}
          <a href={REPO} className="underline">
            pipeline and dashboard code
          </a>
          , the{" "}
          <a href={`${REPO}/blob/main/docs/SOURCES.md`} className="underline">
            source inventory and fallbacks
          </a>
          , and the SQLite database the dashboard is built from.
        </p>
      </section>
    </div>
  );
}
