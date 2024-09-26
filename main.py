from fastapi.params import Depends
from fastapi_users import FastAPIUsers
from fastapi import FastAPI

from user.auth import auth_backend
from user.manager import get_user_manager
from database.models import User
from user.schemas import UserRead, UserCreate

app = FastAPI()

fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)


@app.get("/")
async def root():
    return {"message": "Hello World"}


app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/register",
    tags=["register"],
)

current_user = fastapi_users.current_user()


@app.get("/protected-route")
def protected_route(user: User = Depends(current_user)):
    return {"message": "Hello Protected Route"}
