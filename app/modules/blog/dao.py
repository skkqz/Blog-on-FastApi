import uuid
from typing import Optional

from loguru import logger

from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.modules.blog.schemas import BlogFullResponse
from app.dao.base import BaseDAO
from app.modules.blog.models import Blog, Tag, BlogTag


class BlogDAO(BaseDAO):
    """
    DAO для работы с блогом.
    """

    model = Blog


class TagDAO(BaseDAO):
    """
    DAO для работы с тегом.
    """

    model = Tag

    @classmethod
    async def add_tags(cls, session: AsyncSession, tag_names: list[str]) -> list[uuid.UUID]:
        """
        Метод для добавления тегов в базу данных.
        Принимает список строк (тегов), проверяет, существуют ли они в базе данных,
        добавляет новые и возвращает список ID тегов.

        :param session: Сессия базы данных.
        :param tag_names: Список наименования тегов.
        :return: Список id тегов.
        """

        tag_ids = []
        for tag_name in tag_names:

            tag_name = tag_name.lower()
            stmt = select(cls.model).filter_by(name=tag_name)
            result = await session.execute(stmt)
            tag = result.scalars().first()

            if tag:
                # Если тег найден, добавляем его ID в список
                tag_ids.append(tag.id)
            else:
                # Если тег не найден, создаем новый тег
                new_tag = cls.model(name=tag_name)
                session.add(new_tag)
                try:
                    await session.flush() # Это создает новый тег и позволяет получить его ID
                    logger.info(f'Тег "{tag_name}" добавлен в базу данных.')
                    tag_ids.append(new_tag.id)
                except SQLAlchemyError as e:
                    await session.rollback()
                    logger.error(f"Ошибка при добавлении тега '{tag_name}': {e}")
                    raise e

        return tag_ids


class BlogTagDAO(BaseDAO):
    """
    DAO для работы с промежуточной моделью блогам и тегом.
    """

    model = BlogTag

    @classmethod
    async def add_blog_tags(cls, session: AsyncSession, blog_tag_pairs: list[dict]) -> None:
        """
        Метод для массового добавления связок блогов и тегов в базу данных.
        Принимает список словарей с blog_id и tag_id, добавляет соответствующие записи.

        :param session: Сессия базы данных.
        :param blog_tag_pairs: Список словарей с ключами 'blog_id' и 'tag_id'.
        :return: None
        """

        blog_tag_instances = []
        for pair in blog_tag_pairs:
            blog_id = pair.get('bog_id')
            tag_id = pair.get('tag_id')

            if blog_id and tag_id:
                blog_tag = cls.model(blog_id=blog_id, tag_id=tag_id)
                blog_tag_instances.append(blog_tag)
            else:
                logger.warning(f'Пропущен неверный параметр в паре: {pair}')

        if blog_tag_instances:
            session.add_all(blog_tag_instances) # Добавляем все объекты за один раз

            try:
                await session.flush()  # Применяем изменения и сохраняем записи в базе данных
                logger.info(f'{len(blog_tag_instances)} связок блогов и тегов успешно добавлено.')

            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f'Ошибка при добавлении связок блогов и тегов: {e}')
                raise e
        else:
            logger.warning('Нет валидных данных для добавления в таблицу blog_tags.')