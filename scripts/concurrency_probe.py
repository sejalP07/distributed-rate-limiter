import argparse
import asyncio
import statistics
import time

import httpx


async def make_request(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    request_number: int,
    url: str,
    use_identity_header: bool,
) -> float:
    async with semaphore:
        start = time.perf_counter()

        headers = {}

        if use_identity_header:
            headers["X-User-ID"] = f"probe-{request_number}"

        response = await client.get(
            url,
            headers=headers,
        )

        response.raise_for_status()

        return time.perf_counter() - start


def percentile(
    values: list[float],
    percent: float,
) -> float:
    index = int(
        (len(values) - 1) * percent
    )

    return values[index]


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure endpoint latency under controlled concurrency."
    )

    parser.add_argument(
        "--url",
        default="http://localhost:8000/health",
    )

    parser.add_argument(
        "--requests",
        type=int,
        default=200,
    )

    parser.add_argument(
        "--concurrency",
        type=int,
        default=20,
    )

    parser.add_argument(
        "--identity",
        action="store_true",
        help="Send unique X-User-ID headers.",
    )

    args = parser.parse_args()

    if args.requests <= 0:
        raise ValueError("--requests must be greater than 0")

    if args.concurrency <= 0:
        raise ValueError(
            "--concurrency must be greater than 0"
        )

    semaphore = asyncio.Semaphore(
        args.concurrency
    )

    limits = httpx.Limits(
        max_connections=args.concurrency,
        max_keepalive_connections=args.concurrency,
    )

    timeout = httpx.Timeout(
        connect=5.0,
        read=10.0,
        write=10.0,
        pool=5.0,
    )

    async with httpx.AsyncClient(
        limits=limits,
        timeout=timeout,
    ) as client:

        start = time.perf_counter()

        latencies = await asyncio.gather(
            *[
                make_request(
                    client=client,
                    semaphore=semaphore,
                    request_number=request_number,
                    url=args.url,
                    use_identity_header=args.identity,
                )
                for request_number in range(
                    args.requests
                )
            ]
        )

        duration = (
            time.perf_counter() - start
        )

    latencies_ms = sorted(
        latency * 1000
        for latency in latencies
    )

    print("=" * 60)
    print("CONCURRENCY PROBE")
    print("=" * 60)
    print(f"URL:          {args.url}")
    print(f"Requests:     {args.requests}")
    print(f"Concurrency:  {args.concurrency}")
    print(
        f"Identity:     "
        f"{'enabled' if args.identity else 'disabled'}"
    )
    print(
        f"Duration:     {duration:.4f} s"
    )
    print(
        f"Throughput:   "
        f"{args.requests / duration:.2f} req/s"
    )

    print()
    print("LATENCY")
    print("-" * 60)
    print(
        f"Average:      "
        f"{statistics.mean(latencies_ms):.2f} ms"
    )
    print(
        f"p50:          "
        f"{percentile(latencies_ms, 0.50):.2f} ms"
    )
    print(
        f"p95:          "
        f"{percentile(latencies_ms, 0.95):.2f} ms"
    )
    print(
        f"p99:          "
        f"{percentile(latencies_ms, 0.99):.2f} ms"
    )


if __name__ == "__main__":
    asyncio.run(main())