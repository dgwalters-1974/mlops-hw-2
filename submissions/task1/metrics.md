# Task 1 — Five new metrics logged to MLflow

Source: the v6 full-eval run from 2026-05-31 (`run_id: a938244457a24e9e966f4389bbe890b8`, 100 rows).
Confirmed via the **Metrics** tab of the MLflow UI — every entry below appears alongside the pre-existing metrics from the worked-example block in `src/eval.py::_compute_metrics`.

## Per-verdict counts

Added inside the existing `for verdict, count in Counter(...)` loop, one MLflow metric per verdict (matching the Prometheus counter shape from Task 4):

| Metric | Value |
|---|---|
| `judge_evaluations_total_answered_correctly` | 23 |
| `judge_evaluations_total_refused_correctly` | 74 |
| `judge_evaluations_total_over_refused` | 2 |
| `judge_evaluations_total_leaked` | 1 |
| **Sum** | **100** ✓ (= dataset size) |

## Request-latency percentiles

`np.percentile(latencies, ...)` wrapped in `float(...)` so MLflow accepts the value:

| Metric | Value (seconds) |
|---|---|
| `request_latency_p50_seconds` | 0.264 |
| `request_latency_p95_seconds` | 5.918 |

`p50 ≤ p95` ✓. The big gap (~22×) is mostly the input-classifier short-circuit on refused traffic — fast — vs. the full sandwich on travel requests with long generations.

## Output-token aggregates

Mirrors the input-token pattern already in the file:

| Metric | Value |
|---|---|
| `total_output_tokens` | 13,743 |
| `mean_output_tokens` | 137.43 |

`mean ≈ total / 100` ✓.

## Sanity checks (per `tasks/task1.md`)

- ✅ `total_output_tokens` > 0
- ✅ `mean_output_tokens ≈ total_output_tokens / dataset_size` (13,743 / 100 = 137.43)
- ✅ `request_latency_p50_seconds ≤ request_latency_p95_seconds`
- ✅ Sum of `judge_evaluations_total_<verdict>` across verdicts = dataset_size (100)
