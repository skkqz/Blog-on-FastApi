import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies.auth_dep import get_current_user_optional
from app.core.dependencies.dao_dep import get_session_with_commit, get_session_without_commit
from app.modules.blog.dao import BlogDAO
from app.modules.auth.models import User
from app.modules.blog.schemas import BlogFullResponse, BlogNotFind


async def get_blog_info(
        blog_id: uuid.UUID,
        session: AsyncSession = Depends(get_session_without_commit),
        user_data: User | None = Depends(get_current_user_optional)
) -> BlogFullResponse | BlogNotFind:
    """
    Зависимость на получения блога.
    :param blog_id: Идентификатор блога.
    :param session: Сессия.
    :param user_data: Данные пользователя.
    :return: Данные блога.
    """

    author_id = user_data.id if user_data else None
    return await BlogDAO.get_full_blog_info(session=session, blog_id=blog_id, author_id=author_id)
