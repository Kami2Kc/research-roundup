"""Evaluate the screening prompt against hand labels in eval/labels.csv.

The current prompt is run on every labelled paper (title and abstract come from the CSV, so the evaluation
doesn't depend on the database), and its market focus is compared with the human label.
"""

import csv
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from roundup.llm import LLM, estimate_cost
from roundup.screening import FOCUSES, PROMPT_VERSION, SYSTEM_PROMPT, ScreeningResult

LABELS = ("EM", "DM", "Transversal")


@dataclass
class EvalReport:
    rows: list[dict] = field(default_factory=list)  # one per labelled paper, with the model's answer
    cost_usd: float = 0.0

    @property
    def agreement(self) -> float:
        return sum(r["label"] == r["predicted"] for r in self.rows) / len(self.rows)

    @property
    def kappa(self) -> float:
        """Cohen's kappa: agreement corrected for what chance alone would give."""
        n = len(self.rows)
        labels, predicted = Counter(r["label"] for r in self.rows), Counter(r["predicted"] for r in self.rows)
        expected = sum(labels[c] * predicted[c] for c in LABELS) / (n * n)
        return (self.agreement - expected) / (1 - expected) if expected < 1 else 1.0

    def confusion(self) -> dict[tuple[str, str], int]:
        return Counter((r["label"], r["predicted"]) for r in self.rows)

    def relevance_mae(self) -> float | None:
        scored = [r for r in self.rows if r["label_relevance"] is not None]
        if not scored:
            return None
        return sum(abs(r["label_relevance"] - r["relevance"]) for r in scored) / len(scored)


def load_labels(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["label_market_focus"].strip()]
    for r in rows:
        r["label_market_focus"] = r["label_market_focus"].strip()
        if r["label_market_focus"] not in FOCUSES:
            raise ValueError(f"{r['paper_id']}: label must be one of {', '.join(FOCUSES)}, got '{r['label_market_focus']}'")
    return rows


def run_eval(llm: LLM, model: str, labels_path: Path, results_path: Path) -> EvalReport:
    report = EvalReport()
    for r in load_labels(labels_path):
        prompt = f"Title: {r['title']}\nSource: {r['source']}\nAbstract: {r['abstract']}"
        result = llm.complete_json(ScreeningResult, prompt, model, system=SYSTEM_PROMPT, max_tokens=2000, effort="low")
        report.cost_usd += estimate_cost(result.model, result.input_tokens, result.output_tokens) or 0.0
        relevance_label = r.get("label_relevance", "").strip()
        report.rows.append({
            "paper_id": r["paper_id"],
            "title": r["title"],
            "label": r["label_market_focus"],
            "predicted": result.data.market_focus,
            "label_relevance": int(relevance_label) if relevance_label else None,
            "relevance": result.data.relevance_score,
            "rationale": result.data.focus_rationale,
        })

    with results_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["paper_id", "title", "label", "predicted", "label_relevance",
                                               "relevance", "rationale", "model", "prompt_version"])
        writer.writeheader()
        for row in report.rows:
            writer.writerow({**row, "model": model, "prompt_version": PROMPT_VERSION})
    return report
