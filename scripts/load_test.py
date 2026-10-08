import argparse
import asyncio
import statistics
import time
from collections import Counter

import httpx


def percentile(
    values: list[float],
    percentage: float,
) -> float:
    if not values:
        return 0.0

    sorted_values = sorted(values)

    index = int(
        (percentage / 100)
        * (len(sorted_values) - 1)
    )

    return sorted_values[index]


async def send_request(
    client: httpx.AsyncClient,
    url: str,
    request_number: int,
    mode: str,
) -> tuple[int, float]:
    if mode == "throughput":
        headers = {
            "X-User-ID": f"loadtest-{request_number}",
        }

    else:
        headers = {
            "X-User-ID": "loadtest-shared-user",
        }

    start = time.perf_counter()

    try:
        response = await client.get(
            url,
            headers=headers,
        )

        latency = time.perf_counter() - start

        return response.status_code, latency

    except Exception:
        latency = time.perf_counter() - start

        return 0, latency


async def run_load_test(
    url: str,
    total_requests: int,
    concurrency: int,
    mode: str,
) -> None:
    semaphore = asyncio.Semaphore(concurrency)

    async def bounded_request(
        client: httpx.AsyncClient,
        request_number: int,
    ) -> tuple[int, float]:
        async with semaphore:
            return await send_request(
                client,
                url,
                request_number,
                mode,
            )

    limits = httpx.Limits(
        max_connections=concurrency,
        max_keepalive_connections=concurrency,
    )

    timeout = httpx.Timeout(
        10.0,
        connect=5.0,
    )

    async with httpx.AsyncClient(
        limits=limits,
        timeout=timeout,
    ) as client:
        start = time.perf_counter()

        tasks = [
            bounded_request(
                client,
                request_number,
            )
            for request_number in range(total_requests)
        ]

        results = await asyncio.gather(
            *tasks
        )

        total_duration = (
            time.perf_counter() - start
        )

    status_codes = [
        status_code
        for status_code, _ in results
    ]

    latencies = [
        latency
        for _, latency in results
    ]

    status_counts = Counter(
        status_codes
    )

    successful = status_counts.get(
        200,
        0,
    )

    rate_limited = status_counts.get(
        429,
        0,
    )

    errors = total_requests - (
        successful + rate_limited
    )

    requests_per_second = (
        total_requests / total_duration
        if total_duration > 0
        else 0
    )

    average_latency = (
        statistics.mean(latencies)
        if latencies
        else 0
    )

    print()
    print("=" * 60)
    print("DISTRIBUTED RATE LIMITER LOAD TEST")
    print("=" * 60)

    print(f"URL:              {url}")
    print(f"Mode:             {mode}")
    print(f"Requests:         {total_requests}")
    print(f"Concurrency:      {concurrency}")

    print()
    print("RESULTS")
    print("-" * 60)

    print(
        f"200 responses:    {successful}"
    )

    print(
        f"429 responses:    {rate_limited}"
    )

    print(
        f"Other errors:     {errors}"
    )

    print(
        f"Duration:         {total_duration:.4f} s"
    )

    print(
        f"Throughput:       {requests_per_second:.2f} req/s"
    )

    print()
    print("LATENCY")
    print("-" * 60)

    print(
        f"Average:          {average_latency * 1000:.2f} ms"
    )

    print(
        f"p50:              {percentile(latencies, 50) * 1000:.2f} ms"
    )

    print(
        f"p95:              {percentile(latencies, 95) * 1000:.2f} ms"
    )

    print(
        f"p99:              {percentile(latencies, 99) * 1000:.2f} ms"
    )

    print()
    print("STATUS DISTRIBUTION")
    print("-" * 60)

    for status_code, count in sorted(
        status_counts.items()
    ):
        label = (
            "network/error"
            if status_code == 0
            else str(status_code)
        )

        print(
            f"{label}:             {count}"
        )

    print("=" * 60)
    print()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Load test the distributed rate limiter gateway."
    )

    parser.add_argument(
        "--url",
        default="http://localhost:8000/api/demo",
    )

    parser.add_argument(
        "--requests",
        type=int,
        default=100,
    )

    parser.add_argument(
        "--concurrency",
        type=int,
        default=10,
    )

    parser.add_argument(
        "--mode",
        choices=[
            "throughput",
            "rate-limit",
        ],
        default="throughput",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.requests <= 0:
        raise ValueError(
            "--requests must be greater than 0"
        )

    if args.concurrency <= 0:
        raise ValueError(
            "--concurrency must be greater than 0"
        )

    asyncio.run(
        run_load_test(
            url=args.url,
            total_requests=args.requests,
            concurrency=args.concurrency,
            mode=args.mode,
        )
    )


if __name__ == "__main__":
    main()