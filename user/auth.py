import os

from fastapi_users.authentication import (
    CookieTransport,
    JWTStrategy,
    AuthenticationBackend,
)

from dotenv import load_dotenv
load_dotenv()

SECRET = os.environ.get('SECRET_KEY', "Secret")

cookie_transport = CookieTransport(
    cookie_max_age=4000,
    cookie_name="user_classroom",
    cookie_secure=False,
)



def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=4000)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)
