from typing import Generic, TypeVar

from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    """Common staging operations shared by every concrete repository.

    Repositories only construct queries and stage changes (add/delete) —
    they never call commit/rollback/flush themselves. Transaction boundaries
    stay owned by the service layer, on the same `Session` a repository is
    constructed with, so moving a query into a repository method never
    changes when a write actually lands.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, obj: ModelT) -> None:
        self.db.add(obj)

    def delete(self, obj: ModelT) -> None:
        self.db.delete(obj)
