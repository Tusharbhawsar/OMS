from typing import Generic, TypeVar

from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    """Small repository base that owns a SQLAlchemy session."""

    def __init__(self, db: Session) -> None:
        self.db = db
