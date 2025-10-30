from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from src.api.routes_auth import get_current_user
from src.db.models import Ingredient, MediaAsset, Recipe, Tag, User, Step
from src.db.schemas import RecipeCreate, RecipeRead, RecipeUpdate
from src.db.session import get_db

router = APIRouter(prefix="/recipes", tags=["Recipes"])


def _apply_search_filters(query, q: Optional[str], tags: Optional[List[str]]):
    if q:
        ilike = f"%{q}%"
        query = query.filter((Recipe.title.ilike(ilike)) | (Recipe.description.ilike(ilike)))
    if tags:
        # join through tags
        query = query.join(Recipe.tags).filter(func.lower(Tag.name).in_([t.lower() for t in tags]))
    return query


def _paginate(query, page: int, page_size: int) -> Tuple[List[Recipe], int]:
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def _replace_children(db: Session, recipe: Recipe, data: RecipeUpdate | RecipeCreate):
    # Replace ingredients
    if getattr(data, "ingredients", None) is not None:
        recipe.ingredients.clear()
        for idx, ing in enumerate(data.ingredients):
            recipe.ingredients.append(
                Ingredient(
                    name=ing.name,
                    quantity=ing.quantity,
                    unit=ing.unit,
                    position=ing.position if ing.position is not None else idx,
                )
            )
    # Replace steps
    if getattr(data, "steps", None) is not None:
        recipe.steps.clear()
        for idx, st in enumerate(data.steps):
            recipe.steps.append(Step(instruction=st.instruction, position=st.position if st.position is not None else idx))
    # Replace media assets (note: upload endpoint can also add)
    if getattr(data, "media_assets", None) is not None:
        recipe.media_assets.clear()
        for idx, m in enumerate(data.media_assets):
            recipe.media_assets.append(
                MediaAsset(url=m.url, media_type=m.media_type, alt_text=m.alt_text, position=m.position or idx)
            )
    # Replace tags with upserted tag names
    if getattr(data, "tags", None) is not None:
        recipe.tags.clear()
        for t in data.tags:
            tag = db.query(Tag).filter(func.lower(Tag.name) == t.name.lower()).first()
            if not tag:
                tag = Tag(name=t.name, description=t.description)
                db.add(tag)
                db.flush()
            recipe.tags.append(tag)


@router.get(
    "",
    response_model=List[RecipeRead],
    summary="List recipes",
    description="List recipes with optional search by text and tags, with pagination.",
)
def list_recipes(
    q: Optional[str] = Query(None, description="Free text search in title and description"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    query = db.query(Recipe).options(
        joinedload(Recipe.ingredients), joinedload(Recipe.steps), joinedload(Recipe.media_assets), joinedload(Recipe.tags)
    )

    # For now, list all recipes. If in future we add a "shared" flag, we can filter non-owned by that.
    query = _apply_search_filters(query, q, tags)
    items, _ = _paginate(query.order_by(Recipe.created_at.desc()), page, page_size)
    return items


@router.get(
    "/{recipe_id}",
    response_model=RecipeRead,
    summary="Get recipe",
    description="Retrieve a recipe by ID.",
)
def get_recipe(recipe_id: int, db: Session = Depends(get_db), current_user: Optional[User] = Depends(get_current_user)):
    recipe = (
        db.query(Recipe)
        .options(joinedload(Recipe.ingredients), joinedload(Recipe.steps), joinedload(Recipe.media_assets), joinedload(Recipe.tags))
        .filter(Recipe.id == recipe_id)
        .first()
    )
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    return recipe


@router.post(
    "",
    response_model=RecipeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create recipe",
    description="Create a new recipe owned by the authenticated user.",
)
def create_recipe(payload: RecipeCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    recipe = Recipe(
        title=payload.title,
        description=payload.description,
        servings=payload.servings,
        prep_time_minutes=payload.prep_time_minutes,
        cook_time_minutes=payload.cook_time_minutes,
        owner_id=current_user.id,
    )
    db.add(recipe)
    db.flush()
    _replace_children(db, recipe, payload)
    db.commit()
    db.refresh(recipe)
    return recipe


@router.put(
    "/{recipe_id}",
    response_model=RecipeRead,
    summary="Update recipe",
    description="Update a recipe. Only the owner can update.",
)
def update_recipe(
    recipe_id: int,
    payload: RecipeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    if recipe.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")

    for field in ["title", "description", "servings", "prep_time_minutes", "cook_time_minutes"]:
        val = getattr(payload, field)
        if val is not None:
            setattr(recipe, field, val)

    _replace_children(db, recipe, payload)
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


@router.delete(
    "/{recipe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete recipe",
    description="Delete a recipe. Only the owner can delete.",
)
def delete_recipe(recipe_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    if recipe.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")
    db.delete(recipe)
    db.commit()
    return


@router.post(
    "/{recipe_id}/share",
    summary="Toggle share",
    description="Toggle sharing a recipe (no-op field for now, but endpoint exists for future logic).",
)
def toggle_share(recipe_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Placeholder: could add is_shared field in future. Currently just ensures ownership.
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    if recipe.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")
    return {"status": "ok"}
