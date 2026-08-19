# Lyzr Take-Home Assignment — Track A: Auto-Remediation from Logs

Autonomous SRE log triage, noise filtering, and closed-set remediation agent built on **Lyzr Agent Studio**.

---

## 🏆 Key Measured Results

| Metric | Target / Requirement | Measured (Optimized Build) | Result |
|---|:---:|:---:|:---:|
| **Scale** | Process full 455-event batch | **455 events covered** | ✅ Pass |
| **Category Macro-F1** | $\ge 0.85$ | **1.0000** | ✅ Pass (100%) |
| **Root-Cause Macro-F1** | $\ge 0.80$ | **1.0000** | ✅ Pass (100%) |
| **Free-Form Remediations** | **0** (Strict closed-set) | **0** | ✅ Pass |
| **False Escalation Rate** | Low / Report | **0.0%** (All noise filtered) | ✅ Pass |
| **p95 Latency (Escalated)** | $\le 4.0\text{s}$ | **3.911s** (`MAX_TASK=2`) | ✅ Pass |
| **Cost Reduction vs. Naive** | $\ge 50\%$ | **96.5% cost reduction** (29.9×) | ✅ Pass |
| **Throughput** | Report (events/min) | **977.9 tasks/min** | ✅ Pass |

---

## 📁 Repository Structure & Deliverables

* [`SCOPING_MEMO.md`](file:///Users/kaushikgohainbora/Desktop/lyzr.ai/SCOPING_MEMO.md): **Part 1 — Client Scoping Memo** (Executive framing, risks, 4-way trade-offs, 2-week engagement roadmap).
* [`OPTIMIZATION_WRITEUP.md`](file:///Users/kaushikgohainbora/Desktop/lyzr.ai/OPTIMIZATION_WRITEUP.md): **Part 2 & 3 — Optimization Write-Up & Moving-Target Analysis** (Deep-dive on the 4 optimization levers, side-by-side benchmark table, feature audit, budget/latency pivot plans).
* [`harness.py`](file:///Users/kaushikgohainbora/Desktop/lyzr.ai/harness.py): The async benchmark harness driving Lyzr Agent Studio over API with automated scoring against ground-truth datasets.
* [`payload.json`](file:///Users/kaushikgohainbora/Desktop/lyzr.ai/payload.json): Complete agent configuration schema (instructions, few-shot examples, closed-set mapping, model settings).
* [`requirements.txt`](file:///Users/kaushikgohainbora/Desktop/lyzr.ai/requirements.txt): Minimal Python dependencies (`httpx`, `pandas`, `openpyxl`, `python-dotenv`, `scikit-learn`, `tiktoken`).

---

## 🚀 Quickstart & Reproduction Guide

### 1. Prerequisites & Setup
```bash
# Clone repository and enter directory
cd lyzr.ai

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables
Create a `.env` file in the root directory:
```bash
LYZR_API_KEY="your-lyzr-api-key"
LYZR_AGENT_ID="your-agent-id"
LYZR_USER_ID="your-email@example.com"
```

### 3. Running the Benchmark Harness

#### Run Optimized Build (Fast & Cost-Efficient — 16 unique calls):
```bash
python harness.py --data track_a_logs.xlsx --mode optimized --max-tasks 2
```

#### Run Naive Baseline (Unoptimized — 455 separate calls):
```bash
python harness.py --data track_a_logs.xlsx --mode naive --max-tasks 2
```

#### Run Full Benchmark (Generates Side-by-Side Table & Summary JSON):
```bash
python harness.py --data track_a_logs.xlsx --mode both --max-tasks 2 --out-prefix results_final
```

#### Interactive Calibration Check (Validates local token/cost model against real Lyzr trace):
```bash
python harness.py --mode calibrate
```

---

## 🛠️ The 4 Core Optimization Levers

1. **In-Memory / Distributed Deduplication**:
   * Clusters 455 raw log lines into 16 unique signatures before calling the LLM.
   * Fanned verdicts back out in $O(1)$ time ($<1\mu\text{s}$), cutting API calls, tokens, and billing by **96.5%**.
2. **Stateless Memory Elimination (`store_messages: false`)**:
   * Stripped the 8-span conversational memory pipeline on Lyzr Studio, reducing latency by **34%** and eliminating redundant credit charges.
3. **Deterministic Code Guards & Cross-Field Derivation**:
   * Mapped `root_cause` $\to$ `category` deterministically in code post-processing.
   * Eliminates LLM classification drift and guarantees **0 free-form remediations**.
4. **Asyncio Keep-Alive Connection Pooling (`MAX_TASK=2`)**:
   * Lightweight `asyncio.Semaphore` with `httpx.AsyncClient` keeps connection reuse high while eliminating upstream provider queue spikes, bringing **p95 latency to 3.91s**.
