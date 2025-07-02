from typing import List
from fastapi import APIRouter, Response, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.utils import authenticate_user, set_tokens
from app.core.dependencies.auth_dep import get_current_user, get_current_admin_user, check_refresh_token
from app.core.dependencies.dao_dep import get_session_with_commit, get_session_without_commit
from app.core.exceptions.user_exceptions import UserAlreadyExistsException, IncorrectEmailOrPasswordException
from app.auth.dao import UsersDAO
from app.auth.schemas import SUserRegister, SUserAuth, EmailModel, SUserAddDB, SUserInfo

router = APIRouter()


@router.post("/register/")
async def register_user(user_data: SUserRegister,
                        session: AsyncSession = Depends(get_session_with_commit)) -> dict:
    """
    Регистрирует нового пользователя в системе.

    :param user_data: Данные для регистрации (схема SUserRegister)
    :param session: Асинхронная сессия SQLAlchemy с авто-коммитом
    :return: Сообщение об успешной регистрации
    :raises UserAlreadyExistsException: Если пользователь с таким email уже существует
    """

    # Проверка существования пользователя
    user_dao = UsersDAO(session)

    existing_user = await user_dao.find_one_or_none(filters=EmailModel(email=user_data.email))
    if existing_user:
        raise UserAlreadyExistsException

    # Подготовка данных для добавления
    user_data_dict = user_data.model_dump()
    user_data_dict.pop('confirm_password', None)

    # Добавление пользователя
    await user_dao.add(values=SUserAddDB(**user_data_dict))

    return {'message': 'Вы успешно зарегистрированы!'}


@router.post("/login/")
async def auth_user(
        response: Response,
        user_data: SUserAuth,
        session: AsyncSession = Depends(get_session_without_commit)
) -> dict:
    """
    Аутентифицирует пользователя и устанавливает JWT-токены в cookies.

    :param response: Объект Response для установки cookies
    :param user_data: Данные для входа (схема SUserAuth)
    :param session: Асинхронная сессия SQLAlchemy без авто-коммита
    :return: Сообщение об успешной аутентификации
    :raises IncorrectEmailOrPasswordException: При неверных учетных данных
    """

    users_dao = UsersDAO(session)
    user = await users_dao.find_one_or_none(
        filters=EmailModel(email=user_data.email)
    )

    if not (user and await authenticate_user(user=user, password=user_data.password)):
        raise IncorrectEmailOrPasswordException
    set_tokens(response, user.id)
    return {
        'ok': True,
        'message': 'Авторизация успешна!'
    }


@router.post("/logout")
async def logout(response: Response):
    """
    Выход пользователя из системы - удаляет JWT-токены из cookies.

    :param response: Объект Response для удаления cookies
    :return: Сообщение об успешном выходе
    """

    response.delete_cookie("user_access_token")
    response.delete_cookie("user_refresh_token")
    return {'message': 'Пользователь успешно вышел из системы'}


@router.get("/me/")
async def get_me(user_data: User = Depends(get_current_user)) -> SUserInfo:
    """
    Возвращает информацию о текущем аутентифицированном пользователе.

    :param user_data: Текущий пользователь (из access token)
    :return: Информация о пользователе (схема SUserInfo)
    """

    return SUserInfo.model_validate(user_data)


@router.get("/all_users/")
async def get_all_users(session: AsyncSession = Depends(get_session_with_commit),
                        user_data: User = Depends(get_current_admin_user)
                        ) -> List[SUserInfo]:
    """
    Возвращает список всех пользователей (только для администраторов).

    :param session: Асинхронная сессия SQLAlchemy с авто-коммитом
    :param user_data: Текущий пользователь (должен быть администратором)
    :return: Список пользователей (схема SUserInfo)
    """

    return await UsersDAO(session).find_all()


@router.post("/refresh")
async def process_refresh_token(
        response: Response,
        user: User = Depends(check_refresh_token)
):
    """
    Обновляет JWT-токены по валидному refresh token.

    :param response: Объект Response для установки новых cookies
    :param user: Пользователь из валидного refresh token
    :return: Сообщение об успешном обновлении токенов
    """

    set_tokens(response, user.id)
    return {"message": "Токены успешно обновлены"}
