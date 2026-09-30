from fastapi import FastAPI

app = FastAPI(
    title="Distributed Rate Limiter & API Gateway",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy"
    }