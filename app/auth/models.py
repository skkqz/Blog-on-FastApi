import uuid

from sqlalchemy import text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.dao.database import Base, str_uniq
from app.core.constants import SystemRoles


class Role(Base):
    """
    Модель роли пользователя.

    :Attributes:
        name (Mapped[str]): Уникальное название роли
        users (Mapped[list["User"]]): Список пользователей с этой ролью (отношение один-ко-многим)

    :Methods:
        __repr__: Возвращает строковое представление объекта
    """
    name: Mapped[str_uniq]
    users: Mapped[list["User"]] = relationship(back_populates="role")

    def __repr__(self):
        """
        Возвращает строковое представление объекта Role.

        :return: Строка в формате "Role(id={self.id}, name={self.name})"
        """
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"


class User(Base):
    """
    Модель пользователя системы.

    :Attributes:
        phone_number (Mapped[str]): Уникальный номер телефона
        first_name (Mapped[str]): Имя пользователя
        last_name (Mapped[str]): Фамилия пользователя
        email (Mapped[str]): Уникальный email адрес
        password (Mapped[str]): Хеш пароля
        role_id (Mapped[int]): ID связанной роли (внешний ключ, по умолчанию 1)
        role (Mapped["Role"]): Объект связанной роли (отношение многие-к-одному)

    :Methods:
        __repr__: Возвращает строковое представление объекта
    """
    phone_number: Mapped[str_uniq]
    first_name: Mapped[str]
    last_name: Mapped[str]
    email: Mapped[str_uniq]
    password: Mapped[str]
    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('roles.id'), default=SystemRoles.USER, server_default=text(f"'{SystemRoles.USER}'::uuid")
    )
    role: Mapped["Role"] = relationship("Role", back_populates="users", lazy="joined")

    def __repr__(self):
        """
        Возвращает строковое представление объекта User.

        :return: Строка в формате "User(id={self.id})"
        """
        return f"{self.__class__.__name__}(id={self.id})"