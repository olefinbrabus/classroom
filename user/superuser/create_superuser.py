from asyncio import run as run_async
from copy import deepcopy
from typing import Any

# from fastapi_users import FastAPIUsers

from database.models import User

# from database.engine import engine
from user.schemas import SuperUserCreate


async def create_superuser():
    try:
        user_data = await parse_arguments()
        print(user_data)
    except Exception as e:
        print(e)


async def parse_arguments() -> dict[str, Any]:
    superuser_fields = SuperUserCreate.__pydantic_fields__
    fields_to_pop = ("is_superuser", "is_verified", "is_teacher", "is_active")
    for field in fields_to_pop:
        superuser_fields.pop(field)

    print(superuser_fields)
    superuser_data = {}

    for k, v in superuser_fields.items():
        v = input(f"please, enter {k}:")
        superuser_data[k] = v

    return superuser_data


run_async(create_superuser())
