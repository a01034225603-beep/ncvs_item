"""
인증 API 라우터 — /auth

엔드포인트:
  POST /auth/login — 사용자명+비밀번호로 JWT 액세스 토큰을 발급한다.
                     발급된 토큰은 프론트엔드에서 localStorage 에 보관하여
                     이후 모든 API 요청의 Authorization 헤더에 사용된다.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.repositories import user_repo
from app.schemas.auth import LoginRequest, TokenResponse
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)):
    """username + password 검증 후 JWT 토큰 반환. 실패 시 401."""
    user = await user_repo.get_by_username(session, body.username)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    return TokenResponse(access_token=create_access_token(subject=user.username))
