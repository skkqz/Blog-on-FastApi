import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from fastapi.responses import JSONResponse

from app.core.dependencies.blog_dep import get_blog_info
from app.core.dependencies.dao_dep import get_session_with_commit
from app.modules.blog.schemas import BlogCreateSchemaBase, BlogCreateSchemaAdd, BlogFullResponse, BlogNotFind
from app.core.dependencies.auth_dep import get_current_user
from app.modules.auth.models import User
from app.modules.blog.dao import BlogDAO, BlogTagDAO, TagDAO


router = APIRouter()


@router.post('/add_post/', summary='Добавление нового блога с тегами')
async def add_blog(
        add_data: BlogCreateSchemaBase,
        user_data: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session_with_commit)
):
    """
    Добавление блога.

    :param add_data: Данные для создания блога (заголовок, контент, теги).
    :param user_data: Авторизованный пользователь (автоматически).
    :param session: Сессия БД (автоматически).
    :return: Созданный блог с привязанными тегами.
    """

    blog_dict = add_data.model_dump()
    blog_dict['author'] = user_data.id
    tags = blog_dict.pop('tags', [])

    try:
        blog = await BlogDAO(session=session).add(values=BlogCreateSchemaAdd.model_validate(blog_dict))
        blog_id = blog.id

        if tags:
            tags_ids = await TagDAO.add_tags(session=session, tag_names=tags)
            await BlogTagDAO.add_blog_tags(
                session=session, blog_tag_pairs=[{'blog_id': blog_id, 'tag_id': i} for i in tags_ids]
            )
        logger.info(f'Блог с ID {blog_id} успешно добавлен с тегами {[str(i) for i in tags_ids]}.')
        return {'status': 'success', 'message': f'Блог с ID {blog_id} успешно добавлен с тегами.'}

    except IntegrityError as e:
        if 'UNIQUE constraint failed' in str(e.orig):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='Блог с таким заголовком уже существует.')
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Ошибка при добавлении блога.')


#/todo найти решение вывода информации о блоге
@router.get('/get_blog/{blog_id}', summary="Получить информацию по блогу")
async def get_blog_endpoint(
        blog_id: uuid.UUID,
        blog_info: BlogFullResponse | BlogNotFind = Depends(get_blog_info)
) -> BlogFullResponse | BlogNotFind:
    """
    Получить блог.
    :param blog_id: Идентификатор блога.
    :param blog_info: Информация о блоге.
    :return: Информация о блоге.
    """

    return blog_info


@router.post('delete_blog/{blog_id}', summary='Удалить блог')
async def delete_blog(
        blog_id: uuid.UUID,
        session: AsyncSession = Depends(get_session_with_commit),
        current_user: User = Depends(get_current_user)
):
    """
    Удаление блога.
    :param blog_id: Идентификатор блога.
    :param session: Сессия.
    :param current_user: Данные пользователя.
    :return:
    """

    result = await BlogDAO.delete_blog(session, blog_id, current_user.id)
    if result['status'] == 'error':
        raise HTTPException(status_code=400, detail=result['message'])
    return result