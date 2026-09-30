# Distributed Rate Limiter & API Gateway

A distributed API gateway built with FastAPI, Redis, PostgreSQL, Docker, Token Bucket rate limiting, monitoring, and automated testing.

## Current Progress

### Step 1 — FastAPI Gateway Foundation

- FastAPI application created
- Health endpoint implemented
- Swagger API documentation enabled
- Docker container created
- FastAPI successfully running inside Docker

## Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload