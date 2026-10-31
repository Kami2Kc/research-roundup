# Evaluation set

`labels.csv` holds 25 October 2026 papers labelled by hand. **Latest result:** 22/25 agreement (88%), Cohen's kappa 0.82, with prompt `screen-v3` (details in [docs/METHODOLOGY.md](../docs/METHODOLOGY.md#evaluation), per-paper results in `results.csv`). `roundup eval` runs the current screening prompt on them and reports how often the model's market focus matches the label (with a confusion matrix and Cohen's kappa). The result goes in [docs/METHODOLOGY.md](../docs/METHODOLOGY.md).

## How the papers were chosen

Twenty-five screened October papers, stratified by the model's earlier prediction (8 EM, 8 DM, 9 Transversal) so every class is tested. No source contributes more than three papers, and the set spans journals, NBER, the IMF and BIS, G10 central banks, regional Feds and European central banks. The model's predictions are deliberately not in the file, so labels are blind.

## Labelling

Fill in two columns for each row:

- `label_market_focus` (required): `EM`, `DM` or `Transversal`.
  - **DM:** mainly about advanced economies (US, euro area including the periphery, UK, Japan, Canada, Switzerland, the Nordics, Australia, New Zealand).
  - **EM:** mainly about emerging or developing economies (China, India, Brazil, Mexico, Turkey, South Africa, the Gulf, Central and Eastern Europe outside the euro area).
  - **Transversal:** covers both groups, or is global, cross-country, theoretical or methodological with no particular focus.
- `label_relevance` (optional): 0–10, how useful the paper is to a Global Markets Research team (rates, FX, credit, macro, EM, sectors).
- `notes` (optional): anything ambiguous.

Then run:

```bash
cd pipeline && uv run roundup eval
```

It costs well under one cent with Claude Haiku 5.5. Per-paper results are written to `eval/results.csv`.
