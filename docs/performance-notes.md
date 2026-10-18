# Performance and Concurrency Investigation

## Objective

Investigate latency increases observed during concurrent requests and
test whether increasing the Uvicorn worker count improves performance.

## Test environment

- Local Windows and Docker Compose environment.
- FastAPI gateway with Redis rate limiting, PostgreSQL authentication
  support, and a backend FastAPI service.
- Default single-worker Uvicorn configuration retained.
- Results are local measurements, not production capacity guarantees.

## Long benchmark

Endpoint: GET /health

| Requests | Concurrency | Throughput | Average | P95 | P99 |
|---:|---:|---:|---:|---:|---:|
| 1000 | 20 | 80.82 req/s | 236.96 ms | 776.88 ms | 1469.46 ms |

## Worker-count experiment

Selected measurements from separate runs:

| Worker count | Endpoint | Concurrency | Throughput | Average | P95 | P99 |
|---:|---|---:|---:|---:|---:|---:|
| 1 | /health | 10 | 52.16 req/s | 172.40 ms | 431.39 ms | 756.70 ms |
| 2 | /health | 10 | 35.44 req/s | 267.06 ms | 775.16 ms | 1220.51 ms |
| 1 | /health | 20 | 52.59 req/s | 356.27 ms | 975.67 ms | 1433.28 ms |
| 2 | /health | 20 | 43.01 req/s | 425.36 ms | 2194.80 ms | Not recorded |
| 1 | /api/demo | 20 | 44.31 req/s | 406.05 ms | 1057.18 ms | 1591.02 ms |
| 2 | /api/demo | 20 | 47.88 req/s | 396.63 ms | 1092.22 ms | 2190.46 ms |

The measurements were collected across separate runs and are not a
controlled A/B experiment. They show no consistent benefit from
increasing the worker count.

## Resource observations

- API memory was approximately 71 MiB during the recorded snapshot.
- API and dependency CPU usage varied between snapshots.
- The available snapshots do not establish a specific bottleneck.
- Successful health responses were observed in the API logs.

## Decision

Retain one Uvicorn worker for now. Do not claim that worker-count tuning
has solved the latency issue.

The Prometheus metrics are in-process, so running multiple workers also
requires a suitable multiprocess metrics strategy before metrics can be
trusted across all workers.

## Follow-up

Repeat the comparison under controlled conditions using the same request
count, concurrency, warm-up procedure, and multiple runs for each worker
configuration. Investigate application and dependency latency using the
existing Prometheus histograms before selecting further optimizations.

## Test status

The restored single-worker configuration passed 63 tests in the recorded
run. Rerun tests when making further changes.
