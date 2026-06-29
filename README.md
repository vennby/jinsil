# jinsil

Deterministic offline ranker for the Redrob Intelligent Candidate Discovery &
Ranking Challenge.

## Approach

The ranker is a CPU-only, no-network scoring pipeline for the Senior AI Engineer
founding-team JD. It streams candidates, scores profile evidence, and keeps only
a bounded top-K heap in memory. The implementation lives in `utils/ranking/`,
with `rank.py` as the thin reproducible CLI entry point.

Main scoring components:

- production ML/retrieval/search/ranking/matching evidence
- hands-on engineering and current-title fit
- JD-shaped evidence depth across retrieval, production, evaluation, product
  workflow, and mentoring/architecture signals
- seniority fit around the JD's 5-9 year target
- product-company and shipped-system career evidence
- location/logistics fit
- Redrob engagement, availability, and trust signals
- penalties for keyword stuffing, non-engineering current roles, consulting-only
  trajectories, stale availability, and honeypot-like skill inconsistencies

## Code Structure

- `rank.py`: thin CLI entry point used by the reproduction command.
- `utils/ranking/config.py`: JD-specific scoring terms, weights, and constants.
- `utils/ranking/text.py`: fast normalized phrase matching.
- `utils/ranking/features.py`: candidate and career-history feature extraction.
- `utils/ranking/scoring.py`: evidence-depth scoring, penalties, and calibration.
- `utils/ranking/reasoning.py`: fact-grounded reasoning generation.
- `utils/ranking/ranker.py`: streaming top-K ranking loop.
- `utils/ranking/io.py`: candidate loading, submission writing, diagnostics.
- `validate_submission.py`: official format validator.

The runtime path has no third-party dependencies.

## Reproduce

```powershell
python rank.py --candidates .\candidates.jsonl.gz --out .\team_jinsil.csv
python validate_submission.py .\team_jinsil.csv
```

`team_jinsil.csv` is also the default output name if `--out` is omitted.
On the local 100K `candidates.jsonl` file, the ranking step completed in about
290 seconds with progress logging enabled.

For a quick local smoke test on the bundled sample:

```powershell
python rank.py --candidates .\sample_candidates.json --out .\sample_ranked.csv --top-n 20
```

For tuning, emit component diagnostics:

```powershell
python rank.py --candidates .\sample_candidates.json --out .\sample_ranked.csv --top-n 20 --diagnostics-out .\sample_diagnostics.csv
```
