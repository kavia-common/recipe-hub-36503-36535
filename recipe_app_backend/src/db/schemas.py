from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, EmailStr


# Shared sub-entities

class IngredientBase(BaseModel):
    name: str = Field(..., description="Name of the ingredient")
    quantity: Optional[str] = Field(None, description="Quantity value (e.g., 2, 1/2)")
    unit: Optional[str] = Field(None, description="Unit of measurement (e.g., cups, tsp)")
    position: int = Field(0, description="Ordering position")


class IngredientCreate(IngredientBase):
    pass


class IngredientUpdate(BaseModel):
    name: Optional[str] = Field(None)
    quantity: Optional[str] = None
    unit: Optional[str] = None
    position: Optional[int] = None


class IngredientRead(IngredientBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StepBase(BaseModel):
    instruction: str = Field(..., description="Step instruction")
    position: int = Field(0, description="Ordering position")


class StepCreate(StepBase):
    pass


class StepUpdate(BaseModel):
    instruction: Optional[str] = None
    position: Optional[int] = None


class StepRead(StepBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MediaAssetBase(BaseModel):
    url: str = Field(..., description="URL to the media resource")
    media_type: str = Field("image", description="Type of media, e.g., image or video")
    alt_text: Optional[str] = Field(None, description="Accessible description of the media")
    position: int = Field(0, description="Ordering position")


class MediaAssetCreate(MediaAssetBase):
    pass


class MediaAssetUpdate(BaseModel):
    url: Optional[str] = None
    media_type: Optional[str] = None
    alt_text: Optional[str] = None
    position: Optional[int] = None


class MediaAssetRead(MediaAssetBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TagBase(BaseModel):
    name: str = Field(..., description="Tag name")
    description: Optional[str] = Field(None, description="Tag description")


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class TagRead(TagBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# User schemas

class UserBase(BaseModel):
    email: EmailStr = Field(..., description="User email")
    full_name: Optional[str] = Field(None, description="Full name")


class UserCreate(UserBase):
    password: str = Field(..., description="Plain text password for creation")


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, description="New password")


class UserRead(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Recipe schemas

class RecipeBase(BaseModel):
    title: str = Field(..., description="Recipe title")
    description: Optional[str] = None
    servings: Optional[int] = None
    prep_time_minutes: Optional[int] = None
    cook_time_minutes: Optional[int] = None


class RecipeCreate(RecipeBase):
    # Nested creates
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

    # Replace nested lists entirely on update when provided
    ingredients: Optional[List[IngredientCreate]] = None
    steps: Optional[List[StepCreate]] = None
    tags: Optional[List[TagCreate]] = None
    media_assets: Optional[List[MediaAssetCreate]] = None


class RecipeRead(RecipeBase):
    id: int
    owner_id: Optional[int] = None
    ingredients: List[IngredientRead] = Field(default_factory=list)
    steps: List[StepRead] = Field(default_factory=list)
    tags: List[TagRead] = Field(default_factory=list)
    media_assets: List[MediaAssetRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
