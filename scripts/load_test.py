
import argparse
import asyncio
import math
import statistics
import time
from collections import Counter
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class RequestResult:
    status_code: int
    latency_seconds: float
    error_type: str | None = None


@dataclass(frozen=True)
class RunSummary:
    run_number: int
    duration_seconds: float
    requests_per_second: float
    successful: int
    rate_limited: int
    errors: int
    average_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    status_counts: dict[int, int]


def percentile(values: list[float], percentage: float) -> float:
    """Calculate a percentile using the nearest-rank method."""
    if not values:
        return 0.0

    ordered = sorted(values)
    index = max(
        0,
        min(len(ordered) - 1, math.ceil(percentage / 100 * len(ordered)) - 1),
    )
    return ordered[index]


async def send_request(
    client: httpx.AsyncClient,
    url: str,
    request_number: int,
    mode: str,
    run_number: int,
    phase: str,
) -> RequestResult:
    if mode == "throughput":
        user_id = (
            f"loadtest-run-{run_number}-{phase}-{request_number}"
        )
    else:
        # Requests in a measured rate-limit run share one user identity.
        # Warm-up uses a different user identity.
        user_id = f"loadtest-run-{run_number}-{phase}-shared"

    start = time.perf_counter()

    try:
        response = await client.get(
            url,
            headers={"X-User-ID": user_id},
        )
        return RequestResult(
            status_code=response.status_code,
            latency_seconds=time.perf_counter() - start,
        )
    except httpx.RequestError as exc:
        return RequestResult(
            status_code=0,
            latency_seconds=time.perf_counter() - start,
            error_type=type(exc).__name__,
        )


async def execute_phase(
    client: httpx.AsyncClient,
    url: str,
    request_count: int,
    concurrency: int,
    mode: str,
    run_number: int,
    phase: str,
) -> list[RequestResult]:
    """Execute requests with at most `concurrency` active workers."""
    if request_count == 0:
        return []

    results: list[RequestResult | None] = [None] * request_count
    next_request = 0

    async def worker() -> None:
        nonlocal next_request

        while True:
            request_number = next_request
            next_request += 1

            if request_number >= request_count:
                return

            results[request_number] = await send_request(
                client=client,
                url=url,
                request_number=request_number,
                mode=mode,
                run_number=run_number,
                phase=phase,
            )

    worker_count = min(concurrency, request_count)

    await asyncio.gather(
        *(worker() for _ in range(worker_count))
    )

    # Every request slot has been populated by a worker.
    return [result for result in results if result is not None]


async def run_single_test(
    args: argparse.Namespace,
    run_number: int,
) -> RunSummary:
    limits = httpx.Limits(
        max_connections=args.concurrency,
        max_keepalive_connections=args.concurrency,
    )
    timeout = httpx.Timeout(
        args.timeout,
        connect=min(5.0, args.timeout),
    )

    async with httpx.AsyncClient(
        limits=limits,
        timeout=timeout,
    ) as client:
        if args.warmup_requests:
            await execute_phase(
                client=client,
                url=args.url,
                request_count=args.warmup_requests,
                concurrency=args.concurrency,
                mode=args.mode,
                run_number=run_number,
                phase="warmup",
            )

        start = time.perf_counter()

        results = await execute_phase(
            client=client,
            url=args.url,
            request_count=args.requests,
            concurrency=args.concurrency,
            mode=args.mode,
            run_number=run_number,
            phase="measured",
        )

        duration = time.perf_counter() - start

    status_counts = Counter(
        result.status_code for result in results
    )
    latencies_ms = [
        result.latency_seconds * 1000 for result in results
    ]

    successful = sum(
        200 <= result.status_code < 300 for result in results
    )
    rate_limited = status_counts.get(429, 0)
    errors = len(results) - successful - rate_limited

    return RunSummary(
        run_number=run_number,
        duration_seconds=duration,
        requests_per_second=(
            len(results) / duration if duration > 0 else 0.0
        ),
        successful=successful,
        rate_limited=rate_limited,
        errors=errors,
        average_ms=(
            statistics.mean(latencies_ms) if latencies_ms else 0.0
        ),
        p50_ms=percentile(latencies_ms, 50),
        p95_ms=percentile(latencies_ms, 95),
        p99_ms=percentile(latencies_ms, 99),
        status_counts=dict(status_counts),
    )


def print_run(result: RunSummary, total_runs: int) -> None:
    print()
    print("=" * 64)
    print(f"LOAD TEST RUN {result.run_number}/{total_runs}")
    print("=" * 64)
    print(f"Duration:             {result.duration_seconds:.3f} s")
    print(f"Throughput:           {result.requests_per_second:.2f} req/s")
    print(f"Successful (2xx):     {result.successful}")
    print(f"Rate limited (429):   {result.rate_limited}")
    print(f"Other errors:         {result.errors}")

    print("\nLATENCY")
    print("-" * 64)
    print(f"Average:              {result.average_ms:.2f} ms")
    print(f"P50:                  {result.p50_ms:.2f} ms")
    print(f"P95:                  {result.p95_ms:.2f} ms")
    print(f"P99:                  {result.p99_ms:.2f} ms")

    print("\nSTATUS DISTRIBUTION")
    print("-" * 64)

    for status_code, count in sorted(result.status_counts.items()):
        label = "network/error" if status_code == 0 else str(status_code)
        print(f"{label}: {count}")

    print("=" * 64)


def print_summary(results: list[RunSummary]) -> None:
    print("\n")
    print("#" * 64)
    print("REPEATED-RUN SUMMARY (MEDIAN)")
    print("#" * 64)

    metrics = [
        ("Throughput", [r.requests_per_second for r in results], "req/s"),
        ("Average latency", [r.average_ms for r in results], "ms"),
        ("P50 latency", [r.p50_ms for r in results], "ms"),
        ("P95 latency", [r.p95_ms for r in results], "ms"),
        ("P99 latency", [r.p99_ms for r in results], "ms"),
    ]

    for label, values, unit in metrics:
        print(
            f"{label + ':':20} "
            f"{statistics.median(values):.2f} {unit}"
        )

    combined_statuses: Counter[int] = Counter()
    for result in results:
        combined_statuses.update(result.status_counts)

    print("\nCOMBINED STATUS COUNTS")
    print("-" * 64)
    for status_code, count in sorted(combined_statuses.items()):
        label = "network/error" if status_code == 0 else str(status_code)
        print(f"{label}: {count}")

    print("#" * 64)


async def run_benchmarks(args: argparse.Namespace) -> None:
    results: list[RunSummary] = []

    for run_number in range(1, args.runs + 1):
        result = await run_single_test(args, run_number)
        results.append(result)
        print_run(result, args.runs)

    print_summary(results)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run repeatable load tests against the gateway."
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000/api/demo",
    )
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument(
        "--mode",
        choices=["throughput", "rate-limit"],
        default="throughput",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Number of measured runs (default: 3).",
    )
    parser.add_argument(
        "--warmup-requests",
        type=int,
        default=0,
        help="Unreported warm-up requests before each measured run.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Request timeout in seconds (default: 10).",
    )

    args = parser.parse_args()

    if args.requests <= 0:
        parser.error("--requests must be greater than 0")
    if args.concurrency <= 0:
        parser.error("--concurrency must be greater than 0")
    if args.runs <= 0:
        parser.error("--runs must be greater than 0")
    if args.warmup_requests < 0:
        parser.error("--warmup-requests cannot be negative")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")

    if args.mode == "rate-limit" and args.runs > 1:
        print(
            "WARNING: rate-limit buckets may persist in Redis between runs. "
            "Results may not be independent; use --runs 1 for a single "
            "rate-limit observation."
        )

    return args


def main() -> None:
    args = parse_args()
    asyncio.run(run_benchmarks(args))


if __name__ == "__main__":
    main()
