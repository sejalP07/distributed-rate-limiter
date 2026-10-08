from prometheus_client import Counter, Histogram


GATEWAY_REQUESTS = Counter(
    "gateway_requests_total",
    "Total API gateway requests by final status class.",
    labelnames=["status_class"],
)


RATE_LIMIT_REJECTIONS = Counter(
    "gateway_rate_limit_rejections_total",
    "Total requests rejected by the rate limiter.",
    labelnames=["policy"],
)


AUTH_FAILURES = Counter(
    "gateway_auth_failures_total",
    "Total invalid or inactive API-key authentication attempts.",
)


DEPENDENCY_ERRORS = Counter(
    "gateway_dependency_errors_total",
    "Total gateway dependency failures.",
    labelnames=["dependency"],
)


REQUEST_LATENCY = Histogram(
    "gateway_request_latency_seconds",
    "API gateway request latency in seconds.",
    buckets=[
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
    ],
)

REDIS_LATENCY = Histogram(
    "gateway_redis_latency_seconds",
    "Time spent performing Redis rate-limit operations.",
    buckets=[
        0.001, 0.002, 0.005, 0.01,
        0.025, 0.05, 0.1, 0.25,
        0.5, 1.0,
    ],
)

BACKEND_LATENCY = Histogram(
    "gateway_backend_latency_seconds",
    "Time spent waiting for the backend service.",
    buckets=[
        0.001, 0.002, 0.005, 0.01,
        0.025, 0.05, 0.1, 0.25,
        0.5, 1.0, 2.5, 5.0,
        10.0,
    ],
)