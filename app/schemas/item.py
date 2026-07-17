from pydantic import BaseModel, ConfigDict, Field


class ItemBase(BaseModel):
    title: str = Field(..., max_length=255, description="The title of the item")
    description: str | None = Field(default=None, description="Detailed description of the item")


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255, description="Updated title of the item")
    description: str | None = Field(default=None, description="Updated description of the item")
    is_active: bool | None = Field(default=None, description="Status of the item")


class ItemInDBBase(ItemBase):
    id: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ItemResponse(ItemInDBBase):
    """Schema returned to API clients."""
    pass
