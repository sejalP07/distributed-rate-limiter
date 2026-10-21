
import argparse
import asyncio
import math
import statistics
import time
from collections import Counter

import httpx


def percentile(values: list[float], percentage: float) -> float:
    if not values:
        return 0.0

    ordered = sorted(values)
    index = max(
        0,
        min(
            len(ordered) - 1,
            math.ceil(percentage / 100 * len(ordered)) - 1,
        ),
    )
    return ordered[index]


async def send_request(
    client: httpx.AsyncClient,
    url: str,
    user_id: str,
) -> tuple[int, float, str | None]:
    start = time.perf_counter()

    try:
        response = await client.get(
            url,
            headers={"X-User-ID": user_id},
        )
        return (
            response.status_code,
            time.perf_counter() - start,
            None,
        )
    except httpx.RequestError as exc:
        return (
            0,
            time.perf_counter() - start,
            type(exc).__name__,
        )


async def run_test(args: argparse.Namespace) -> None:
    limits = httpx.Limits(
        max_connections=args.concurrency,
        max_keepalive_connections=args.concurrency,
    )
    timeout = httpx.Timeout(
        args.timeout,
        connect=min(5.0, args.timeout),
    )

    results: list[tuple[int, float, str | None]] = []
    request_number = 0

    async with httpx.AsyncClient(
        limits=limits,
        timeout=timeout,
    ) as client:
        # Warm up the connection and application before measuring.
        for i in range(args.warmup_requests):
            warmup_user = (
                f"sustained-warmup-{i}"
                if args.mode == "throughput"
                else "sustained-warmup-shared"
            )
            await send_request(client, args.url, warmup_user)

        deadline = time.perf_counter() + args.duration
        start = time.perf_counter()

        async def worker(worker_id: int) -> None:
            nonlocal request_number

            while time.perf_counter() < deadline:
                current_number = request_number
                request_number += 1

                if args.mode == "throughput":
                    user_id = f"sustained-user-{current_number}"
                else:
                    user_id = "sustained-shared-user"

                result = await send_request(
                    client,
                    args.url,
                    user_id,
                )
                results.append(result)

        await asyncio.gather(
            *(worker(i) for i in range(args.concurrency))
        )

        elapsed = time.perf_counter() - start

    statuses = Counter(status for status, _, _ in results)
    latency_ms = [latency * 1000 for _, latency, _ in results]

    successful = sum(200 <= status < 300 for status, _, _ in results)
    rate_limited = statuses.get(429, 0)
    errors = len(results) - successful - rate_limited

    print("\n" + "=" * 64)
    print("SUSTAINED LOAD TEST")
    print("=" * 64)
    print(f"URL:                  {args.url}")
    print(f"Mode:                 {args.mode}")
    print(f"Target duration:      {args.duration:.1f} s")
    print(f"Actual elapsed:       {elapsed:.2f} s")
    print(f"Concurrency:          {args.concurrency}")
    print(f"Completed requests:   {len(results)}")
    print(
        f"Throughput:           "
        f"{len(results) / elapsed if elapsed else 0:.2f} req/s"
    )
    print(f"Successful (2xx):     {successful}")
    print(f"Rate limited (429):   {rate_limited}")
    print(f"Other errors:         {errors}")

    print("\nLATENCY")
    print("-" * 64)
    print(
        f"Average:              "
        f"{statistics.mean(latency_ms) if latency_ms else 0:.2f} ms"
    )
    print(f"P50:                  {percentile(latency_ms, 50):.2f} ms")
    print(f"P95:                  {percentile(latency_ms, 95):.2f} ms")
    print(f"P99:                  {percentile(latency_ms, 99):.2f} ms")

    print("\nSTATUS DISTRIBUTION")
    print("-" * 64)
    for status, count in sorted(statuses.items()):
        print(f"{'network/error' if status == 0 else status}: {count}")

    print("\nNETWORK ERROR TYPES")
    print("-" * 64)
    error_types = Counter(
        error for _, _, error in results if error is not None
    )
    if error_types:
        for error, count in error_types.items():
            print(f"{error}: {count}")
    else:
        print("None")

    print("=" * 64)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a timed sustained-load test against the gateway."
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000/api/demo",
    )
    parser.add_argument("--duration", type=float, default=300)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--warmup-requests", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument(
        "--mode",
        choices=["throughput", "rate-limit"],
        default="throughput",
    )

    args = parser.parse_args()

    if args.duration <= 0:
        parser.error("--duration must be greater than 0")
    if args.concurrency <= 0:
        parser.error("--concurrency must be greater than 0")
    if args.warmup_requests < 0:
        parser.error("--warmup-requests cannot be negative")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")

    return args


if __name__ == "__main__":
    asyncio.run(run_test(parse_args()))
