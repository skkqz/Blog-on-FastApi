import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated
from sqlalchemy import func, TIMESTAMP, inspect
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, declared_attr
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine, AsyncSession
from app.core.config import database_url


engine = create_async_engine(url=database_url)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
str_uniq = Annotated[str, mapped_column(unique=True, nullable=False)]


class Base(AsyncAttrs, DeclarativeBase):
    """
    Абстрактный базовый класс для всех моделей базы данных.

    Этот класс предоставляет общие поля и методы для всех моделей, такие как:
    - Автоматическое создание имени таблицы.
    - Уникальный идентификатор (UUID).
    - Временные метки создания и обновления.
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False, index=True,
        comment='Уникальный идентификатор пользователя.'
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now(), comment='Дата и время создания записи пользователя.'
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now(),
        comment='Дата и время последнего обновления записи пользователя.'
    )

    @declared_attr
    def __tablename__(cls) -> str:
        """
        Автоматически генерирует имя таблицы на основе имени класса.
        :return: Имя таблицы в нижнем регистре с добавлением 's' в конце.
        """
        return f'{cls.__name__.lower()}s'

    def to_dict(self, exclude_none: bool = False):
        """
        Преобразует объект модели в словарь.

        :exclude_none (bool): Исключать ли None значения из результата
        :return: Словарь с данными объекта
        """
        result = {}
        for column in inspect(self.__class__).columns:
            value = getattr(self, column.key)

            # Преобразование специальных типов данных
            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, Decimal):
                value = float(value)
            elif isinstance(value, uuid.UUID):
                value = str(value)

            # Добавляем значение в результат
            if not exclude_none or value is not None:
                result[column.key] = value

        return result

    def __repr__(self) -> str:
        """
        Строковое представление объекта для удобства отладки.
        :return: Строка с представлением таблицы.
        """

        return f"<{self.__class__.__name__}(id={self.id}, created_at={self.created_at}, updated_at={self.updated_at})>"
