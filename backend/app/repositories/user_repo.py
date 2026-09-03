from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id: str) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalars(select(User).where(User.email == email.strip().lower())).first()

    def add(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
