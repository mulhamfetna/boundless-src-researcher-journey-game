from fastapi import FastAPI

app = FastAPI(title="Gamified Quiz")


@app.get("/health")
def health():
    return {"status": "ok"}
