from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.base import ErrorResponse
from app.schemas.auth import LoginRequest, LoginResponse, SignupRequest, UserResponse
from app.services.auth_service import AuthService, redirect_path_for

router = APIRouter(prefix="/auth", tags=["auth"])

E400 = {400: {"model": ErrorResponse}}
E401 = {401: {"model": ErrorResponse}}
E409 = {409: {"model": ErrorResponse}}


def _user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "userId": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "redirectPath": redirect_path_for(user.role),
        "createdAt": user.created_at,
    }


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={**E400, **E409},
    summary="회원가입 — 역할은 ENGINEER | SAFETY_MANAGER",
)
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    return _user_payload(AuthService(db).signup(body))


@router.post(
    "/login",
    response_model=LoginResponse,
    responses=E401,
    summary="로그인 — redirectPath 는 서버가 정한다 (ENGINEER→/home, SAFETY_MANAGER→/manage/requests)",
)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    token, user = AuthService(db).login(body)
    return {
        "accessToken": token,
        "tokenType": "Bearer",
        "role": user.role,
        "redirectPath": redirect_path_for(user.role),
    }


@router.get(
    "/me",
    response_model=UserResponse,
    responses=E401,
    summary="토큰 소유자 — 새로고침·직접 URL 진입 시 역할별 GNB 렌더링용",
)
def me(current: User = Depends(get_current_user)):
    return _user_payload(current)
