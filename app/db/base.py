
"""
base.py

Purpose:
    Define the shared SQLAlchemy base for DevTrace database models.

Input:
    SQLAlchemy declarative mapping.

Output:
    Base class and metadata used by database models and Alembic.

Responsibilities:
    - Provide a common base for all database entities.
    - Collect table definitions in shared metadata.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
