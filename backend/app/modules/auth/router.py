from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database.session import get_db
from app.modules.auth import service
from app.modules.auth.models import User
from app.modules.auth.schemas import LoginIn, RefreshIn, RegisterIn, TokenOut, UserOut, UserUpdateIn

router = APIRouter()


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        preferred_language=user.preferred_language,
        role=user.role.key,
    )


@router.post("/auth/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED, tags=["auth"])
def register(body: RegisterIn, db: Session = Depends(get_db)) -> TokenOut:
    user = service.create_user(
        db, email=body.email, password=body.password, full_name=body.full_name, language=body.preferred_language
    )
    return service.issue_tokens(db, user)


@router.post("/auth/login", response_model=TokenOut, tags=["auth"])
def login(body: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    return service.login(db, body.email, body.password)


@router.post("/auth/refresh", response_model=TokenOut, tags=["auth"])
def refresh(body: RefreshIn, db: Session = Depends(get_db)) -> TokenOut:
    return service.refresh(db, body.refresh_token)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, tags=["auth"])
def logout(body: RefreshIn, db: Session = Depends(get_db)) -> None:
    service.logout(db, body.refresh_token)


@router.get("/users/me", response_model=UserOut, tags=["users"])
def me(user: User = Depends(get_current_user)) -> UserOut:
    return _user_out(user)


@router.patch("/users/me", response_model=UserOut, tags=["users"])
def update_me(
    body: UserUpdateIn, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> UserOut:
    user = db.merge(user)
    if body.full_name is not None:
        user.full_name = body.full_name.strip()
    if body.preferred_language is not None:
        user.preferred_language = body.preferred_language
        request.state.language = body.preferred_language
    db.flush()
    return _user_out(user)
