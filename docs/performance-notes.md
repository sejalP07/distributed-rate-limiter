# Performance and Concurrency Investigation

## Objective

Investigate latency increases observed during concurrent requests and test whether increasing the Uvicorn worker count improves performance.

## Test environment

- Local Windows and Docker Compose environment.
- FastAPI gateway with Redis rate limiting, PostgreSQL authentication support, and a backend FastAPI service.
- Default single-worker Uvicorn configuration retained.
- Results are local measurements, not production capacity guarantees.

## Long benchmark

Endpoint: `GET /health`

| Requests | Concurrency | Throughput | Average | P95 | P99 |
|---:|---:|---:|---:|---:|---:|
| 1000 | 20 | 80.82 req/s | 236.96 ms | 776.88 ms | 1469.46 ms |

## Worker-count experiment

Selected measurements from separate runs:

| Worker count | Endpoint | Concurrency | Throughput | Average | P95 | P99 |
|---:|---|---:|---:|---:|---:|---:|
| 1 | `/health` | 10 | 52.16 req/s | 172.40 ms | 431.39 ms | 756.70 ms |
| 2 | `/health` | 10 | 35.44 req/s | 267.06 ms | 775.16 ms | 1220.51 ms |
| 1 | `/health` | 20 | 52.59 req/s | 356.27 ms | 975.67 ms | 1433.28 ms |
| 2 | `/health` | 20 | 43.01 req/s | 425.36 ms | 2194.80 ms | Not recorded |
| 1 | `/api/demo` | 20 | 44.31 req/s | 406.05 ms | 1057.18 ms | 1591.02 ms |
| 2 | `/api/demo` | 20 | 47.88 req/s | 396.63 ms | 1092.22 ms | 2190.46 ms |

The measurements were collected across separate runs and are not a controlled A/B experiment. They show no consistent benefit from increasing the worker count.

## Resource observations

- API memory was approximately 71 MiB during the recorded snapshot.
- API and dependency CPU usage varied between snapshots.
- The available snapshots do not establish a specific bottleneck.
- Successful health responses were observed in the API logs.

## Decision

Retain one Uvicorn worker for now. Do not claim that worker-count tuning has solved the latency issue.

The Prometheus metrics are in-process, so running multiple workers also requires a suitable multiprocess metrics strategy before metrics can be trusted across all workers.

## Step 22: Repeatable Load Testing

### Methodology

The benchmark used the updated `scripts/load_test.py` script.

- Environment: Local Windows environment using Docker Compose.
- Endpoint: `GET /health`.
- Measured requests per run: 1,000.
- Concurrency: 20.
- Warm-up requests before each run: 20.
- Number of measured runs: 3.
- All 3,000 measured requests returned HTTP 200.
- No rate-limit rejections or other errors occurred.

### Individual benchmark results

| Run | Throughput (req/s) | Average (ms) | P50 (ms) | P95 (ms) | P99 (ms) |
|---:|---:|---:|---:|---:|---:|
| 1 | 77.91 | 255.10 | 153.45 | 759.94 | 1418.56 |
| 2 | 83.50 | 238.09 | 149.99 | 787.75 | 1178.83 |
| 3 | 72.72 | 270.94 | 171.96 | 765.48 | 2095.56 |
| Median | 77.91 | 255.10 | 153.45 | 765.48 | 1418.56 |

### Results interpretation

The three runs produced a median throughput of 77.91 requests per second, median average latency of 255.10 ms, median P95 latency of 765.48 ms, and median P99 latency of 1418.56 ms.

Throughput varied from 72.72 to 83.50 requests per second. P99 latency also varied, reaching 2095.56 ms in the third run.

These results provide a repeatable local baseline. The elevated tail latency warrants further investigation, but the measurements alone do not identify a specific bottleneck.

### Rate-limit observation

A separate single-run test used the following configuration:

- Endpoint: `GET /api/demo`.
- Requests: 100.
- Concurrency: 10.
- Warm-up requests: 0.
- Mode: `rate-limit`.

Results:

| Metric | Result |
|---|---:|
| Throughput | 32.71 req/s |
| Successful 2xx responses | 23 |
| HTTP 429 responses | 77 |
| Other errors | 0 |
| Average latency | 294.18 ms |
| P50 latency | 83.45 ms |
| P95 latency | 1942.32 ms


## Step 23: Controlled Concurrency Sweep

### Methodology

- Environment: Local Windows and Docker Compose.
- Endpoint: `GET /health`.
- Measured requests per run: 300.
- Concurrency levels: 1, 5, 10, 20, and 40.
- Repeated measured runs per level: 3.
- Warm-up requests before each run: 20.
- Total measured requests: 4,500.
- All measured requests returned HTTP 200.
- No HTTP 429 responses or other errors occurred.

### Results

| Concurrency | Throughput (req/s) | Average (ms) | P50 (ms) | P95 (ms) | P99 (ms) |
|---:|---:|---:|---:|---:|---:|
| 1 | 136.31 | 7.32 | 6.47 | 11.52 | 16.32 |
| 5 | 94.74 | 52.50 | 38.23 | 163.23 | 232.44 |
| 10 | 97.81 | 100.04 | 55.88 | 363.76 | 639.48 |
| 20 | 49.35 | 400.33 | 267.76 | 1525.51 | 1900.55 |
| 40 | 65.17 | 587.70 | 402.36 | 1714.61 | 2288.31 |

*Values are the median metrics reported across three measured runs at each concurrency level.*

### Interpretation

Concurrency 1 produced the highest measured median throughput at 136.31 requests per second. Throughput was lower at concurrency levels 5, 10, and 20, and partially recovered at concurrency 40.

Average and tail latency increased substantially as concurrency increased. Run-to-run variability was also observed, particularly at higher concurrency levels.

The results do not show a consistent throughput benefit from increasing concurrency. They do not establish a specific application or dependency bottleneck.

### Decision and follow-up

- Keep the existing single-worker configuration for now.
- Do not treat higher concurrency as an optimization by itself.
- Use Prometheus metrics to investigate gateway, Redis, and backend latency.
- Repeat key benchmark configurations if needed to assess environmental variability.
- Select optimizations only after gathering evidence about the underlying bottleneck.

These results are local measurements and are not production capacity guarantees.

## Step 24: API-Path Performance Baseline

### Methodology

- Endpoint: GET /api/demo.
- Environment: Local Windows and Docker Compose.
- Measured requests per run: 300.
- Concurrency: 10.
- Measured runs: 3.
- Warm-up requests per run: 20.
- Temporary high rate-limit thresholds were used for throughput testing.
- All 900 measured requests returned HTTP 2xx.
- No HTTP 429 responses or other errors occurred.

### Benchmark results

| Run | Throughput (req/s) | Average (ms) | P50 (ms) | P95 (ms) | P99 (ms) |
|---:|---:|---:|---:|---:|---:|
| 1 | 121.88 | 81.12 | 54.00 | 253.33 | 480.01 |
| 2 | 98.13 | 100.83 | 86.49 | 186.26 | 283.48 |
| 3 | 107.19 | 92.48 | 85.77 | 184.07 | 240.42 |
| Median | 107.19 | 92.48 | 85.77 | 186.26 | 283.48 |

### Prometheus observations

A query shortly after the benchmark returned the following
one-minute-window P95 latency estimates:

- Gateway: 169.1 ms.
- Redis: 20.1 ms.
- Backend: 84.9 ms.

These are independent histogram estimates, not an exact per-request
latency breakdown. Later queries returned NaN or zero after the
workload became inactive.

### Interpretation

The short local benchmark met the initial targets of P95 below
250 ms and P99 below 500 ms at concurrency 10.

Run-to-run variation remains visible. The measurements do not yet
establish sustained five-minute capacity or identify a specific
bottleneck.

Further work should compare gateway, Redis, and backend behavior
during a sustained workload, with the normal rate-limit settings
restored after performance testing.

These measurements are local results, not production guarantees.