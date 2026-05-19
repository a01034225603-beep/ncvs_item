from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import User
from app.repositories import user_repo
from app.security import decode_access_token

oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2), session: AsyncSession = Depends(get_session)
) -> User:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials"
    )
    try:
        payload = decode_access_token(token)
        username = payload.get("sub")
    except InvalidTokenError as exc:
        raise cred_exc from exc
    if not username:
        raise cred_exc
    user = await user_repo.get_by_username(session, username)
    if user is None:
        raise cred_exc
    return user
