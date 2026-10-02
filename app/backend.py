from fastapi import FastAPI


app = FastAPI(
    title="Rate Limiter Backend Service",
    version="1.0.0",
)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "backend",
    }


@app.get("/demo")
async def demo():
    return {
        "message": "Response came from backend",
        "service": "backend",
    }


@app.get("/search")
async def search():
    return {
        "message": "Search response came from backend",
        "service": "backend",
    }


@app.get("/upload")
async def upload():
    return {
        "message": "Upload response came from backend",
        "service": "backend",
    }