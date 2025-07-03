import uuid
from tkinter.constants import CASCADE

from sqlalchemy import ForeignKey, Text, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.dao.database import Base, str_uniq
from app.core.constants import SystemRoles

from app.modules.auth.models import User


class Blog(Base):
    """
    Класс модели блога.
    """

    title: Mapped[str_uniq] =mapped_column(comment='Заголовок')
    author: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'), nullable=False, comment='Автор')
    content: Mapped[str] = mapped_column(Text, comment='Контент')
    short_description: Mapped[str] = mapped_column(String(255), comment='Короткое описание')
    status: Mapped[str] = mapped_column(default='published', server_default='published', comment='Статус')

    user: Mapped['User'] = relationship('User', back_populates='blog')
    tags: Mapped[list['Tag']] = relationship(
        secondary='blogtags', # Указываем промежуточную таблицу
        back_populates='blogs'
    )


class Tag(Base):
    """
    Класс модели тега.
    """

    name: Mapped[str] = mapped_column(String(50), unique=True, comment='Наименование')
    blogs: Mapped[list['Blog']] = relationship(
        secondary='blogtags', # Указываем промежуточную таблицу
        back_populates='tags'
    )


class BlogTag(Base):
    """
    Класс промежуточной модели блога и тага.
    """

    blog_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('blogs.id', ondelete=CASCADE), nullable=False)
    tag_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tags.id', ondelete=CASCADE), nullable=False)

    # Уникальное ограничение для предотвращения дублирования
    __table_args__ = (
        UniqueConstraint('blog_id', 'tag_id', name='uq_blog_tag'),
    )