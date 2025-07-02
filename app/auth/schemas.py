import re
import uuid
from typing import Self
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator, computed_field
from app.auth.utils import get_password_hash


class EmailModel(BaseModel):
    """
    Базовая модель для работы с электронной почтой.

    Attributes:
        email (EmailStr): Валидный email адрес
    """

    email: EmailStr = Field(description="Электронная почта")
    model_config = ConfigDict(from_attributes=True)


class UserBase(EmailModel):
    """
    Базовая модель пользователя с основной информацией.

    Attributes:
        phone_number (str): Номер телефона в международном формате
        first_name (str): Имя пользователя (3-50 символов)
        last_name (str): Фамилия пользователя (3-50 символов)

    Methods:
        validate_phone_number: Валидатор номера телефона
    """

    phone_number: str = Field(description="Номер телефона в международном формате, начинающийся с '+'")
    first_name: str = Field(min_length=3, max_length=50, description="Имя, от 3 до 50 символов")
    last_name: str = Field(min_length=3, max_length=50, description="Фамилия, от 3 до 50 символов")

    @field_validator("phone_number")
    def validate_phone_number(cls, value: str) -> str:
        """
        Проверяет корректность формата номера телефона.

        Args:
            value: Номер телефона для валидации

        Returns:
            Валидный номер телефона

        Raises:
            ValueError: Если номер не соответствует формату
        """

        if not re.match(r'^\+\d{5,15}$', value):
            raise ValueError('Номер телефона должен начинаться с "+" и содержать от 5 до 15 цифр')
        return value


class SUserRegister(UserBase):
    """
    Модель для регистрации нового пользователя.

    Attributes:
        password (str): Пароль (5-50 символов)
        confirm_password (str): Подтверждение пароля (5-50 символов)

    Methods:
        check_password: Проверяет совпадение паролей и хеширует основной пароль
    """

    password: str = Field(min_length=5, max_length=50, description="Пароль, от 5 до 50 знаков")
    confirm_password: str = Field(min_length=5, max_length=50, description="Повторите пароль")

    @model_validator(mode="after")
    def check_password(self) -> Self:
        """
        Проверяет совпадение паролей и хеширует основной пароль.

        Returns:
            Экземпляр модели с хешированным паролем

        Raises:
            ValueError: Если пароли не совпадают
        """

        if self.password != self.confirm_password:
            raise ValueError("Пароли не совпадают")
        self.password = get_password_hash(self.password)  # хешируем пароль до сохранения в базе данных
        return self


class SUserAddDB(UserBase):
    """
    Модель для добавления пользователя в БД.

    Attributes:
        password (str): Хешированный пароль (мин. 5 символов)
    """

    password: str = Field(min_length=5, description="Пароль в формате HASH-строки")


class SUserAuth(EmailModel):
    """
    Модель для аутентификации пользователя.

    Attributes:
        password (str): Пароль (5-50 символов)
    """

    password: str = Field(min_length=5, max_length=50, description="Пароль, от 5 до 50 знаков")


class RoleModel(BaseModel):
    """
    Модель роли пользователя.

    Attributes:
        id (uuid.uuid4): Идентификатор роли
        name (str): Название роли
    """

    id: uuid.UUID = Field(description="Идентификатор роли")
    name: str = Field(description="Название роли")
    model_config = ConfigDict(from_attributes=True)


class SUserInfo(UserBase):
    """
    Модель для отображения информации о пользователе.

    Attributes:
        id (uuid.uuid4): Идентификатор пользователя
        role (RoleModel): Объект роли (исключен из сериализации)
    """

    id: uuid.UUID = Field(description="Идентификатор пользователя")
    role: RoleModel = Field(exclude=True)

    @computed_field
    def role_name(self) -> str:
        """
        Возвращает название роли пользователя.

        Returns:
            Название роли
        """

        return self.role.name

    @computed_field
    def role_id(self) -> uuid.uuid4:
        """
        Возвращает идентификатор роли пользователя.

        Returns:
            ID роли
        """

        return self.role.id
