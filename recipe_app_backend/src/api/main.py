from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.db.session import Base, engine

settings = get_settings()

openapi_tags = [
    {"name": "Health", "description": "Service health and diagnostics."},
    {"name": "Users", "description": "User management endpoints."},
    {"name": "Recipes", "description": "Recipe management endpoints."},
]

app = FastAPI(
    title=settings.app_name,
    description="API for recipe browsing, search, and management.",
    version="0.1.0",
    openapi_tags=openapi_tags,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this via environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    """Create tables on startup for initial bootstrap."""
    # When using SQLite file path, ensure directory exists
    import os
    db_url = settings.database_url
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "", 1)
        dir_path = os.path.dirname(db_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
    Base.metadata.create_all(bind=engine)


@app.get("/", tags=["Health"], summary="Health Check", description="Returns the service health status.")
def health_check():
    return {"message": "Healthy"}
