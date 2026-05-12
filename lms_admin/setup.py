from pathlib import Path

from fastapi import FastAPI
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette_admin.contrib.sqla import Admin

from database.engine import engine
from lms_admin.auth import SuperuserAdminAuth
from lms_admin.dashboard import DashboardView
from lms_admin.file_preview import add_uploaded_file_preview_route
from lms_admin.views import ADMIN_VIEWS
from user.auth import SECRET

ADMIN_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def setup_admin(app: FastAPI) -> None:
    admin = Admin(
        engine,
        title="Classroom LMS Admin",
        base_url="/admin",
        templates_dir=str(ADMIN_TEMPLATES_DIR),
        index_view=DashboardView(),
        auth_provider=SuperuserAdminAuth(),
        middlewares=[
            Middleware(
                SessionMiddleware,
                secret_key=SECRET,
                same_site="lax",
                https_only=False,
            )
        ],
    )
    for view in ADMIN_VIEWS:
        admin.add_view(view)
    add_uploaded_file_preview_route(admin)
    admin.mount_to(app)
