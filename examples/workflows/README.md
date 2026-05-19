# Workflow Examples

Canonical, hand-authored **sample runs** for the multi-skill workflows defined
in [`workflows/*.yaml`](../../workflows/). Each sub-directory shows the exact
prompt you would give Claude, plus the artifact each required step contributes
to the workflow's data flow, plus a machine-readable `manifest.yaml` that a
future fixture/replay harness can consume.

> ⚠️ **Illustrative only — not investment advice.** Every artifact here uses
> **fictional / hand-authored data** (the trade example uses the fictional
> ticker `EXMPL`; the market-regime example uses a fictional market snapshot
> with **no individual tickers**). These files are teaching/reference samples,
> **not** live signals, recommendations, or real skill output captured from a
> real account. Do not trade off them.

## Available examples

| Example | Workflow | Cadence | Skills (required) |
|---|---|---|---|
| [`market-regime-daily/`](market-regime-daily/) | [`market-regime-daily.yaml`](../../workflows/market-regime-daily.yaml) | daily | market-breadth-analyzer → uptrend-analyzer → exposure-coach |
| [`trade-memory-loop/`](trade-memory-loop/) | [`trade-memory-loop.yaml`](../../workflows/trade-memory-loop.yaml) | per closed trade | trader-memory-core → signal-postmortem → trader-memory-core |

Each example is **required-only**: it exercises just the required steps. The
one optional step in each workflow is intentionally skipped and documented in
that example's `README.md` and `manifest.yaml` (`optional_steps_skipped`). A
full-path sample (including optional steps) may be added later in a separate
change.

## Artifact convention: `raw-plus-handoff`

The sample JSON artifacts are **workflow hand-off artifacts**, not byte-for-byte
copies of raw skill stdout:

- The nested `composite { … }` block **mirrors the real skill output
  structure** (e.g. `market-breadth-analyzer` and `uptrend-analyzer` both nest
  their score at `composite.composite_score`).
- A **top-level hand-off field** (`breadth_score` / `uptrend_score`) is added
  alongside it. This is the field the Claude-orchestrated next step actually
  consumes when it hands a score to `exposure-coach`.

This convention is deliberate and also **documents a real, known
`exposure-coach` parser asymmetry**: `extract_uptrend_score()` already reads
the nested `composite` shape, but `extract_breadth_score()` reads **only** the
top-level field — so raw breadth output (nested only) is silently dropped by
`exposure-coach` today. That parser gap is **not fixed here** (this is a
docs/sample-only change); it is tracked as a separate code issue and linked
from the pull request that introduced these examples. The sample is authored
so that running the **real** `exposure-coach` extractors over these files
reproduces exactly the scores shown in `04_exposure_decision.json` (see each
example's verification notes).

## Coupling

These files are intentionally **decoupled** from the generated-docs / drift-gate
machinery: no generator, validator, snapshot builder, catalog, CI metadata
job, or pytest path reads `examples/`. Editing or extending them cannot cause
catalog/snapshot/docs drift. (They are still subject to the standard
hygiene pre-commit hooks — whitespace, YAML syntax, `detect-secrets`,
`no-absolute-paths`, etc.)
