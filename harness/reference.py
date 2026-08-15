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
