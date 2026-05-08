from sqlalchemy import select
from starlette.requests import Request
from starlette.responses import Response
from starlette_admin.auth import AdminConfig, AdminUser, AuthProvider
from starlette_admin.exceptions import LoginFailed

from database.models import User
from user.manager import UserManager


class SuperuserAdminAuth(AuthProvider):
    session_key = "admin_user_id"

    async def login(
        self,
        username: str,
        password: str,
        remember_me: bool,
        request: Request,
        response: Response,
    ) -> Response:
        user = await self._get_superuser(request, username)
        if user is None:
            raise LoginFailed("Invalid email or password")

        valid_password, updated_hash = UserManager(
            None
        ).password_helper.verify_and_update(password, user.hashed_password)
        if not valid_password:
            raise LoginFailed("Invalid email or password")

        if updated_hash is not None:
            user.hashed_password = updated_hash
            request.state.session.add(user)
            await request.state.session.commit()

        request.session[self.session_key] = user.id
        return response

    async def logout(self, request: Request, response: Response) -> Response:
        request.session.pop(self.session_key, None)
        return response

    async def is_authenticated(self, request: Request) -> bool:
        user_id = request.session.get(self.session_key)
        if user_id is None:
            return False

        user = await request.state.session.get(User, user_id)
        if not self._has_admin_access(user):
            request.session.pop(self.session_key, None)
            return False

        request.state.admin_user = user
        return True

    def get_admin_user(self, request: Request) -> AdminUser | None:
        user = getattr(request.state, "admin_user", None)
        if user is None:
            return None
        return AdminUser(username=user.email)

    def get_admin_config(self, request: Request) -> AdminConfig:
        return AdminConfig(app_title="Classroom LMS Admin")

    async def _get_superuser(self, request: Request, email: str) -> User | None:
        result = await request.state.session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        if not self._has_admin_access(user):
            return None
        return user

    @staticmethod
    def _has_admin_access(user: User | None) -> bool:
        return bool(user and user.is_active and user.is_superuser)
