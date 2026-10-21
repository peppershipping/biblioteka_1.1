"""
Модель данных «Библиотеки» (см. отчёт, раздел 7).

User ── UserBook ── Book ── Author (m2m)
          │            │
          │            └── Genre (m2m)
          └── Rating
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

# ---------------------------------------------------------------------------
# Таблицы связи many-to-many
# ---------------------------------------------------------------------------

book_authors = Table(
    "book_authors",
    Base.metadata,
    Column("book_id", ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
    Column("author_id", ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True),
)

book_genres = Table(
    "book_genres",
    Base.metadata,
    Column("book_id", ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    library: Mapped[list["UserBook"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Author(Base):
    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    books: Mapped[list["Book"]] = relationship(secondary=book_authors, back_populates="authors")


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)

    books: Mapped[list["Book"]] = relationship(secondary=book_genres, back_populates="genres")


class Book(Base):
    """
    Каталог книг. Полнотекстовый поиск реализован функциональным GIN-индексом
    по названию, описанию и ключевым словам (PostgreSQL Full-Text Search,
    см. отчёт, раздел 4.3) — индекс создаётся вместе с таблицей через Base.metadata.create_all.
    """

    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    keywords: Mapped[str] = mapped_column(Text, default="", nullable=False)
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    authors: Mapped[list["Author"]] = relationship(secondary=book_authors, back_populates="books")
    genres: Mapped[list["Genre"]] = relationship(secondary=book_genres, back_populates="books")
    user_entries: Mapped[list["UserBook"]] = relationship(back_populates="book")

    __table_args__ = (
        Index(
            "ix_books_search_vector",
            text(
                "to_tsvector('russian', "
                "coalesce(title, '') || ' ' || coalesce(description, '') || ' ' || coalesce(keywords, ''))"
            ),
            postgresql_using="gin",
        ),
    )


class UserBook(Base):
    """Запись «эта книга есть в личной библиотеке пользователя, со статусом чтения»."""

    __tablename__ = "user_books"

    STATUS_WANT = "want_to_read"
    STATUS_READING = "reading"
    STATUS_READ = "read"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=STATUS_WANT, nullable=False)
    # личный комментарий пользователя к книге
    comment: Mapped[str] = mapped_column(Text, default="", server_default="", nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    user: Mapped["User"] = relationship(back_populates="library")
    book: Mapped["Book"] = relationship(back_populates="user_entries")
    rating: Mapped["Rating | None"] = relationship(
        back_populates="user_book", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("user_id", "book_id", name="uq_user_book"),)


class Rating(Base):
    """
    Многокритериальная оценка книги (см. отчёт, раздел 4.2).
    total = (plot + characters + style) / 3, считается на сервере
    при сохранении — хранится, чтобы не пересчитывать при каждом чтении.
    """

    __tablename__ = "ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_book_id: Mapped[int] = mapped_column(
        ForeignKey("user_books.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    plot: Mapped[int] = mapped_column(Integer, nullable=False)
    characters: Mapped[int] = mapped_column(Integer, nullable=False)
    style: Mapped[int] = mapped_column(Integer, nullable=False)
    total: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()")
    )

    user_book: Mapped["UserBook"] = relationship(back_populates="rating")
