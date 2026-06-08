"""
인증 API 요청/응답 스키마.

LoginRequest: /auth/login 요청 body (username, password)
TokenResponse: JWT 액세스 토큰 응답
"""
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
