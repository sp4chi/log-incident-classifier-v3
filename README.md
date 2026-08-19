# Lyzr Take-Home — Track A: Auto-Remediation from Logs

Autonomous SRE log triage and closed-set remediation agent, built on Lyzr Agent Studio and driven over its API by `harness.py`.

## Results (full 455-event dataset, both passes call the same live agent)

| Metric                           | Target | Naive (455 calls) | Optimized (16 calls) |
| -------------------------------- | ------ | ----------------- | -------------------- |
| Category macro-F1 (40 labeled)   | ≥ 0.85 | 1.00              | 1.00                 |
| Root-cause macro-F1 (40 labeled) | ≥ 0.80 | 1.00              | 1.00                 |
| Free-form remediations           | 0      | 0                 | 0                    |
| False escalation rate            | report | 0.0%              | 0.0%                 |
| p50 latency, escalated events    | report | 3.68s             | 4.08s                |
| p95 latency, escalated events    | ≤ 4.0s | 5.27s             | 3.9–4.6s (see note)  |
| Total tokens                     | report | 1,579,688         | 55,592               |
| Total cost (est.)                | report | $2.48             | $0.087               |
| Cost per task                    | report | $0.00544          | $0.00019             |
| Cost reduction vs. naive         | ≥ 50%  | —                 | 96.5% (28.3×)        |
| Wall clock, full batch           | report | 424s              | 15–32s               |
| Throughput                       | report | 64 tasks/min      | 866–1844 tasks/min   |

**p95 latency note**: the optimized pass only makes 16 real calls (one per unique message), so p95 is the 2nd-worst of 16 samples — a small, noisy statistic. Three repeated runs at the same settings measured 3.91s, 4.34s, and 4.65s. Treat this as "around the 4s line," not a precise number; the naive pass's p95 (5.27s, n=455) is the statistically solid measurement, and it doesn't gate the SLO since the optimized path is what ships.

**Token/cost figures are estimates**: Lyzr's `/v3/inference/chat/` response carries no usage block, so every token/cost number above comes from a local estimate calibrated against 16 real metered traces pulled from the Studio traces dashboard (see the calibration comment block at the top of `harness.py`). The naive-vs-optimized _delta_ is solid regardless (it's driven by the 455→16 call ratio), the absolute dollar figures are calibrated estimates.

## Repository

- [`SCOPING_MEMO.md`](SCOPING_MEMO.md) — Part 1, client-facing scoping note.
- [`OPTIMIZATION_WRITEUP.md`](OPTIMIZATION_WRITEUP.md) — Part 2/3, levers pulled + moving-target analysis.
- [`harness.py`](harness.py) — the benchmark harness (naive baseline, optimized/dedup build, metrics, calibration).
- [`payload.json`](payload.json) — the deployed agent's config (instructions, few-shot examples, model settings), kept in sync with what's live on Studio.
- [`track_a_logs.xlsx`](track_a_logs.xlsx) — the provided dataset.

## Running it

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

`.env`:

```
LYZR_API_KEY=...
LYZR_AGENT_ID=...
LYZR_USER_ID=...
```

```bash
# both passes, regenerates the results table + CSVs + summary.json
python harness.py --data track_a_logs.xlsx --mode both --max-tasks 2 --out-prefix results_final

# either pass alone
python harness.py --data track_a_logs.xlsx --mode naive
python harness.py --data track_a_logs.xlsx --mode optimized --max-tasks 2
```

## What's actually enabled on Studio, and why

| Feature                                  | On?                       | Why                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ---------------------------------------- | ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Conversational memory (`store_messages`) | Off                       | Triage is stateless — one log line in, one verdict out. Memory would add tokens and latency for no benefit here.                                                                                                                                                                                                                                                                                                                                     |
| 4 few-shot examples                      | On                        | Anchors the model to the exact closed-set strings (`payload.json`'s `examples` field) — the two taxonomy entries with a worked example are the two the model reproduces most reliably verbatim.                                                                                                                                                                                                                                                      |
| Platform JSON-schema / `response_format` | Off, deliberately         | Removed after a real incident: Lyzr's routing silently fell back to an incompatible model mid-batch, and its structured-output implementation couldn't accept the schema — every call 400'd. Enforcement now happens via prompt instructions + code-side validation in `harness.py` (`ALLOWED_CATEGORIES`/`ALLOWED_ROOT_CAUSES`/`ALLOWED_REMEDIATIONS`), which degrades to "flag for human review" instead of "pipeline down" when the model drifts. |
| Multi-provider fallback                  | On (configured in Studio) | Protects against the exact failure mode above recurring as a hard outage. Not yet re-exported into `payload.json` as a checkable artifact — flagging that as a to-do, not overstating it as fully documented.                                                                                                                                                                                                                                        |

## Known limitations, stated plainly

- Token/cost numbers are estimates calibrated from real traces, not metered API numbers (Lyzr doesn't return a usage block).
- `false_escalation_rate` is scored against the 40 labeled events; it assumes every message outside that set is noise, which holds for this specific 16-unique-message corpus but isn't a general guarantee.
- `category` is derived deterministically from `root_cause` in post-processing, so its F1 tracks root-cause F1 by construction — it isn't an independently-earned model score.
- Optimized-pass p95 is measured on only 16 calls; see the note in the results table.
