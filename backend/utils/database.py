"""DocuMind AI — SQLAlchemy 2.0 async engine, session factory, and ORM table definitions.

Provides the async engine, async session maker, and declarative Base for all
database models. Also defines all ORM table classes matching the SQL schema
specified in CLAUDE.md.
"""

import os
import uuid
import logging
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Computed,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, TSVECTOR
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://documind:documind@localhost:5432/documind")


engine = create_async_engine(DATABASE_URL, echo=os.getenv("DEBUG", "false").lower() == "true")

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


class Document(Base):
    """ORM model for the documents table."""
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    filename = Column(Text, nullable=False)
    file_type = Column(Text, nullable=False)
    doc_type = Column(Text, nullable=True)
    language = Column(Text, default="en")
    upload_date = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    storage_path = Column(Text, nullable=False)
    status = Column(Text, default="pending")
    metadata_ = Column("metadata", JSONB, default={}, server_default=text("'{}'::jsonb"))

    pages = relationship("Page", back_populates="document", cascade="all, delete-orphan")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    extracted_fields = relationship("ExtractedField", back_populates="document", cascade="all, delete-orphan")


class Page(Base):
    """ORM model for the pages table."""
    __tablename__ = "pages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)
    raw_text = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)
    needs_review = Column(Boolean, default=False)
    page_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    document = relationship("Document", back_populates="pages")
    chunks = relationship("Chunk", back_populates="page", cascade="all, delete-orphan")


class Chunk(Base):
    """ORM model for the chunks table."""
    __tablename__ = "chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_id = Column(UUID(as_uuid=True), ForeignKey("pages.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    text_search = Column(
        TSVECTOR,
        Computed("to_tsvector('english', text)", persisted=True),
    )
    chunk_type = Column(Text, nullable=True)
    section_heading = Column(Text, nullable=True)
    page_number = Column(Integer, nullable=True)
    bbox = Column(JSONB, nullable=True)
    metadata_ = Column("metadata", JSONB, default={}, server_default=text("'{}'::jsonb"))
    embedding_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    document = relationship("Document", back_populates="chunks")
    page = relationship("Page", back_populates="chunks")

    __table_args__ = (
        Index("idx_chunks_text_search", text_search, postgresql_using="gin"),
        Index("idx_chunks_document_id", document_id),
    )


class ExtractedField(Base):
    """ORM model for the extracted_fields table."""
    __tablename__ = "extracted_fields"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    field_name = Column(Text, nullable=False)
    field_value = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    document = relationship("Document", back_populates="extracted_fields")


class Feedback(Base):
    """ORM model for the feedback table."""
    __tablename__ = "feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    query = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)
    correction = Column(Text, nullable=True)
    document_ids = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())


async def get_session() -> AsyncSession:
    """Yield an async database session for dependency injection.

    Returns:
        AsyncSession: An SQLAlchemy async session.
    """
    async with async_session() as session:
        yield session
