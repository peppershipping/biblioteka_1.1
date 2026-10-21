"""Pydantic-схемы запросов и ответов API (валидация — см. отчёт, раздел 5)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# ---------------------------------------------------------------------------
# Пользователи / авторизация
# ---------------------------------------------------------------------------


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=150)
    email: EmailStr | None = None
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: str | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------------------------------------------------------------------------
# Авторы / жанры
# ---------------------------------------------------------------------------


class AuthorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class GenreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


# ---------------------------------------------------------------------------
# Книги
# ---------------------------------------------------------------------------


class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = ""
    keywords: str = ""
    publication_year: int | None = None
    cover_url: str | None = None
    authors: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    publication_year: int | None
    cover_url: str | None
    authors: list[AuthorOut] = Field(default_factory=list)
    genres: list[GenreOut] = Field(default_factory=list)


class BookWithLibraryOut(BookOut):
    """Книга + сведения из личной библиотеки текущего пользователя (если есть)."""

    status: str | None = None
    my_rating: float | None = None


# ---------------------------------------------------------------------------
# Оценки
# ---------------------------------------------------------------------------


class RatingIn(BaseModel):
    plot: int = Field(ge=1, le=10)
    characters: int = Field(ge=1, le=10)
    style: int = Field(ge=1, le=10)


class RatingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    plot: int
    characters: int
    style: int
    total: float
    updated_at: datetime


# ---------------------------------------------------------------------------
# Личная библиотека
# ---------------------------------------------------------------------------

VALID_STATUSES = {"want_to_read", "reading", "read"}


class UserBookCreate(BaseModel):
    book_id: int
    status: str = "want_to_read"

    @field_validator("status")
    @classmethod
    def check_status(cls, v: str) -> str:
        if v not in VALID_STATUSES:
            raise ValueError(f"Недопустимый статус. Разрешены: {', '.join(sorted(VALID_STATUSES))}")
        return v


class UserBookUpdate(BaseModel):
    """Можно менять статус, комментарий или оба поля сразу."""

    status: str | None = None
    comment: str | None = Field(default=None, max_length=5000)

    @field_validator("status")
    @classmethod
    def check_status(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_STATUSES:
            raise ValueError(f"Недопустимый статус. Разрешены: {', '.join(sorted(VALID_STATUSES))}")
        return v


class CustomBookCreate(BaseModel):
    """Книга, введённая пользователем вручную (форма «Добавить книгу»)."""

    title: str = Field(min_length=1, max_length=300)
    author: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=5000)  # краткое описание сюжета
    comment: str = Field(default="", max_length=5000)  # личный комментарий


class UserBookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    book_id: int
    status: str
    comment: str = ""
    added_at: datetime
    book: BookOut
    rating: RatingOut | None = None  # сюжет, персонажи, стиль, общая
    my_rating: float | None = None  # то же, что rating.total — оставлено для совместимости
