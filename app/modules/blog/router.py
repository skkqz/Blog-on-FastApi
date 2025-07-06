import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from fastapi.responses import JSONResponse

from app.core.dependencies.dao_dep import get_session_with_commit, get_session_without_commit
from app.modules.blog.schemas import BlogCreateSchemaBase, BlogCreateSchemaAdd, BlogFullResponse, BlogNotFind
from app.core.dependencies.auth_dep import get_current_user, get_current_user_optional
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
    :param session: Асинхронная сессия SQLAlchemy.
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



@router.get('/detail/{blog_id}', summary='Детальная информация блога')
async def blog_detail(
        blog_id: uuid.UUID,
        user_data: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session_with_commit)
) -> BlogFullResponse | BlogNotFind:
    """
    Детально отображение блога.

    :param blog_id: Идентификатор блога.
    :param user_data:  Данные пользователя.
    :param session: Асинхронная сессия SQLAlchemy.
    :return: Данные блога.
    """

    author_id = user_data.id if user_data else None
    blog = await BlogDAO.get_full_blog_info(session=session, blog_id=blog_id, author_id=author_id)

    return blog


@router.patch('/change_blog_status/{blog_id}', summary="Изменить статус блога")
async def change_blog_status(
        blog_id: uuid.UUID,
        new_status: str,
        session: AsyncSession = Depends(get_session_with_commit),
        current_user: User = Depends(get_current_user)
):
    """
    Изменяет статус блога на указанный.

    :param blog_id: Идентификатор изменяемого блога.
    :param new_status:  Новый статус блога (должен быть одним из: 'draft', 'published').
    :param session: Асинхронная сессия SQLAlchemy.
    :param current_user: Текущий аутентифицированный пользователь.
    :return: Словарь с результатом операции.
    """
    result = await BlogDAO.change_blog_status(session, blog_id, new_status, current_user.id)
    if result['status'] == 'error':
        raise HTTPException(status_code=400, detail=result['message'])
    return result


@router.get('/blogs/', summary='Получить все блоги в статусе "publish"')
async def get_blog_info(
        author_id: uuid.UUID | None = None,
        tag: str | None = None,
        page: int = Query(1, ge=1, description='Номер страницы'),
        page_size: int = Query(10, ge=10, le=100, description='Записей на странице'),
        session: AsyncSession = Depends(get_session_without_commit),
):
    """
    Получает список опубликованных блогов с возможностью фильтрации и пагинацией.

    :param author_id: Фильтр по ID автора блога. Если не указан, возвращаются блоги всех авторов.
    :param tag: Фильтр по тегу. Если не указан, возвращаются блоги с любыми тегами.
    :param page: Номер страницы (начинается с 1).
    :param page_size:  Количество блогов на странице (10-100).
    :param session: Асинхронная сессия SQLAlchemy.
    :return: Словарь с результатами.
    """

    try:
        result = await BlogDAO.get_blog_list(session=session, author_id=author_id, tag=tag, page=page,
                                             page_size=page_size)
        return result if result['blogs'] else BlogNotFind(message='логи не найдены', status='error')
    except Exception as e:
        logger.error(f'Ошибка при получении блогов: {e}')
        return JSONResponse(status_code=500, content={'detail': 'Ошибка сервера'})


@router.post('/delete_blog/{blog_id}', summary='Удалить блог')
async def delete_blog(
        blog_id: uuid.UUID,
        session: AsyncSession = Depends(get_session_with_commit),
        current_user: User = Depends(get_current_user)
):
    """
    Удаление блога.

    :param blog_id: Идентификатор блога.
    :param session: Асинхронная сессия SQLAlchemy.
    :param current_user: Данные пользователя.
    :return:
    """

    result = await BlogDAO.delete_blog(session, blog_id, current_user.id)
    if result['status'] == 'error':
        raise HTTPException(status_code=400, detail=result['message'])
    return result