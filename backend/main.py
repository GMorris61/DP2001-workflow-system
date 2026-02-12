from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "app": "dp2001",
        "env": "local"
    }
