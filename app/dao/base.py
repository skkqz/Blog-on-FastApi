import uuid
from typing import List, TypeVar, Generic, Type
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
from sqlalchemy import update as sqlalchemy_update, delete as sqlalchemy_delete, func
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from .database import Base

T = TypeVar("T", bound=Base)


class BaseDAO(Generic[T]):
    """
    Базовый DAO (Data Access Object) класс для работы с SQLAlchemy моделями.

    :Generic T: Тип SQLAlchemy модели, должен быть унаследован от Base
    :attr model: Класс SQLAlchemy модели для работы
    """

    model: Type[T] = None

    def __init__(self, session: AsyncSession):
        """
        Инициализирует DAO с асинхронной сессией SQLAlchemy.

        :param session: Асинхронная сессия SQLAlchemy
        :raises ValueError: Если модель не указана в дочернем классе
        """

        self._session = session
        if self.model is None:
            raise ValueError("Модель должна быть указана в дочернем классе")

    async def find_one_or_none_by_id(self, data_id: uuid.uuid4):
        """
        Находит одну запись по ID или возвращает None.

        :param data_id: ID искомой записи
        :return: Найденный объект модели или None
        :raises SQLAlchemyError: При ошибках работы с БД
        """

        try:
            query = select(self.model).filter_by(id=data_id)
            result = await self._session.execute(query)
            record = result.scalar_one_or_none()
            log_message = f"Запись {self.model.__name__} с ID {data_id} {'найдена' if record else 'не найдена'}."
            logger.info(log_message)
            return record
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при поиске записи с ID {data_id}: {e}")
            raise

    async def find_one_or_none(self, filters: BaseModel):
        """
        Находит одну запись по фильтрам или возвращает None.

        :param filters: Pydantic модель с критериями поиска
        :return: Найденный объект модели или None
        :raises SQLAlchemyError: При ошибках работы с БД
        """

        filter_dict = filters.model_dump(exclude_unset=True)
        logger.info(f"Поиск одной записи {self.model.__name__} по фильтрам: {filter_dict}")
        try:
            query = select(self.model).filter_by(**filter_dict)
            result = await self._session.execute(query)
            record = result.scalar_one_or_none()
            log_message = f"Запись {'найдена' if record else 'не найдена'} по фильтрам: {filter_dict}"
            logger.info(log_message)
            return record
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при поиске записи по фильтрам {filter_dict}: {e}")
            raise

    async def find_all(self, filters: BaseModel | None = None):
        """
        Находит все записи, соответствующие фильтрам.

        :param filters: Опциональная Pydantic модель с критериями поиска
        :return: Список найденных объектов модели
        :raises SQLAlchemyError: При ошибках работы с БД
        """

        filter_dict = filters.model_dump(exclude_unset=True) if filters else {}
        logger.info(f"Поиск всех записей {self.model.__name__} по фильтрам: {filter_dict}")
        try:
            query = select(self.model).filter_by(**filter_dict)
            result = await self._session.execute(query)
            records = result.scalars().all()
            logger.info(f"Найдено {len(records)} записей.")
            return records
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при поиске всех записей по фильтрам {filter_dict}: {e}")
            raise

    async def add(self, values: BaseModel):
        """
        Добавляет новую запись в БД.

        :param values: Pydantic модель с данными для создания
        :return: Созданный объект модели
        :raises SQLAlchemyError: При ошибках работы с БД
        """

        values_dict = values.model_dump(exclude_unset=True)
        logger.info(f"Добавление записи {self.model.__name__} с параметрами: {values_dict}")
        try:
            new_instance = self.model(**values_dict)
            self._session.add(new_instance)
            logger.info(f"Запись {self.model.__name__} успешно добавлена.")
            await self._session.flush()
            return new_instance
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при добавлении записи: {e}")
            raise

    async def add_many(self, instances: List[BaseModel]):
        """
        Добавляет несколько записей в БД.

        :param instances: Список Pydantic моделей для создания
        :return: Список созданных объектов модели
        :raises SQLAlchemyError: При ошибках работы с БД
        """

        values_list = [item.model_dump(exclude_unset=True) for item in instances]
        logger.info(f"Добавление нескольких записей {self.model.__name__}. Количество: {len(values_list)}")
        try:
            new_instances = [self.model(**values) for values in values_list]
            self._session.add_all(new_instances)
            logger.info(f"Успешно добавлено {len(new_instances)} записей.")
            await self._session.flush()
            return new_instances
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при добавлении нескольких записей: {e}")
            raise

    async def update(self, filters: BaseModel, values: BaseModel):
        """
        Обновляет записи по фильтрам.

        :param filters: Pydantic модель с критериями поиска
        :param values: Pydantic модель с данными для обновления
        :return: Количество обновленных записей
        :raises SQLAlchemyError: При ошибках работы с БД
        """

        filter_dict = filters.model_dump(exclude_unset=True)
        values_dict = values.model_dump(exclude_unset=True)
        logger.info(
            f"Обновление записей {self.model.__name__} по фильтру: {filter_dict} с параметрами: {values_dict}")
        try:
            query = (
                sqlalchemy_update(self.model)
                .where(*[getattr(self.model, k) == v for k, v in filter_dict.items()])
                .values(**values_dict)
                .execution_options(synchronize_session="fetch")
            )
            result = await self._session.execute(query)
            logger.info(f"Обновлено {result.rowcount} записей.")
            await self._session.flush()
            return result.rowcount
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при обновлении записей: {e}")
            raise

    async def delete(self, filters: BaseModel):
        """
        Удаляет записи по фильтрам.

        :param filters: Pydantic модель с критериями поиска
        :return: Количество удаленных записей
        :raises ValueError: Если не указаны фильтры
        :raises SQLAlchemyError: При ошибках работы с БД
        """

        filter_dict = filters.model_dump(exclude_unset=True)
        logger.info(f"Удаление записей {self.model.__name__} по фильтру: {filter_dict}")
        if not filter_dict:
            logger.error("Нужен хотя бы один фильтр для удаления.")
            raise ValueError("Нужен хотя бы один фильтр для удаления.")
        try:
            query = sqlalchemy_delete(self.model).filter_by(**filter_dict)
            result = await self._session.execute(query)
            logger.info(f"Удалено {result.rowcount} записей.")
            await self._session.flush()
            return result.rowcount
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при удалении записей: {e}")
            raise

    async def count(self, filters: BaseModel | None = None):
        """
        Подсчитывает количество записей, соответствующих фильтрам.

        :param filters: Опциональная Pydantic модель с критериями поиска
        :return: Количество найденных записей
        :raises SQLAlchemyError: При ошибках работы с БД
        """

        filter_dict = filters.model_dump(exclude_unset=True) if filters else {}
        logger.info(f"Подсчет количества записей {self.model.__name__} по фильтру: {filter_dict}")
        try:
            query = select(func.count(self.model.id)).filter_by(**filter_dict)
            result = await self._session.execute(query)
            count = result.scalar()
            logger.info(f"Найдено {count} записей.")
            return count
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при подсчете записей: {e}")
            raise

    async def bulk_update(self, records: List[BaseModel]):
        """
        Выполняет массовое обновление записей.

        :param records: Список Pydantic моделей с данными для обновления
        :return: Количество обновленных записей
        :raises SQLAlchemyError: При ошибках работы с БД
        """

        logger.info(f"Массовое обновление записей {self.model.__name__}")
        try:
            updated_count = 0
            for record in records:
                record_dict = record.model_dump(exclude_unset=True)
                if 'id' not in record_dict:
                    continue

                update_data = {k: v for k, v in record_dict.items() if k != 'id'}
                stmt = (
                    sqlalchemy_update(self.model)
                    .filter_by(id=record_dict['id'])
                    .values(**update_data)
                )
                result = await self._session.execute(stmt)
                updated_count += result.rowcount

            logger.info(f"Обновлено {updated_count} записей")
            await self._session.flush()
            return updated_count
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при массовом обновлении: {e}")
            raise
