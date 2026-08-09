from fastapi import FastAPI
from app.api.routes.session import router as session_router

app = FastAPI(title="Session Context Tracking API", version="1.0.0")

app.include_router(session_router)

@app.get("/")
def root():
    return {"message": "Session Context Tracking API"}
