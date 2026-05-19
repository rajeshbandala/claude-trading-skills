# Example: `trade-memory-loop` (required-only)

A canonical sample run of the
[`trade-memory-loop`](../../../workflows/trade-memory-loop.yaml) workflow: the
per-closed-trade loop that records the outcome, generates a postmortem, and
journals the lessons so the next decision is better-informed.

> ⚠️ **Illustrative only — not investment advice.** This sample uses the
> **fictional ticker `EXMPL`** (Example Corp) and a hand-authored trade. The
> numbers are internally consistent and schema-faithful, **not** captured from
> a real account.

## Steps in this sample

| Step | Skill | Artifact | In this sample |
|---|---|---|---|
| 1 | `trader-memory-core` | `closed_thesis_record` | ✅ included |
| 2 | `signal-postmortem` | `postmortem_findings` | ✅ included |
| 3 | `backtest-expert` | `backtest_validation` | ⏭️ **skipped** (optional) |
| 4 | `trader-memory-core` | `lessons_log_entry` | ✅ included |

Step 3 is the workflow's one optional step. This is the **required-only**
canonical sample, so it is intentionally skipped (recorded in
[`sample-run/manifest.yaml`](sample-run/manifest.yaml) under
`optional_steps_skipped`). A full-path sample including the backtest
re-validation may be added later in a separate change.

## Files

```
sample-run/
  prompt.md                       # the prompt you give Claude
  manifest.yaml                   # machine-readable step → artifact → file map
  01_closed_thesis_record.yaml    # step 1 canonical (trader-memory-core thesis, CLOSED)
  02_postmortem_findings.json     # step 2 canonical (signal-postmortem record)
  02_postmortem_summary.md        # step 2 companion (human summary)
  04_lessons_log_entry.md         # step 4 canonical (journal entry)
```

`closed_thesis_record` has no companion (the YAML *is* the canonical artifact);
`lessons_log_entry` is inherently Markdown (canonical, no companion).
`postmortem_findings` has a JSON canonical + a Markdown companion. Every file
above (except `manifest.yaml` itself) is referenced from the manifest.

## The trade (fictional)

`EXMPL`, a `growth_momentum` / VCP-breakout thesis surfaced by `vcp-screener`
(grade A). Entered 2026-01-08 @ 142.10 (70 sh, 1% risk, stop 134.50), exited
2026-02-27 @ 168.40 (`target_hit`) after trailing past the initial 2R target.
Result: +18.5% / +$1,841 over 50 holding days; MAE -4.2%, MFE +21.0%.
Postmortem classifies it **`TRUE_POSITIVE`** — thesis-driven, not luck.

## Schema fidelity (this is enforced, not asserted)

- `01_closed_thesis_record.yaml` passes the **real** trader-memory-core
  validator: `jsonschema` Draft-07 against
  `skills/trader-memory-core/schemas/thesis.schema.json` **plus** the `CLOSED`
  business invariants in `thesis_store._validate_thesis()` (exit price/date
  set, valid `exit_reason`, `exit_date ≥ entry_date`, `status_history`
  monotonic and ending in `CLOSED`, RFC-3339 timestamps with timezone). Date
  strings are quoted so `yaml.safe_load` returns them as strings (the schema
  requires `type: string` + `format: date-time`/`date`).
- `02_postmortem_findings.json` is produced by the **real**
  `signal-postmortem` recorder consuming that thesis, so its
  `outcome_category` / `holding_days` are computed, not hand-typed.

## Reproduce / verify

From the repo root (read-only; `uv` provides `jsonschema`):

```bash
uv run python - <<'PY'
import json, sys, yaml
sys.path.insert(0, "skills/trader-memory-core/scripts")
import thesis_store
d = "examples/workflows/trade-memory-loop/sample-run"
t = yaml.safe_load(open(f"{d}/01_closed_thesis_record.yaml"))
thesis_store._validate_thesis(t)            # raises on any violation
pm = json.load(open(f"{d}/02_postmortem_findings.json"))
assert pm["outcome_category"] == "TRUE_POSITIVE"
assert pm["holding_days"] == 50
print("OK: thesis validates; postmortem fields reproduce")
PY
```

## Run it for real

See [`sample-run/prompt.md`](sample-run/prompt.md). No API key is required
(FMP is optional, only for MAE/MFE auto-calc); your real thesis IDs, dates,
and outcome will differ from this fixed sample.
