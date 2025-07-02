import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))

    # Блок настроек аутентификации
    SECRET_KEY: str
    ALGORITHM: str

    # Блок настроек подключения к базе данных
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    model_config = SettingsConfigDict(env_file=f"{BASE_DIR}/.env")

    def get_sqlite_db_url(self):
        """
        Генерирует URL для подключения к SQLite базе данных.

        :return: Строка с URL для подключения к базе данных.
        """

        return f"sqlite+aiosqlite:///{self.BASE_DIR}/data/db.sqlite3"

    def get_postgres_db_url(self):
        """
        Генерирует URL для подключения к PostgreSQL базе данных.

        :return: Строка с URL для подключения к базе данных.
        """

        return (f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@"
                f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}")


# Получаем параметры для загрузки переменных среды
settings = Settings()
database_url = settings.get_postgres_db_url()
