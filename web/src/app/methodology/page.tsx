import type { Metadata } from "next";
import { FocusBadge } from "@/components/focus-badge";

export const metadata: Metadata = {
  title: "Methodology · The Research Roundup",
};

const REPO = "https://github.com/Kami2Kc/research-roundup";

// Evaluation of screen-v3 on 25 hand-labelled papers (eval/results.csv): rows are labels, columns the model.
const FOCUS_ORDER = ["EM", "DM", "Transversal"] as const;
const CONFUSION = [
  [7, 0, 0],
  [0, 8, 1],
  [1, 1, 7],
];

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
          market focus) and chooses five to eight, skipping any paper whose
          abstract sets out a question without reporting findings. The code
          checks the selection against the house rules: a balance of EM, DM and
          Transversal papers, no more than two papers from one source or on one
          main topic, and length limits on every summary. Anything that breaks
          a rule goes back to the editor to revise. The editor&apos;s reasoning
          is published with each issue.
        </p>
        <p>
          Summaries are based on abstracts only, and the newsletter says so for
          paywalled papers. Always check the original paper before citing it.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">How accurate is the screening?</h2>
        <p>
          We labelled 25 October papers by hand, without seeing the
          model&apos;s answers, spread across EM, DM and Transversal and six
          source types. On market focus the model agreed with the label on{" "}
          <strong>22 of 25 papers (88%)</strong>, a Cohen&apos;s kappa of{" "}
          <strong>0.82</strong> (agreement corrected for chance). With 25
          papers the 95% confidence interval for agreement is roughly 70% to
          96%.
        </p>
        <div className="overflow-x-auto">
          <table className="text-sm tabular-nums">
            <caption className="mb-2 text-left text-muted-foreground">
              Hand label (rows) against the model&apos;s answer (columns),
              prompt screen-v3
            </caption>
            <thead>
              <tr className="border-b">
                <th className="py-1.5 pr-6 text-left font-medium">Label</th>
                {FOCUS_ORDER.map((f) => (
                  <th key={f} className="px-4 py-1.5 text-right font-medium">
                    {f}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {FOCUS_ORDER.map((label, i) => (
                <tr key={label} className="border-b last:border-b-0">
                  <th className="py-1.5 pr-6 text-left font-medium">{label}</th>
                  {CONFUSION[i].map((n, j) => (
                    <td
                      key={FOCUS_ORDER[j]}
                      className={`px-4 py-1.5 text-right ${i === j ? "font-semibold" : n ? "text-red-700" : "text-muted-foreground"}`}
                    >
                      {n}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p>
          The model never confused EM with DM. All three disagreements sit on
          the boundary with Transversal, such as a theory paper about a generic
          currency union that the model tagged EM. We have not tuned the prompt
          on these 25 papers, since that would inflate the figure; the{" "}
          <a
            href={`${REPO}/blob/main/docs/METHODOLOGY.md#evaluation`}
            className="underline"
          >
            full evaluation
          </a>{" "}
          discusses each case.
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
