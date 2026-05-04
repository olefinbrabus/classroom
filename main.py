from fastapi.params import Depends
from fastapi import FastAPI

from settings import fastapi_users, current_user
from user.auth import auth_backend
from database.models import User
from user.schemas import UserRead, UserCreate
from classroom.router import router as classroom_router
from user.router import router as user_router

app = FastAPI()


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

app.include_router(classroom_router, prefix="/classroom", tags=["classroom"])
app.include_router(user_router, prefix="/users", tags=["users"])


@app.get("/protected-route")
def protected_route(user: User = Depends(current_user)):
    return {"message": "Hello Protected Route"}
