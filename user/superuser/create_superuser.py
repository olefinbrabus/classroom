import asyncio
import sys
from pathlib import Path

from fastapi_users import exceptions
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.engine import BaseModel, async_session_maker, engine
from database.models import User
from user.manager import UserManager
from user.schemas import SuperUserCreate


def ask_superuser_data() -> SuperUserCreate:
    password = input("Password: ")
    password_confirmation = input("Repeat password: ")
    if password != password_confirmation:
        raise ValueError("Passwords do not match")

    return SuperUserCreate(
        email=input("Email: "),
        password=password,
        first_name=input("First name: "),
        second_name=input("Second name: "),
        third_name=input("Third name: "),
        is_active=True,
        is_superuser=True,
        is_verified=True,
        is_teacher=True,
    )


async def create_superuser(user_data: SuperUserCreate) -> User:
    async with engine.begin() as connection:
        await connection.run_sync(BaseModel.metadata.create_all)

    async with async_session_maker() as session:
        user_db = SQLAlchemyUserDatabase(session, User)
        user_manager = UserManager(user_db)
        return await user_manager.create(user_data, safe=False)


async def main() -> int:
    try:
        user = await create_superuser(ask_superuser_data())
    except exceptions.UserAlreadyExists:
        print("User with this email already exists.", file=sys.stderr)
        return 1
    except (ValidationError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1
    finally:
        await engine.dispose()

    print(f"Created superuser {user.email} with id {user.id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
