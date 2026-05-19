# Example: `market-regime-daily` (required-only)

A canonical sample run of the
[`market-regime-daily`](../../../workflows/market-regime-daily.yaml) workflow:
a daily, no-API market-posture check that decides whether new swing-trade risk
is allowed before the session.

> ⚠️ **Illustrative only — not investment advice.** This sample uses a
> **fictional market snapshot** for a fixed date (`2026-01-15`) with **no
> individual tickers**. The numbers are hand-authored to be internally
> consistent and code-faithful, **not** captured from a live run.

## Steps in this sample

| Step | Skill | Artifact | In this sample |
|---|---|---|---|
| 1 | `market-breadth-analyzer` | `market_breadth_report` | ✅ included |
| 2 | `uptrend-analyzer` | `uptrend_report` | ✅ included |
| 3 | `market-top-detector` | `top_risk_report` | ⏭️ **skipped** (optional) |
| 4 | `exposure-coach` | `exposure_decision` | ✅ included |

Step 3 is the workflow's one optional step. This is the **required-only**
canonical sample, so it is intentionally skipped (recorded in
[`sample-run/manifest.yaml`](sample-run/manifest.yaml) under
`optional_steps_skipped`). A full-path sample including the optional satellites
may be added later in a separate change.

## Files

```
sample-run/
  prompt.md                       # the prompt you give Claude
  manifest.yaml                   # machine-readable step → artifact → file map
  01_market_breadth_report.json   # step 1 canonical (raw composite{} + breadth_score)
  01_market_breadth_report.md     # step 1 companion (human report)
  02_uptrend_report.json          # step 2 canonical (raw composite{} + uptrend_score)
  02_uptrend_report.md            # step 2 companion
  04_exposure_decision.json       # step 4 canonical (exposure-coach output)
  04_exposure_decision.md         # step 4 companion (one-page posture)
```

## The `raw-plus-handoff` artifact convention

`01`/`02` JSON each carry **both**:

- the real nested `composite { composite_score, zone, … }` block — exactly the
  structure `market-breadth-analyzer` / `uptrend-analyzer` emit; and
- a **top-level hand-off field** (`breadth_score` / `uptrend_score`) equal to
  `composite.composite_score`.

The top-level field exists because of a **real, known `exposure-coach` parser
asymmetry**:

- `extract_uptrend_score()` already reads the nested `composite` shape, so raw
  uptrend output is consumable as-is.
- `extract_breadth_score()` reads **only** the top-level field — it has **no**
  nested-`composite` fallback — so *raw* breadth output (nested only) is
  silently dropped, becoming a missing **critical** input.

This sample documents that gap rather than hiding it. It is **not fixed here**
(this is a docs/sample-only change); the parser fix is tracked as a separate
code issue, linked from the pull request that introduced this example. The
sample is authored so the **real** extractors reproduce the exact scores in
`04_exposure_decision.json` (`breadth_score == 66`, `uptrend_score == 72`).

## Why the posture is `REDUCE_ONLY / LOW` (this is correct)

`exposure-coach` treats `regime`, `top_risk`, and `breadth` as **critical
inputs** and applies a **−10 composite haircut per missing critical input**.
In the required-only path, both `regime` (`macro-regime-detector`) and
`top_risk` (`market-top-detector`) are absent → a −20 haircut. With breadth 66
and uptrend 72 the pre-haircut composite is `(66+72)/2 = 69.0`, haircut to
`49.0`, which maps to a **48% exposure ceiling, REDUCE_ONLY recommendation,
LOW confidence** — even though internal participation is `BROAD`.

This is the **honest, code-faithful** output of the required-only path, and it
is exactly *why the optional satellites exist*: adding `macro-regime-detector`
and `market-top-detector` clears the critical-input haircut and lets the
posture rise toward `NEW_ENTRY_ALLOWED` when internals support it. The
required-only sample deliberately shows the conservative floor.

## Reproduce / verify

From the repo root (read-only; writes only to a temp dir):

```bash
python3 - <<'PY'
import json, sys
sys.path.insert(0, "skills/exposure-coach/scripts")
import calculate_exposure as ce
d = "examples/workflows/market-regime-daily/sample-run"
b = json.load(open(f"{d}/01_market_breadth_report.json"))
u = json.load(open(f"{d}/02_uptrend_report.json"))
dec = json.load(open(f"{d}/04_exposure_decision.json"))
assert ce.extract_breadth_score(b) == dec["component_scores"]["breadth_score"] == 66
assert ce.extract_uptrend_score(u) == dec["component_scores"]["uptrend_score"] == 72
print("OK: real exposure-coach extractors reproduce the sample scores")
PY
```

## Run it for real

See [`sample-run/prompt.md`](sample-run/prompt.md). The skills fetch public
CSVs (no API key); your live numbers will differ from this fixed sample.
