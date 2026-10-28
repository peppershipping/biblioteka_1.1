"""
Модели данных «Библиотеки» — отражают DDL из раздела 14 ТЗ.

Схему БД создаёт миграция Alembic (alembic/versions/0001_initial.py), а не
Base.metadata.create_all: ENUM, CHECK-ограничения, триггеры пересчёта total и
аудита оценок живут в самой БД.

User ── UserBook ── Book ── Author (M:N)
  │         │          └──── Genre  (M:N)
  │         └── Rating
  ├── Recommendation ── Book
  └── RefreshToken
"""

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class ReadingStatus(str, enum.Enum):
    """Статусы чтения (ENUM reading_status в PostgreSQL)."""

    want_to_read = "want_to_read"  # «Хочу прочитать»
    in_progress = "in_progress"  # «В процессе»
    read = "read"  # «Прочитано»


ROLE_USER = "user"
ROLE_ADMIN = "admin"

FEEDBACK_HELPFUL = "helpful"
FEEDBACK_NOT_HELPFUL = "not_helpful"

book_authors = Table(
    "book_authors",
    Base.metadata,
    Column("book_id", BigInteger, ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
    Column("author_id", BigInteger, ForeignKey("authors.id", ondelete="RESTRICT"), primary_key=True),
)

book_genres = Table(
    "book_genres",
    Base.metadata,
    Column("book_id", BigInteger, ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", BigInteger, ForeignKey("genres.id", ondelete="RESTRICT"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'user'"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    library: Mapped[list["UserBook"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class Author(Base):
    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)

    books: Mapped[list["Book"]] = relationship(secondary=book_authors, back_populates="authors")


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    books: Mapped[list["Book"]] = relationship(secondary=book_genres, back_populates="genres")


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    publication_year: Mapped[int | None] = mapped_column(Integer)
    cover_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Вектор для полнотекстового поиска (GIN-индекс). Заполняется функцией
    # services.books.refresh_search_vector (название, авторы, жанры, описание).
    # deferred — чтобы не тянуть его в каждый запрос.
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, deferred=True)

    authors: Mapped[list[Author]] = relationship(
        secondary=book_authors, back_populates="books", order_by="Author.name"
    )
    genres: Mapped[list[Genre]] = relationship(
        secondary=book_genres, back_populates="books", order_by="Genre.name"
    )
    user_entries: Mapped[list["UserBook"]] = relationship(back_populates="book", passive_deletes=True)


class UserBook(Base):
    """Запись «книга в личной библиотеке пользователя» со статусом чтения."""

    __tablename__ = "user_books"
    __table_args__ = (UniqueConstraint("user_id", "book_id", name="user_books_user_id_book_id_key"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[ReadingStatus] = mapped_column(
        Enum(ReadingStatus, name="reading_status", create_type=False),
        nullable=False,
        server_default=text("'want_to_read'"),
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="library")
    book: Mapped[Book] = relationship(back_populates="user_entries")
    rating: Mapped["Rating | None"] = relationship(
        back_populates="user_book", uselist=False, cascade="all, delete-orphan", passive_deletes=True
    )


class Rating(Base):
    """
    Оценка книги по трём критериям. total считается триггером БД
    (recalc_rating_total) и дублируется в приложении (services.ratings).
    """

    __tablename__ = "ratings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_book_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("user_books.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    plot: Mapped[int] = mapped_column(Integer, nullable=False)
    characters: Mapped[int] = mapped_column(Integer, nullable=False)
    style: Mapped[int] = mapped_column(Integer, nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(3, 1), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user_book: Mapped[UserBook] = relationship(back_populates="rating")


class Recommendation(Base):
    """Показанная пользователю рекомендация: пояснение и обратная связь."""

    __tablename__ = "recommendations"
    __table_args__ = (UniqueConstraint("user_id", "book_id", name="recommendations_user_id_book_id_key"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    feedback: Mapped[str | None] = mapped_column(String(20))  # helpful | not_helpful
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    book: Mapped[Book] = relationship()


class RefreshToken(Base):
    """
    Refresh-токен хранится только в виде хеша (ТЗ 15.2). При ротации старый
    токен отзывается (revoked_at); при logout — тоже.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
