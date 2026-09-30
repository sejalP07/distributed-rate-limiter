# Distributed Rate Limiter & API Gateway

A production-style distributed API gateway built with **FastAPI, Redis, Token Bucket rate limiting, PostgreSQL, Docker, monitoring, and automated testing**.

The gateway sits in front of backend services and controls how many requests a client can make within a given period. Requests within the configured limit are allowed to continue to the backend, while excessive traffic is rejected with **HTTP 429 Too Many Requests**.

The system is designed around **shared Redis rate-limit state** so multiple gateway instances can enforce a consistent policy.

---

## Project Status

| Step    | Component                       | Status         |
| ------- | ------------------------------- | -------------- |
| Step 1  | FastAPI Gateway Foundation      | ✅ Complete     |
| Step 2  | Redis Integration               | ✅ Complete     |
| Step 3A | In-Memory Token Bucket          | ✅ Complete     |
| Step 3B | Redis-Backed Token Bucket       | ✅ Complete     |
| Step 4  | FastAPI Rate-Limit Middleware   | 🚧 In Progress |
| Step 5  | Backend Proxy / Gateway Routing | ⏳ Planned      |
| Step 6  | PostgreSQL                      | ⏳ Planned      |
| Step 7  | API Key Authentication          | ⏳ Planned      |
| Step 8  | Configurable Rate Policies      | ⏳ Planned      |
| Step 9  | Logging                         | ⏳ Planned      |
| Step 10 | Prometheus + Grafana            | ⏳ Planned      |
| Step 11 | Automated Integration Tests     | ⏳ Planned      |
| Step 12 | Load Testing & Benchmarking     | ⏳ Planned      |
| Step 13 | Failure Handling                | ⏳ Planned      |
| Step 14 | Multi-Gateway Deployment        | ⏳ Planned      |

---

# 1. Problem Statement

Public APIs can become overloaded or abused when clients send excessive numbers of requests.

This project builds a distributed API gateway that:

* identifies the client
* applies a rate-limit policy
* maintains shared rate-limit state in Redis
* allows requests within the configured limit
* rejects excessive requests with HTTP 429
* communicates rate-limit information through response headers
* eventually supports users, API keys, IP-based policies, and endpoint-specific policies
* provides testing, benchmarking, logging, and monitoring

The project requirements include shared Redis state, configurable limits, concurrent-request safety, rejected-request handling, and observability.

---

# 2. High-Level Architecture

Current architecture:

```text
                    ┌─────────────────────┐
                    │      Client         │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   FastAPI Gateway   │
                    │                     │
                    │ Rate-Limit          │
                    │ Middleware          │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Redis Token Bucket  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │       Redis         │
                    │ Shared State Store  │
                    └─────────────────────┘
```

Planned final architecture:

```text
                         Client
                           │
                           ▼
                  ┌─────────────────┐
                  │  API Gateway    │
                  │    FastAPI      │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Rate Limiter    │
                  │ Token Bucket     │
                  └────────┬────────┘
                           │
                           ▼
                        Redis
                           │
                    ┌──────┴──────┐
                    │             │
                 Allowed       Rejected
                    │             │
                    ▼             ▼
              Backend APIs       429
                    │
                    ▼
               PostgreSQL
```

---

# 3. Technology Stack

## FastAPI

Used to build the API gateway and HTTP endpoints.

### Why?

* Python-based
* clean API development
* asynchronous request handling
* automatic OpenAPI/Swagger documentation
* works well with Redis and other asynchronous services

---

## Uvicorn

Used to run the FastAPI application.

```text
FastAPI = Application
Uvicorn = ASGI Server
```

---

## Redis

Used for shared, fast-changing rate-limit state.

Example future bucket state:

```text
rate_limit:ip:10.0.0.1

tokens = 7
last_refill_ms = ...
```

Redis is important because multiple gateway instances need a shared state instead of maintaining independent counters.

---

## Token Bucket

Used as the rate-limiting algorithm.

A bucket contains a limited number of tokens.

Example:

```text
capacity = 5
refill_rate = 1 token/second
```

A request consumes one token.

```text
5 → 4 → 3 → 2 → 1 → 0
```

When no tokens are available:

```text
Request
   ↓
No token
   ↓
429
```

Tokens are gradually refilled based on elapsed time.

---

## PostgreSQL

Planned as the persistent database.

Expected responsibilities:

```text
Users
API Keys
Rate-Limit Policies
Persistent Configuration
Audit/Persistent Logs
```

PostgreSQL will be kept separate from Redis because Redis handles the frequently changing rate-limiter state while PostgreSQL stores persistent application data.

---

## Docker

Used to package and run the application consistently.

---

## Docker Compose

Used to run multiple services together.

Current:

```text
FastAPI
Redis
```

Planned:

```text
FastAPI
Redis
PostgreSQL
Prometheus
Grafana
```

---

## Pytest

Used for automated testing.

---

## Prometheus

Planned for collecting application metrics.

---

## Grafana

Planned for visualization and dashboards.

---

# 4. Rate-Limiting Strategy

## Token Bucket

The Token Bucket maintains:

```text
capacity
current tokens
refill rate
last refill time
```

The refill calculation is conceptually:

```text
new_tokens =
min(
    capacity,
    current_tokens + elapsed_time × refill_rate
)
```

A request is allowed when enough tokens are available.

```text
tokens >= requested_tokens
        │
     ┌──┴──┐
     │     │
    YES    NO
     │     │
    ALLOW  REJECT
```

---

# 5. Distributed Rate Limiting

A single-process in-memory limiter is not sufficient for a distributed gateway.

Example:

```text
                ┌── Gateway 1 ──┐
                │               │
Client ─────────┼── Gateway 2 ──┼──► Redis
                │               │
                └── Gateway 3 ──┘
```

All gateways use the same Redis state.

This prevents each gateway from maintaining an independent limit.

---

# 6. Atomic Redis Operation

The Redis-backed Token Bucket uses a Redis Lua script.

The rate-limit decision is performed as one Redis-side operation:

```text
Read bucket state
       ↓
Get Redis server time
       ↓
Calculate elapsed time
       ↓
Refill tokens
       ↓
Check requested tokens
       ↓
Consume tokens if allowed
       ↓
Save new state
       ↓
Return decision
```

This avoids splitting the operation into independent:

```text
GET
calculate
SET
```

operations.

That is important for concurrent requests because two requests arriving at almost the same time must not incorrectly consume the same token.

---

# 7. Current Project Structure

```text
distributed-rate-limiter/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── redis.py
│   ├── token_bucket.py
│   ├── redis_token_bucket.py
│   └── rate_limit_middleware.py
│
├── tests/
│   ├── __init__.py
│   ├── test_health.py
│   ├── test_token_bucket.py
│   └── test_redis_token_bucket.py
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .dockerignore
├── .gitignore
└── README.md
```

---

# 8. Application Components

## `app/main.py`

Contains:

* FastAPI application
* health endpoint
* Redis health endpoint
* Redis test endpoint
* demo API endpoint
* rate-limit middleware registration

---

## `app/redis.py`

Responsible for:

* Redis client creation
* Redis URL configuration
* asynchronous Redis connection

Configuration uses:

```text
REDIS_URL
```

Example inside Docker Compose:

```text
redis://redis:6379
```

---

## `app/token_bucket.py`

Contains the pure Python Token Bucket implementation.

It is intentionally independent of:

* FastAPI
* Redis
* HTTP responses

This makes the algorithm easy to test.

---

## `app/redis_token_bucket.py`

Contains the distributed Redis-backed Token Bucket.

Responsibilities:

* Redis bucket state
* token refill
* token consumption
* Redis Lua execution
* atomic rate-limit decisions

---

## `app/rate_limit_middleware.py`

Connects the Redis-backed Token Bucket to FastAPI.

Current policy:

```text
Client identity = IP address

Capacity = 5 tokens

Refill = 1 token/second
```

Only `/api/*` routes are currently rate limited.

---

# 9. Current API Endpoints

## Health

```http
GET /health
```

Response:

```json
{
  "status": "healthy"
}
```

---

## Redis Health

```http
GET /health/redis
```

Example response:

```json
{
  "status": "healthy",
  "redis": true
}
```

---

## Redis Test

```http
GET /redis/test
```

Example response:

```json
{
  "status": "success",
  "redis_key": "rate_limiter:test",
  "redis_value": "hello"
}
```

---

## Protected Demo API

```http
GET /api/demo
```

Example successful response:

```json
{
  "message": "Request passed the rate limiter"
}
```

---

# 10. Rate-Limit Response Headers

Successful protected responses expose:

```text
X-RateLimit-Limit
X-RateLimit-Remaining
```

Rejected requests additionally expose:

```text
Retry-After
```

Example:

```http
HTTP/1.1 429 Too Many Requests

X-RateLimit-Limit: 5
X-RateLimit-Remaining: 0
Retry-After: 1
```

Example response:

```json
{
  "detail": "Rate limit exceeded",
  "retry_after_seconds": 1
}
```

The project requirements include HTTP 429 responses and rate-limit information for clients.

---

# 11. Local Development

## Create virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

---

## Install dependencies

```powershell
python -m pip install -r requirements.txt
```

---

# 12. Run with Docker Compose

Build and start the services:

```powershell
docker compose up --build
```

Or run in the background:

```powershell
docker compose up -d --build
```

Check the services:

```powershell
docker compose ps
```

Expected:

```text
API     → Up
Redis   → Up (healthy)
```

---

# 13. Test the Application

Open:

```text
http://localhost:8000/health
```

Then:

```text
http://localhost:8000/health/redis
```

Then:

```text
http://localhost:8000/redis/test
```

Then:

```text
http://localhost:8000/api/demo
```

Swagger documentation:

```text
http://localhost:8000/docs
```

---

# 14. Testing

Run the complete test suite inside Docker:

```powershell
docker compose exec api python -m pytest
```

The test suite currently covers:

```text
FastAPI health
Token Bucket behavior
Token consumption
Token refill
Bucket capacity
Invalid inputs
Redis-backed rate limiting
Shared Redis state
Concurrent requests
```

Current verified result:

```text
15 passed
```

---

# 15. Concurrency Testing

The Redis-backed Token Bucket includes a concurrent-request test.

Example:

```text
Capacity = 10
Concurrent requests = 50
```

Expected:

```text
10 requests → ALLOWED
40 requests → REJECTED
```

This demonstrates that the Redis-side atomic operation prevents multiple concurrent requests from incorrectly consuming the same token.

---

# 16. Failure Handling

The gateway explicitly considers dependency failures.

For example:

```text
Client
  ↓
FastAPI
  ↓
Redis
  X
```

The current protected API behavior is:

```text
Rate limiter unavailable
        ↓
HTTP 503
```

The project roadmap identifies Redis failure, concurrent requests, high traffic, multiple gateway instances, and retry behavior as engineering failure cases to address.

---

# 17. Future Client Identification

The current MVP uses IP address identification.

Planned identity types:

```text
IP address
User ID
API key
```

Examples:

```text
IP 10.0.0.1
→ 100 requests/min

User 501
→ 1,000 requests/min

API_KEY_A
→ 5,000 requests/hour
```

These identification methods are part of the project requirements.

---

# 18. Future Configurable Policies

The initial policy is intentionally fixed:

```text
capacity = 5
refill = 1/sec
```

The final system will support configurable policies such as:

```text
100 requests/minute
1,000 requests/hour
5,000 requests/day
```

Potential endpoint-specific policies:

```text
GET  /products  → 1000/min
POST /orders    → 100/min
POST /payments  → 20/min
```

The roadmap specifically calls for flexible rate-limit configuration and different policies for different endpoints or clients.

---

# 19. Planned PostgreSQL Model

PostgreSQL will eventually contain persistent data such as:

```text
users
api_keys
rate_limit_policies
audit_logs
```

Example conceptual relationship:

```text
User
 │
 ├── API Keys
 │
 └── Rate Limit Policy
```

Redis will remain responsible for high-frequency Token Bucket state.

---

# 20. Planned Monitoring

The monitoring layer will eventually collect:

```text
Requests received
Requests allowed
Requests rejected
Request latency
Rate-limit usage
Redis errors
Application errors
```

The project requirements explicitly include observability for allowed/rejected requests, usage, latency, and errors.

Planned stack:

```text
FastAPI
   ↓
Prometheus
   ↓
Grafana
```

---

# 21. Planned Load Testing

After the gateway is fully implemented, the project will be benchmarked under increasing traffic.

Example scenarios:

```text
100 requests
1,000 requests
10,000 requests
```

Measurements will include:

```text
Throughput
Latency
Allowed requests
Rejected requests
Redis performance
Error rate
```

The goal is to provide measurable evidence rather than only demonstrating that the API works.

---

# 22. Planned Distributed Deployment

The final development environment will be able to run multiple gateway instances:

```text
              ┌── Gateway 1 ──┐
Client ───────┼── Gateway 2 ──┼──► Redis
              └── Gateway 3 ──┘
```

All instances will use shared Redis state.

This is what makes the rate limiter distributed.

---

# 23. Development Approach

The project is being developed incrementally:

```text
Problem
   ↓
Requirements
   ↓
Architecture
   ↓
FastAPI Foundation
   ↓
Redis
   ↓
Token Bucket
   ↓
Redis-backed Token Bucket
   ↓
Gateway Middleware
   ↓
Backend Proxy
   ↓
PostgreSQL
   ↓
Authentication
   ↓
Monitoring
   ↓
Testing
   ↓
Load Testing
   ↓
Failure Handling
   ↓
Multi-Gateway Deployment
```

This approach isolates each major engineering concern and verifies it before adding the next layer.

---

# 24. Git Development History

The project is developed using incremental commits.

Current milestone history:

```text
feat: initialize FastAPI gateway
        ↓
feat: add Redis integration
        ↓
feat: implement token bucket rate limiter
        ↓
feat: add Redis-backed token bucket
        ↓
feat: add FastAPI rate limiting middleware
```

Each commit represents a meaningful implementation milestone.

---

# 25. Security Considerations

Future security work will include:

* API key authentication
* secure secret management
* trusted proxy handling
* client identity validation
* protection against rate-limit bypass
* input validation
* Redis access control
* safe configuration handling

Clients should not be able to manipulate request metadata to bypass rate limits.

---

# 26. Current Limitations

This project is being developed incrementally.

Current limitations include:

* IP-based identification is currently the MVP
* PostgreSQL persistence is not yet implemented
* API-key authentication is not yet implemented
* monitoring dashboards are not yet implemented
* load testing is not yet implemented
* multi-instance gateway deployment is not yet implemented
* production proxy/trusted-IP handling is not yet implemented

These are planned engineering stages rather than missing pieces of the current MVP.

---

# 27. Roadmap

## Phase 1 — Foundation

* [x] FastAPI
* [x] Docker
* [x] Health endpoint
* [x] Git/GitHub

## Phase 2 — Redis

* [x] Redis
* [x] Redis client
* [x] Docker Compose
* [x] Redis health check
* [x] Redis read/write test

## Phase 3 — Rate Limiting

* [x] Token Bucket
* [x] Unit tests
* [x] Redis-backed Token Bucket
* [x] Lua atomic operation
* [x] Concurrent-request test

## Phase 4 — Gateway

* [x] FastAPI middleware
* [x] IP-based identification
* [x] HTTP 429
* [x] Rate-limit headers
* [ ] Backend proxy

## Phase 5 — Persistence & Authentication

* [ ] PostgreSQL
* [ ] Users
* [ ] API keys
* [ ] Rate-limit policies
* [ ] Authentication

## Phase 6 — Observability

* [ ] Structured logging
* [ ] Prometheus metrics
* [ ] Grafana dashboard

## Phase 7 — Performance

* [ ] Load testing
* [ ] Benchmarking
* [ ] Latency measurements
* [ ] Throughput measurements

## Phase 8 — Distributed Engineering

* [ ] Multiple gateway instances
* [ ] Redis failure strategy
* [ ] Retry behavior
* [ ] High-traffic testing
* [ ] Production hardening

---

# 28. Learning Goals

This project is designed to demonstrate practical understanding of:

```text
FastAPI
Redis
Token Bucket
Lua
Atomic operations
Concurrency
Docker
Docker Compose
REST APIs
Middleware
PostgreSQL
Authentication
Testing
Load testing
Monitoring
Distributed systems
```

---

# 29. Quick Start

Clone the repository:

```bash
git clone https://github.com/sejalP07/distributed-rate-limiter.git
cd distributed-rate-limiter
```

Create and activate the virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Start Docker Compose:

```powershell
docker compose up -d --build
```

Check services:

```powershell
docker compose ps
```

Run tests:

```powershell
docker compose exec api python -m pytest
```

Open Swagger:

```text
http://localhost:8000/docs
```

Test the protected endpoint:

```text
http://localhost:8000/api/demo
```

---

# 30. Project Goal

The final goal is to build a reliable distributed API gateway that can:

```text
Receive request
      ↓
Identify client
      ↓
Find rate-limit policy
      ↓
Check shared Redis Token Bucket
      ↓
       ┌─────────────┐
       │   Allowed?  │
       └──────┬──────┘
          YES │ NO
              │
         ┌────┴────┐
         ▼         ▼
      Backend      429
         │
         ▼
    PostgreSQL

         +
     Monitoring
         +
       Testing
         +
   Load Benchmarking
```

The project is being built incrementally so every major layer can be understood, tested, measured, and committed independently.
