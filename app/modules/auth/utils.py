import uuid

from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta, timezone
from fastapi.responses import Response
from app.core.config import settings


def create_tokens(data: dict) -> dict:
    """
    Создает пару JWT-токенов (access и refresh) для аутентификации пользователя.

    :data (dict): Данные для включения в токен (обычно содержит 'sub' - идентификатор пользователя)
    :return (dict): Словарь с двумя токенами:
            - access_token: короткоживущий токен (30 минут)
            - refresh_token: долгоживущий токен (7 дней)

    Example:
        >>> create_tokens({"sub": "123"})
        {'access_token': 'eyJ...', 'refresh_token': 'eyJ...'}
    """

    # Текущее время в UTC
    now = datetime.now(timezone.utc)

    # AccessToken - 30 минут
    access_expire = now + timedelta(seconds=10)
    access_payload = data.copy()
    access_payload.update({"exp": int(access_expire.timestamp()), "type": "access"})
    access_token = jwt.encode(
        access_payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    # RefreshToken - 7 дней
    refresh_expire = now + timedelta(days=7)
    refresh_payload = data.copy()
    refresh_payload.update({"exp": int(refresh_expire.timestamp()), "type": "refresh"})
    refresh_token = jwt.encode(
        refresh_payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return {"access_token": access_token, "refresh_token": refresh_token}


async def authenticate_user(user, password) -> bool:
    """
    Аутентифицирует пользователя путем проверки пароля.

    :user: Объект пользователя из БД (должен содержать атрибут password)
    :password (str): Пароль в чистом виде для проверки

    :return bool: True если аутентификация успешна, False если пользователь не найден или пароль неверный
    """

    if not user or verify_password(plain_password=password, hashed_password=user.password) is False:
        return False
    return True


def set_tokens(response: Response, user_id: uuid.uuid4) -> None:
    """
    Устанавливает JWT-токены в cookies HTTP-ответа.

    :response (Response): Объект ответа FastAPI
    :user_id (uuid.uuid4): Идентификатор пользователя для включения в токен

    Cookies:
        - user_access_token: Access token (30 мин, httpOnly, secure)
        - user_refresh_token: Refresh token (7 дней, httpOnly, secure)
    """

    new_tokens = create_tokens(data={"sub": str(user_id)})
    access_token = new_tokens.get('access_token')
    refresh_token = new_tokens.get("refresh_token")

    response.set_cookie(
        key="user_access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax"
    )

    response.set_cookie(
        key="user_refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax"
    )


# Контекст для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """
    Генерирует хеш пароля с использованием bcrypt.

    :password (str): Пароль в чистом виде

    :return str: Хешированная строка пароля

    Example:
        >>> get_password_hash("secret")
        '$2b$12$...'
    """

    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет соответствие чистого пароля его хешу.

    :plain_password (str): Пароль в чистом виде
    :hashed_password (str): Хешированная версия пароля

    :return bool: True если пароли совпадают, False если нет

    Example:
        >>> verify_password("secret", "$2b$12$...")
        True
    """

    return pwd_context.verify(plain_password, hashed_password)