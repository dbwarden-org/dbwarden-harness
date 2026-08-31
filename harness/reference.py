from __future__ import annotations

MINIMAL_SQLITE_MODELS = '''\
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base
from dbwarden.databases import TableMeta


Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False)

    class Meta(TableMeta):
        comment = "Reference users"
'''

CONSTRAINED_MODELS = '''\
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

from dbwarden.databases import CheckSpec, TableMeta, UniqueSpec


Base = declarative_base()


class Branch(Base):
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(32), nullable=False)

    class Meta(TableMeta):
        uniques = [UniqueSpec(columns=["code"], name="uq_branches_code")]


class Heartbeat(Base):
    __tablename__ = "heartbeats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    branch_id = Column(Integer, nullable=False)
    seq_no = Column(Integer, nullable=False)

    class Meta(TableMeta):
        uniques = [UniqueSpec(columns=["branch_id"], name="uq_heartbeats_branch_id")]
        checks = [CheckSpec(expression="seq_no >= 0", name="ck_heartbeats_seq_no")]
'''
"""Portable models whose only interesting content is table constraints.

Declared with the backend-neutral ``TableMeta`` so the same source runs on
every backend the harness drives. No foreign keys: this fixture exists to prove
that ``uniques`` and ``checks`` survive generation and reach the server, and a
foreign key would drag backend-specific rebuild behaviour into that question.
"""

CONSTRAINED_MODELS_RELAXED = CONSTRAINED_MODELS.replace(
    'uniques = [UniqueSpec(columns=["branch_id"], name="uq_heartbeats_branch_id")]\n        ',
    "",
)
"""``CONSTRAINED_MODELS`` with one named unique constraint removed.

Used to check that dropping a constraint from the models produces a migration
that drops exactly that constraint and leaves the rest of the table alone.
"""
