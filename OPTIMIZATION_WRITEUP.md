# PART 2/3: Optimization Write-Up & Moving-Target Analysis

## Results (from `harness.py`, full 455-event dataset)

| Metric | Naive (455 calls) | Optimized (16 calls) | Delta |
|---|---|---|---|
| Category macro-F1 | 1.00 | 1.00 | — |
| Root-cause macro-F1 | 1.00 | 1.00 | — |
| Free-form remediations | 0 | 0 | — |
| False escalation rate | 0.0% | 0.0% | — |
| p50 latency, escalated | 3.68s | 4.08s | — |
| p95 latency, escalated | 5.27s (n=455) | 3.9–4.6s (n=16, noisy — see README) | — |
| Total tokens | 1,579,688 | 55,592 | ↓96.5% |
| Total cost (estimate) | $2.4765 | $0.0874 | ↓96.5% (28.3×) |
| Cost per task | $0.005443 | $0.000192 | ↓96.5% |
| Wall clock | 424s | 15–32s | ↓93–96% |
| Throughput | 64 tasks/min | 866–1844 tasks/min | 14–29× |

Cost/token figures are local estimates, calibrated against 16 real metered traces pulled from the Studio dashboard — see the calibration note in `harness.py`. The accuracy numbers and the call-count ratio (both of which drive the headline deltas) are not estimates.

## Levers pulled, and what each one actually bought

**1. Deduplication before the model ever sees a message (the main lever).** 455 raw rows collapse to 16 unique message signatures; one real call per signature, the verdict fanned out to every duplicate row at zero extra latency/cost. This is where essentially all of the 96.5% cost and token reduction comes from — not a cheaper model, not fewer output tokens per call. *Cost/scale: large win. Accuracy: neutral — same model, same prompt, same verdict per message either way. Latency: large win on batch wall-clock (424s → ~20s); no effect on the per-call latency floor.*

**2. Confidence gating (`confidence < 0.6` → forced human review, in code, not just prompt).** Zero added calls — it's a threshold check on a field already in the response. *Accuracy/safety: catches low-confidence verdicts before they'd be auto-executed. Cost elsewhere: none in dollars, but it does shift work to a human reviewer — worth reporting the flagged count alongside the F1 numbers, not F1 alone. On this run: 0 flagged, because the taxonomy match was clean.*

**3. Closed-set code-level validation, independent of the prompt.** `ALLOWED_CATEGORIES`/`ALLOWED_ROOT_CAUSES`/`ALLOWED_REMEDIATIONS` in `harness.py` reject anything outside the approved set regardless of what the model returns, and `root_cause` deterministically derives `category` in post-processing rather than trusting the model's own category field. *Accuracy/safety: this is the actual mechanism behind "0 free-form remediations" — a guarantee the code enforces, not one the prompt merely requests. Cost elsewhere: none — it's a dict lookup. Caveat: category-F1 tracks root-cause-F1 by construction, not an independent signal.*

**4. Concurrency-bounded async calls (`MAX_TASK`, `asyncio.Semaphore` + shared `httpx.AsyncClient`).** This is the one real latency-vs-throughput trade-off we could directly measure: raising concurrency raises throughput but also raises tail latency (more in-flight requests contending for the same provider queue). `MAX_TASK=2` is what we ship with to stay near the p95≤4s SLO. *Latency: this is the lever that decides whether p95 clears the SLO. Cost/throughput: higher `MAX_TASK` finishes the batch faster in wall-clock terms — direct latency-vs-throughput trade, not free.*

**5. No platform-level JSON-schema / `response_format` enforcement (deliberately off).** We hit a real incident where Lyzr's routing layer silently substituted a fallback model mid-batch whose structured-output path was incompatible with the schema we'd set — every call in that batch failed with a 400. We removed schema enforcement and now rely on prompt instructions + the code-side validator in lever 3, which degrades to "flag for review" instead of "pipeline down" when the model drifts from the taxonomy. *Reliability: converts a hard outage into a soft, visible degradation. Accuracy: no schema backstop means defensive parsing has to catch more — which is why lever 3 is a hard requirement, not optional polish, in this design.*

**6. Multi-provider fallback, configured in Studio.** Protects against the exact failure mode in lever 5 recurring — if the primary model is rate-limited or unavailable, a fallback model keeps the pipeline moving instead of stalling. We don't have an isolated before/after measurement for this one (it wasn't triggered during this benchmark run), so we're not attaching a percentage to it — it's a reliability lever, not a cost/accuracy one, and we're stating that distinction rather than forcing a number that isn't real.

**Deliberately left off: a regex/pattern pre-filter for obvious noise** (e.g. hardcoding `GET /health 200` as free). With only 16 unique messages in this corpus, hand-written noise patterns would overfit to this specific dataset and risk masking a real incident that happens to match a "known-noise" shape in production. Dedup already captures the volume win without that assumption, and generalizes to any duplicate-heavy corpus without maintenance.

## Moving-target: latency SLO tightens to 1.5s p95

A ~3.5k-token prompt against a hosted model has an inference floor well above 1.5s — no amount of harness-side tuning gets there without changing what's sent to the model. The actual levers, in order:

1. **Prompt compression**: the 3,397-token fixed overhead (measured, see `harness.py`) is dominated by the taxonomy table and 4 few-shot examples. Cutting to 1–2 examples and compressing the taxonomy to a lookup key rather than full sentences would meaningfully cut input tokens and time-to-first-token — at some cost to exactly the taxonomy-adherence problem we hit this session, so this needs re-validating against the labeled set before shipping, not assumed safe.
2. **Route to a smaller/faster model** for the classification step, keeping the current model only for ambiguous/low-confidence cases — a cheap-fast/expensive-accurate split rather than one model for everything.
3. **Accept that dedup's fan-out rows (96.5% of volume) already satisfy any latency SLO** — they're a dict lookup, not a call. The SLO only binds on the 16 real calls per batch, so the real target is: can 16 calls per unique-message-batch clear 1.5s each, not 455.

Expected accuracy cost: real but unmeasured here — smaller/faster models increase the risk of exactly the taxonomy-drift failure mode we saw firsthand this session, which is why lever 3 (hard code-level closed-set validation) is what makes this trade survivable rather than silently dangerous.
