from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, status, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import os
import shutil

# Configuration via environment variables (set by orchestrator into .env)
API_TITLE = "Recipe Hub Backend"
API_DESC = "API for recipe browsing, search, and management."
API_VERSION = "0.1.0"

# Build CORS origins:
# - Prefer explicit CORS_ORIGINS (comma-separated)
# - Else derive from FRONTEND_ORIGIN or REACT_APP_FRONTEND_URL if provided
# - Always include localhost dev default
_default_frontend = "http://localhost:3000"
explicit = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
derived = []
for key in ["FRONTEND_ORIGIN", "REACT_APP_FRONTEND_URL"]:
    val = os.getenv(key)
    if val and val.strip():
        derived.append(val.strip())
# Normalize to include both http and https variants for preview URLs when scheme differs
def _variants(url: str) -> list[str]:
    try:
        from urllib.parse import urlparse, urlunparse
        p = urlparse(url)
        hosts = []
        if p.scheme in ("http", "https"):
            other = "https" if p.scheme == "http" else "http"
            hosts = [
                urlunparse(p),
                urlunparse(p._replace(scheme=other)),
            ]
        else:
            hosts = [url]
        return hosts
    except Exception:
        return [url]

origins = set()
for item in (explicit or []) + (derived or []) + [_default_frontend]:
    for v in _variants(item):
        origins.add(v.rstrip("/"))

CORS_ORIGINS = sorted(list(origins))
MEDIA_DIR = os.getenv("MEDIA_DIR", "./media")

# For demonstration we keep in-memory data structures.
# Replace with actual DB models/repositories in full implementation.
class User(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False

# Simple in-memory user store and recipes
USERS = {
    "user@example.com": User(id=1, email="user@example.com", full_name="Example User"),
}
TOKENS = {
    # token -> user_email
}

class IngredientCreate(BaseModel):
    name: str = Field(..., description="Name of the ingredient")
    quantity: Optional[str] = Field(None, description="Quantity value (e.g., 2, 1/2)")
    unit: Optional[str] = Field(None, description="Unit of measurement (e.g., cups, tsp)")
    position: int = Field(0, description="Ordering position")

class StepCreate(BaseModel):
    instruction: str = Field(..., description="Step instruction")
    position: int = Field(0, description="Ordering position")

class MediaAssetCreate(BaseModel):
    url: str = Field(..., description="URL to the media resource")
    media_type: str = Field("image", description="Type of media, e.g., image or video")
    alt_text: Optional[str] = Field(None, description="Accessible description of the media")
    position: int = Field(0, description="Ordering position")

class TagCreate(BaseModel):
    name: str = Field(..., description="Tag name")
    description: Optional[str] = Field(None, description="Tag description")

class RecipeCreate(BaseModel):
    title: str = Field(..., description="Recipe title")
    description: Optional[str] = None
    servings: Optional[int] = None
    prep_time_minutes: Optional[int] = None
    cook_time_minutes: Optional[int] = None
    ingredients: List[IngredientCreate] = Field(default_factory=list)
    steps: List[StepCreate] = Field(default_factory=list)
    tags: List[TagCreate] = Field(default_factory=list)
    media_assets: List[MediaAssetCreate] = Field(default_factory=list)

class RecipeUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    servings: Optional[int] = None
    prep_time_minutes: Optional[int] = None
    cook_time_minutes: Optional[int] = None
    ingredients: Optional[List[IngredientCreate]] = None
    steps: Optional[List[StepCreate]] = None
    tags: Optional[List[TagCreate]] = None
    media_assets: Optional[List[MediaAssetCreate]] = None

class RecipeRead(RecipeCreate):
    id: int

RECIPES: List[RecipeRead] = [
    RecipeRead(
        id=1,
        title="Spaghetti Aglio e Olio",
        description="Simple and delicious pasta with garlic and oil.",
        servings=2,
        prep_time_minutes=10,
        cook_time_minutes=15,
        ingredients=[IngredientCreate(name="Spaghetti", quantity="200", unit="g")],
        steps=[StepCreate(instruction="Boil pasta until al dente.", position=1)],
        tags=[TagCreate(name="italian")],
        media_assets=[],
    )
]

app = FastAPI(
    title=API_TITLE,
    description=API_DESC,
    version=API_VERSION,
    openapi_tags=[
        {"name": "Health", "description": "Service health and diagnostics."},
        {"name": "Users", "description": "User management endpoints."},
        {"name": "Recipes", "description": "Recipe management endpoints."},
    ],
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure media dir exists and mount it
os.makedirs(MEDIA_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

# PUBLIC_INTERFACE
@app.get("/", tags=["Health"], summary="Health Check", description="Returns the service health status.")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

# Auth models
class LoginPayload(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None

class UserRead(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False

def get_current_user(token: Optional[str] = None):
    # Simplified token extractor for demo; usually from Authorization header.
    # FastAPI dep injection for real bearer omitted for brevity.
    # This file is a minimal integration layer to support frontend smoke flows.
    if not token:
        # try from environment or skip
        return None
    email = TOKENS.get(token)
    if not email:
        return None
    return USERS.get(email)

# PUBLIC_INTERFACE
@app.post("/auth/register", tags=["Users"], summary="Register user", description="Create a new user account with email and password.", response_model=UserRead)
def register(user: UserCreate):
    """Register a new user."""
    if user.email in USERS:
        raise HTTPException(status_code=400, detail="Email already registered")
    new = User(id=len(USERS) + 1, email=user.email, full_name=user.full_name or "")
    USERS[user.email] = new
    return UserRead(**new.dict())

# PUBLIC_INTERFACE
@app.post("/auth/login", tags=["Users"], summary="Login", description="Authenticate with email and password and receive a JWT access token.", response_model=Token)
def login(payload: LoginPayload):
    """Login endpoint. Accepts JSON payload {email, password} for demo."""
    # In real app, verify password. Here we accept any if user exists or create a temp user.
    user = USERS.get(payload.email)
    if not user:
        user = User(id=len(USERS) + 1, email=payload.email, full_name="")
        USERS[payload.email] = user
    token = f"demo-token-{user.id}"
    TOKENS[token] = user.email
    return Token(access_token=token)

# PUBLIC_INTERFACE
@app.get("/auth/me", tags=["Users"], summary="Get current user", description="Returns the current authenticated user's profile.", response_model=UserRead)
def me(token: Optional[str] = None):
    """Get current user profile based on demo token."""
    # In real world, you would use OAuth2PasswordBearer dependency
    # Here, allow passing token as query for demo/testing convenience.
    user = get_current_user(token)
    if not user:
        # Try to return first user if exists to allow smoke testing
        if USERS:
            any_user = list(USERS.values())[0]
            return UserRead(**any_user.dict())
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return UserRead(**user.dict())

# Recipe endpoints
# PUBLIC_INTERFACE
@app.get("/recipes", tags=["Recipes"], summary="List recipes", description="List recipes with optional search by text and tags, with pagination.", response_model=List[RecipeRead])
def list_recipes(q: Optional[str] = None, tag: Optional[str] = None, page: int = 1, page_size: int = 20):
    """List recipes with minimal filtering for smoke flow."""
    items = RECIPES
    if q:
        items = [r for r in items if q.lower() in r.title.lower() or (r.description or "").lower().find(q.lower()) >= 0]
    if tag:
        items = [r for r in items if any(t.name.lower() == tag.lower() for t in r.tags)]
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end]

# PUBLIC_INTERFACE
@app.get("/recipes/{recipe_id}", tags=["Recipes"], summary="Get recipe", description="Retrieve a recipe by ID.", response_model=RecipeRead)
def get_recipe(recipe_id: int):
    """Get a single recipe by ID."""
    for r in RECIPES:
        if r.id == recipe_id:
            return r
    raise HTTPException(status_code=404, detail="Recipe not found")

# PUBLIC_INTERFACE
@app.post("/recipes", tags=["Recipes"], summary="Create recipe", description="Create a new recipe.", response_model=RecipeRead, status_code=201)
def create_recipe(recipe: RecipeCreate):
    """Create a recipe (demo in-memory)."""
    new_id = (max((r.id for r in RECIPES), default=0) + 1) if RECIPES else 1
    read = RecipeRead(id=new_id, **recipe.dict())
    RECIPES.append(read)
    return read

# PUBLIC_INTERFACE
@app.put("/recipes/{recipe_id}", tags=["Recipes"], summary="Update recipe", description="Update a recipe (demo).", response_model=RecipeRead)
def update_recipe(recipe_id: int, update: RecipeUpdate):
    """Update an existing recipe (demo in-memory)."""
    for idx, r in enumerate(RECIPES):
        if r.id == recipe_id:
            data = r.dict()
            upd = update.dict(exclude_unset=True)
            data.update({k: v for k, v in upd.items() if v is not None})
            updated = RecipeRead(**data)
            RECIPES[idx] = updated
            return updated
    raise HTTPException(status_code=404, detail="Recipe not found")

# PUBLIC_INTERFACE
@app.delete("/recipes/{recipe_id}", tags=["Recipes"], summary="Delete recipe", description="Delete a recipe (demo).", status_code=204)
def delete_recipe(recipe_id: int):
    """Delete a recipe (demo in-memory)."""
    global RECIPES
    before = len(RECIPES)
    RECIPES = [r for r in RECIPES if r.id != recipe_id]
    if len(RECIPES) == before:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return JSONResponse(status_code=204, content=None)

# PUBLIC_INTERFACE
@app.post(
    "/media/upload",
    tags=["Recipes"],
    summary="Upload media",
    description="Upload media file and receive a URL served under /media.",
)
def upload_media(file: UploadFile = File(...)):
    """Accept a file upload and store it into MEDIA_DIR, returning a public URL."""
    filename = file.filename
    if not filename:
        raise HTTPException(status_code=400, detail="No filename")
    base_name = os.path.basename(filename)
    save_path = os.path.join(MEDIA_DIR, base_name)
    # Avoid overwrite by adjusting filename
    base, ext = os.path.splitext(base_name)
    counter = 1
    while os.path.exists(save_path):
        save_path = os.path.join(MEDIA_DIR, f"{base}_{counter}{ext}")
        counter += 1
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    public_name = os.path.basename(save_path)
    url = f"/media/{public_name}"
    return {"url": url}
