from fastapi_users import FastAPIUsers

from database.models import User
from user.auth import auth_backend
from user.manager import get_user_manager

fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)

current_user = fastapi_users.current_user()