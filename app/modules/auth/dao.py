from app.dao.base import BaseDAO
from app.modules.auth.models import User, Role


class UsersDAO(BaseDAO):
    """
    Класс dao user
    """
    model = User


class RoleDAO(BaseDAO):
    """
    Класс dao role
    """
    model = Role
