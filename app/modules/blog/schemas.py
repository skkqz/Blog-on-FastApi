import uuid
from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict, computed_field, Field


class BaseModelConfig(BaseModel):
    """
    Базовая модель.
    """
    model_config = ConfigDict(from_attributes=True)


class BlogCreateSchemaBase(BaseModelConfig):
    """
    Схема для создания блога.
    """

    title: str
    content: str
    short_description: str
    tags: List[str] = []


class BlogCreateSchemaAdd(BlogCreateSchemaBase):
    """
    Схема добавления автора
    """
    author: uuid.UUID
