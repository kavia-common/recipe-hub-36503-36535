from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routes_auth import router as auth_router
from src.api.routes_media import router as media_router
from src.api.routes_recipes import router as recipes_router
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

# CORS
allow_origins = ["*"]
if settings.frontend_origin:
    allow_origins = [settings.frontend_origin]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    """Create tables on startup for initial bootstrap and ensure media dir exists."""
    # When using SQLite file path, ensure directory exists
    import os
    db_url = settings.database_url
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "", 1)
        dir_path = os.path.dirname(db_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
    Base.metadata.create_all(bind=engine)

    # Ensure media dir exists
    os.makedirs(settings.media_dir, exist_ok=True)


@app.get("/", tags=["Health"], summary="Health Check", description="Returns the service health status.")
def health_check():
    """Health check endpoint returning a simple JSON message."""
    return {"message": "Healthy"}


# Mount static for media
app.mount(settings.media_url_prefix, StaticFiles(directory=settings.media_dir), name="media")

# Routers
app.include_router(auth_router)
app.include_router(recipes_router)
app.include_router(media_router)
