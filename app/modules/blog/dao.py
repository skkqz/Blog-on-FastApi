import uuid
from typing import Optional

from loguru import logger

from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.dao.base import BaseDAO
from app.modules.blog.models import Blog, Tag, BlogTag
from app.modules.blog.schemas import BlogFullResponse


class BlogDAO(BaseDAO):
    """
    DAO для работы с блогом.
    """

    model = Blog

    @classmethod
    async def get_full_blog_info(cls, session: AsyncSession, blog_id: uuid.UUID, author_id: uuid.UUID = None):
        """
        Метод для получения полной информации о блоге, включая данные об авторе и тегах.
        Для опубликованных блогов доступ к информации открыт всем пользователям.
        Для черновиков доступ открыт только автору блога.
        """

        # Строим запрос с подгрузкой данных о пользователе и тегах
        query = (
            select(
                cls.model).options(
                joinedload(Blog.user),  # Подгружаем данные о пользователе (авторе)
                selectinload(Blog.tags) # Подгружаем связанные теги
            ).filter_by(id=blog_id)     # Фильтруем по ID блога
        )

        result = await session.execute(query)
        blog = result.scalar_one_or_none()

        # Если блог не найден или нет прав для его просмотра
        if not blog:
            logger.warning(f'Блог с ID {blog_id} не найден или у вас нет прав на его просмотр.')
            return {
                'message': f'Блог с ID {blog_id} не найден или у вас нет прав на его просмотр.',
                'status': 'error'
            }

        # Если блог в статусе 'draft', проверяем, является ли пользователь автором
        if blog.status == 'draft' and (author_id != blog.author):
            logger.warning('Этот блог находится в статусе черновика, и доступ к нему имеют только авторы.')
            return {
                'message': 'Этот блог находится в статусе черновика, и доступ к нему имеют только авторы.',
                'status': 'error'
            }

        # Возвращаем данные блога (если он опубликован или автор имеет доступ к черновику)
        return BlogFullResponse.model_validate(blog)

    @classmethod
    async def delete_blog(cls, session: AsyncSession, blog_id: uuid.UUID, author_id: uuid.UUID) -> dict:
        """
        Метод для удаления блога. Удаление возможно только автором блога.

        :param session: Асинхронная сессия SQLAlchemy
        :param blog_id: ID блога
        :param author_id: ID автора, пытающегося удалить блог
        :return: Словарь с результатом операции
        """

        try:
            query = select(cls.model).filter_by(id=blog_id)
            result = await session.execute(query)
            blog = result.scalar_one_or_none()

            if not blog:
                logger.warning(f'Блог с ID {blog_id} не найден.')
                return {
                    'message': f'Блог с ID {blog_id} не найден.',
                    'status': 'error'
                }

            # Проверяем, является ли пользователь автором блога
            if author_id != blog.author:
                logger.warning(f'Нет прав на удаление этого блога.')
                return {
                    'message': 'У вас нет прав на удаление этого блога.',
                    'status': 'error'
                }

            # Удаляем блог
            await session.delete(blog)
            await session.flush()

            logger.info(f'Блог с ID {blog_id} успешно удален.')
            return {
                'message': f'Блог с ID {blog_id} успешно удален.',
                'status': 'success'
            }

        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f'Произошла ошибка при удалении блога: {str(e)}')
            return {
                'message': f'Произошла ошибка при удалении блога: {str(e)}',
                'status': 'error'
            }

    @classmethod
    async def change_blog_status(
            cls, session: AsyncSession, blog_id: uuid.UUID, new_status: str, author_id: uuid.UUID
    ) -> dict:
        """
        Метод для изменения статуса блога. Изменение возможно только автором блога.

        :param session: Асинхронная сессия SQLAlchemy
        :param blog_id: ID блога
        :param new_status: Новый статус блога ('draft' или 'published')
        :param author_id: ID автора, пытающегося изменить статус
        :return: Словарь с результатом операции
        """

        if new_status not in ['draft', 'published']:
            return {
                'message': 'Недопустимый статус. Используйте "draft" или "published".',
                'status': 'error'
            }

        try:
            query = select(cls.model).filter_by(id=blog_id)
            result = await session.execute(query)
            blog = result.scalar_one_or_none()

            if not blog:
                return {
                    'message': f'Блог с ID {blog_id} не найден.',
                    'status': 'error'
                }

            if blog.author != author_id:
                return {
                    'message': 'У вас нет прав на изменение статуса этого блога.',
                    'status': 'error'
                }

            # Если текущий статус совпадает с новым, возвращаем сообщение без изменений
            if blog.status == new_status:
                return {
                    'message': f'Блог уже имеет статус "{new_status}".',
                    'status': 'info',
                    'blog_id': blog_id,
                    'current_status': new_status
                }

            # Меняем статус блога
            blog.status = new_status
            await session.flush()

            return {
                'message': f'Статус блога успешно изменен на "{new_status}".',
                'status': 'success',
                'blog_id': blog_id,
                'new_status': new_status
            }
        except SQLAlchemyError as e:
            await session.rollback()
            return {
                'message': f'Произошла ошибка при изменении статуса блога: {str(e)}',
                'status': 'error'
            }

    @classmethod
    async def get_blog_list(cls, session: AsyncSession, author_id: Optional[uuid.UUID] = None, tag: Optional[str] = None,
                            page: int = 1, page_size: int = 10):
        """
        Получает список опубликованных блогов с возможностью фильтрации и пагинации.

        :param session: Асинхронная сессия SQLAlchemy.
        :param author_id: ID автора для фильтрации (опционально).
        :param tag: Название тега для фильтрации (опционально).
        :param page: Номер страницы (начиная с 1).
        :param page_size: Количество записей на странице (от 3 до 100).
        :return: Словарь с ключами page, total_page, total_result, blogs.
        """

        # Ограничение параметров
        page_size = max(3, min(page_size,  100))
        page = max(1, page)

        base_query = select(cls.model).options(
            joinedload(cls.model.user),
            selectinload(cls.model.tags)
        ).filter_by(status='published')

        # Фильтрация по автору
        if author_id is not None:
            base_query = base_query.filter_by(author=author_id)

        # Фильтрация по тегу
        if tag:
            base_query = base_query.join(cls.model.tags).filter(cls.model.tags.any(Tag.name.ilike(f"%{tag.lower()}%")))

        # Подсчет общего количества записей
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await session.scalar(count_query)

        # Если записей нет, возвращаем пустой результат
        if not total_result:
            return {
                'page': page,
                'total_page': 0,
                'total_result': 0,
                'blogs': []
            }

        # Расчет количества страниц
        total_page = (total_result + page_size - 1) // page_size

        # Применение пагинации
        offset = (page - 1) * page_size
        paginated_query = base_query.offset(offset).limit(page_size)

        # Выполнение запроса и получение результатов
        result = await session.execute(paginated_query)
        blogs = result.scalars().all()

        # Удаление дубликатов блогов по их ID
        unique_blogs = []
        seen_ids = set()
        for blog in blogs:
            if blog.id not in seen_ids:
                unique_blogs.append(BlogFullResponse.model_validate(blog))
                seen_ids.add(blog.id)

        # Логирование
        filters = []
        if author_id is not None:
            filters.append(f'author_id={author_id}')
        if tag:
            filters.append(f'tag={tag}')
        filter_str = ' & '.join(filters) if filters else 'no filters'

        logger.info(f'Page {page} fetched with {len(blogs)} blogs, filters: {filter_str}')
        # Формирование результата
        return {
            'page': page,
            'total_page': total_page,
            'total_result': total_result,
            'blogs': unique_blogs
        }


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
                    logger.error(f'Ошибка при добавлении тега "{tag_name}": {e}')
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
            blog_id = pair.get('blog_id')
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