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
    Схема добавления автора.
    """
    author: uuid.UUID


class UserBase(BaseModelConfig):
    """
    Базовая схема пользователя.
    """
    id: uuid.UUID
    first_name: str
    last_name: str


class TagResponse(BaseModelConfig):
    """
    Схема тегов.
    """
    id: uuid.UUID
    name: str


class BlogFullResponse(BaseModelConfig):
    """
    Схема блога (полное описание).
    """
    id: uuid.UUID
    author: uuid.UUID
    title: str
    content: str
    short_description: str
    created_at: datetime
    status: str
    tags: List[TagResponse]
    # Это поле нужно для работы computed fields, но оно не будет включено в финальный JSON
    user: UserBase = Field(exclude=True)

    # Используем вычисляемые поля для преобразования данных о пользователе
    @computed_field
    @property
    def author_id(self) -> uuid.UUID:
        return self.user.id if self.user else None

    @computed_field
    @property
    def author_name(self) -> str:
        if self.user:
            return f"{self.user.first_name} {self.user.last_name}"
        return None


class BlogNotFind(BaseModel):
    """
    Схема блога (блог не доступен).
    """
    message: str
    status: str
