import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.api.routes_auth import get_current_user
from src.core.config import get_settings
from src.db.models import MediaAsset, Recipe, User
from src.db.session import get_db

router = APIRouter(prefix="/media", tags=["Recipes"])


@router.post(
    "/upload",
    summary="Upload media",
    description="Upload media file and optionally attach to a recipe as a MediaAsset.",
)
async def upload_media(
    file: UploadFile = File(...),
    recipe_id: Optional[int] = None,
    alt_text: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settings = get_settings()
    os.makedirs(settings.media_dir, exist_ok=True)

    # Basic content-type validation
    content_type = file.content_type or ""
    if not (content_type.startswith("image/") or content_type.startswith("video/")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported content type")

    # Save the file
    ext = os.path.splitext(file.filename or "")[1]
    fname = f"{uuid.uuid4().hex}{ext}"
    abs_path = os.path.join(settings.media_dir, fname)
    with open(abs_path, "wb") as out:
        out.write(await file.read())

    url = f"{settings.media_url_prefix}/{fname}"

    media_asset = None
    if recipe_id:
        recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
        if not recipe:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
        if recipe.owner_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")
        media_asset = MediaAsset(url=url, media_type="image" if content_type.startswith("image/") else "video", alt_text=alt_text)
        recipe.media_assets.append(media_asset)
        db.add(recipe)
        db.commit()
        db.refresh(recipe)

    return JSONResponse({"url": url, "attached": bool(media_asset), "filename": fname})
