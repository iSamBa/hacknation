import uuid
from datetime import datetime

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, async_session, engine


class _TestModel(Base):
    __tablename__ = "test_model"


def test_engine_is_async():
    assert isinstance(engine, AsyncEngine)


def test_async_session_is_sessionmaker():
    assert isinstance(async_session, async_sessionmaker)


def test_base_has_id_field():
    mapper = inspect(_TestModel)
    assert "id" in mapper.columns


def test_base_has_created_at_field():
    mapper = inspect(_TestModel)
    assert "created_at" in mapper.columns


def test_base_has_updated_at_field():
    mapper = inspect(_TestModel)
    assert "updated_at" in mapper.columns


def test_base_id_is_primary_key():
    mapper = inspect(_TestModel)
    assert mapper.columns["id"].primary_key


def test_base_created_at_has_server_default():
    mapper = inspect(_TestModel)
    assert mapper.columns["created_at"].server_default is not None


def test_base_updated_at_has_server_default():
    mapper = inspect(_TestModel)
    assert mapper.columns["updated_at"].server_default is not None
