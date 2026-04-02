from fastapi import FastAPI

app = FastAPI(title="xhs-ai-bot orchestrator")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
