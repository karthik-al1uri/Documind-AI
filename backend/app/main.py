"""DocuMind AI API — skeleton."""

from fastapi import FastAPI

app = FastAPI(title="DocuMind AI", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
