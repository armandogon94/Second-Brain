from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    telegram_user_id: Mapped[int | None] = mapped_column()
    llm_preference: Mapped[str] = mapped_column(String(50), default="haiku")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)

    notes: Mapped[list["Note"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    bookmarks: Mapped[list["Bookmark"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    pdfs: Mapped[list["Pdf"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    tags: Mapped[list["Tag"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), default=1)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    markdown_content: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    source: Mapped[str] = mapped_column(String(50), default="web_ui")
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    user: Mapped["User"] = relationship(back_populates="notes")
    tag_assignments: Mapped[list["TagAssignment"]] = relationship(
        primaryjoin="and_(TagAssignment.source_type=='note', "
        "foreign(TagAssignment.source_id)==Note.id)",
        viewonly=True,
    )

    __table_args__ = (Index("idx_notes_user_created", "user_id", created_at.desc()),)


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), default=1)
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(String(500))
    scraped_content: Mapped[str | None] = mapped_column(Text)
    source_domain: Mapped[str | None] = mapped_column(String(255))
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    user: Mapped["User"] = relationship(back_populates="bookmarks")
    tag_assignments: Mapped[list["TagAssignment"]] = relationship(
        primaryjoin="and_(TagAssignment.source_type=='bookmark', "
        "foreign(TagAssignment.source_id)==Bookmark.id)",
        viewonly=True,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "original_url", name="uq_bookmarks_user_url"),
        Index("idx_bookmarks_user_created", "user_id", captured_at.desc()),
    )


class Pdf(Base):
    __tablename__ = "pdfs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), default=1)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    page_count: Mapped[int | None] = mapped_column()
    file_size: Mapped[int | None] = mapped_column()
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    user: Mapped["User"] = relationship(back_populates="pdfs")
    tag_assignments: Mapped[list["TagAssignment"]] = relationship(
        primaryjoin="and_(TagAssignment.source_type=='pdf', "
        "foreign(TagAssignment.source_id)==Pdf.id)",
        viewonly=True,
    )

    __table_args__ = (Index("idx_pdfs_user_uploaded", "user_id", uploaded_at.desc()),)


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), default=1)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[int] = mapped_column(nullable=False)
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    character_count: Mapped[int | None] = mapped_column()
    token_count: Mapped[int | None] = mapped_column()
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    embedding: Mapped["Embedding | None"] = relationship(
        back_populates="chunk", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_chunks_source", "source_type", "source_id"),)


class Embedding(Base):
    __tablename__ = "embeddings"

    id: Mapped[int] = mapped_column(primary_key=True)
    chunk_id: Mapped[int] = mapped_column(
        ForeignKey("chunks.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    embedding = mapped_column(Vector(1536))
    embedding_model: Mapped[str] = mapped_column(
        String(100), default="text-embedding-3-small"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    chunk: Mapped["Chunk"] = relationship(back_populates="embedding")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), default=1)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str | None] = mapped_column(String(7))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="tags")
    assignments: Mapped[list["TagAssignment"]] = relationship(
        back_populates="tag", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_tags_user_name"),
    )


class TagAssignment(Base):
    __tablename__ = "tag_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[int] = mapped_column(nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    tag: Mapped["Tag"] = relationship(back_populates="assignments")

    __table_args__ = (
        UniqueConstraint("tag_id", "source_type", "source_id", name="uq_tag_assignment"),
        Index("idx_tag_assignments_source", "source_type", "source_id"),
    )


# ─── Wiki models ─────────────────────────────────────────────────────────────


class WikiPage(Base):
    __tablename__ = "wiki_pages"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), default=1)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    page_type: Mapped[str] = mapped_column(String(50), nullable=False, default="concept")
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False, default="")
    frontmatter: Mapped[dict] = mapped_column(JSONB, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    compiled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR)

    outgoing_links: Mapped[list["WikiLink"]] = relationship(
        foreign_keys="WikiLink.from_page_id",
        back_populates="from_page",
        cascade="all, delete-orphan",
    )
    incoming_links: Mapped[list["WikiLink"]] = relationship(
        foreign_keys="WikiLink.to_page_id",
        back_populates="to_page",
        cascade="all, delete-orphan",
    )
    wiki_sources: Mapped[list["WikiSource"]] = relationship(
        back_populates="wiki_page", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "slug", name="uq_wiki_pages_user_slug"),
        Index("idx_wiki_pages_slug", "user_id", "slug"),
        Index("idx_wiki_pages_user_type", "user_id", "page_type"),
    )


class WikiLink(Base):
    __tablename__ = "wiki_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    from_page_id: Mapped[int] = mapped_column(
        ForeignKey("wiki_pages.id", ondelete="CASCADE"), nullable=False
    )
    to_page_id: Mapped[int] = mapped_column(
        ForeignKey("wiki_pages.id", ondelete="CASCADE"), nullable=False
    )
    link_text: Mapped[str] = mapped_column(String(255), nullable=False)
    context_snippet: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    from_page: Mapped["WikiPage"] = relationship(
        foreign_keys=[from_page_id], back_populates="outgoing_links"
    )
    to_page: Mapped["WikiPage"] = relationship(
        foreign_keys=[to_page_id], back_populates="incoming_links"
    )

    __table_args__ = (
        UniqueConstraint(
            "from_page_id", "to_page_id", "link_text", name="uq_wiki_link"
        ),
        Index("idx_wiki_links_from", "from_page_id"),
        Index("idx_wiki_links_to", "to_page_id"),
    )


class WikiSource(Base):
    __tablename__ = "wiki_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    wiki_page_id: Mapped[int] = mapped_column(
        ForeignKey("wiki_pages.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[int] = mapped_column(nullable=False)
    source_hash: Mapped[str | None] = mapped_column(String(64))
    compiled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    wiki_page: Mapped["WikiPage"] = relationship(back_populates="wiki_sources")

    __table_args__ = (
        UniqueConstraint(
            "wiki_page_id", "source_type", "source_id", name="uq_wiki_source"
        ),
        Index("idx_wiki_sources_source", "source_type", "source_id"),
        Index("idx_wiki_sources_page", "wiki_page_id"),
    )


class CompilationLog(Base):
    __tablename__ = "compilation_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), default=1)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    sources_processed: Mapped[int] = mapped_column(Integer, default=0)
    pages_created: Mapped[int] = mapped_column(Integer, default=0)
    pages_updated: Mapped[int] = mapped_column(Integer, default=0)
    token_usage: Mapped[dict] = mapped_column(JSONB, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    details: Mapped[dict] = mapped_column(JSONB, default=dict)

    __table_args__ = (
        Index("idx_compilation_log_status", "user_id", "status"),
    )
