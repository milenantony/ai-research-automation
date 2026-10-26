from fastapi import FastAPI

from app.api.routes.research import router as research_router

app = FastAPI(
    title="AI Research Automation System",
    description="An AI-powered academic research automation platform",
    version="0.1.0",
)


app.include_router(research_router)


@app.get("/")
def root():
    return {
        "message": "AI Research Automation System API is running"
    }