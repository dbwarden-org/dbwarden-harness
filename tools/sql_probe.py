from __future__ import annotations

from typing import Any, Self

from sqlalchemy import create_engine, text
from sqlalchemy.exc import DatabaseError


class ConstraintNotEnforced(AssertionError):
    """A statement the database was expected to refuse succeeded instead."""


class SqlProbe:
    """Exercise a live database with ordinary SQL to test behaviour, not shape.

    Catalog inspection answers whether an object exists. It does not answer
    whether the server enforces it: a constraint that is recorded but inert is
    indistinguishable at runtime from one that was never created. The
    constraint suites therefore try to violate what they declared and require
    the server to refuse.
    """

    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self.engine.dispose()

    def execute(self, *statements: str) -> None:
        with self.engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))

    def scalar(self, statement: str) -> Any:
        with self.engine.connect() as connection:
            return connection.execute(text(statement)).scalar()

    def rows(self, statement: str) -> list[tuple[Any, ...]]:
        with self.engine.connect() as connection:
            return [tuple(row) for row in connection.execute(text(statement))]

    def rejects(self, statement: str) -> bool:
        """Return whether the database refuses ``statement``.

        The probe always rolls back, so a statement that unexpectedly succeeds
        leaves no row behind to confuse a later assertion in the same test.
        """
        with self.engine.connect() as connection:
            transaction = connection.begin()
            try:
                connection.execute(text(statement))
            except DatabaseError:
                return True
            finally:
                transaction.rollback()
        return False

    def assert_rejects(self, statement: str, *, because: str) -> None:
        if not self.rejects(statement):
            raise ConstraintNotEnforced(
                f"The database accepted a statement it should have refused ({because}): {statement}"
            )
