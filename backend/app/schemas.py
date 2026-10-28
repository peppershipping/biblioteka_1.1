"""
DTO (Pydantic v2) для REST API. Входные схемы отделены от ORM-моделей: клиент
не может задать role, user_id, password_hash и другие системные поля
(защита от mass assignment, ТЗ 15.3).
"""

import re
from datetime import datetime
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from .models import ReadingStatus

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Страница результатов с пагинацией limit/offset (ТЗ 15.1, правило 39)."""

    items: list[T]
    limit: int
    offset: int
    total: int


# ---------------------------------------------------------------------------
# Аутентификация
# ---------------------------------------------------------------------------

_USERNAME_RE = re.compile(r"^[\w.\-]+$")


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def _username(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("слишком короткое имя пользователя (минимум 3 символа)")
        if not _USERNAME_RE.match(v):
            raise ValueError("допустимы буквы, цифры и символы . _ -")
        return v

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = str(v).strip().lower()
        if len(v) > 254:
            raise ValueError("слишком длинный адрес электронной почты")
        return v


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=254)  # имя пользователя или email
    password: str = Field(min_length=1, max_length=128)


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=256)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # секунд до истечения access-токена


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: str


# ---------------------------------------------------------------------------
# Книги
# ---------------------------------------------------------------------------


def _names(v):
    """ORM-объекты Author/Genre -> строки с именами."""
    return [getattr(item, "name", item) for item in (v or [])]


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None = None
    publication_year: int | None = None
    cover_url: str | None = None
    authors: list[str] = []
    genres: list[str] = []

    @field_validator("authors", "genres", mode="before")
    @classmethod
    def _to_names(cls, v):
        return _names(v)


class BookListItem(BookOut):
    """Карточка каталога: данные книги + статус и оценка текущего пользователя."""

    my_status: ReadingStatus | None = None
    my_rating: float | None = None


class BookPage(Page[BookListItem]):
    # Если включён «умный поиск» и языковая модель распознала запрос — сюда
    # попадают извлечённые фильтры (для отображения пользователю).
    interpreted: dict | None = None


class BookDetail(BookListItem):
    library_id: int | None = None  # id записи user_books, если книга в библиотеке
    avg_rating: float | None = None
    ratings_count: int = 0


class BookCreate(BaseModel):
    """Создание книги в общем каталоге (только admin)."""

    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=10000)
    publication_year: int | None = Field(default=None, ge=1, le=2100)
    cover_url: str | None = Field(default=None, max_length=1000)
    authors: list[str] = Field(default_factory=list, max_length=10)
    genres: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("title")
    @classmethod
    def _title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("название не может быть пустым")
        return v

    @field_validator("authors", "genres")
    @classmethod
    def _names_list(cls, items: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in items:
            item = item.strip()
            if not item:
                continue
            if len(item) > 200:
                raise ValueError("слишком длинное имя (максимум 200 символов)")
            if item.lower() not in {c.lower() for c in cleaned}:
                cleaned.append(item)
        return cleaned

    @field_validator("cover_url")
    @classmethod
    def _cover(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        v = v.strip()
        if not re.match(r"^https?://", v, re.IGNORECASE):
            raise ValueError("ссылка на обложку должна начинаться с http:// или https://")
        return v


class GenreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


# ---------------------------------------------------------------------------
# Оценки
# ---------------------------------------------------------------------------

Score = Annotated[int, Field(strict=True, ge=1, le=10)]


class RatingIn(BaseModel):
    plot: Score
    characters: Score
    style: Score


class RatingPatch(BaseModel):
    plot: int | None = Field(default=None, strict=True, ge=1, le=10)
    characters: int | None = Field(default=None, strict=True, ge=1, le=10)
    style: int | None = Field(default=None, strict=True, ge=1, le=10)

    @model_validator(mode="after")
    def _at_least_one(self) -> "RatingPatch":
        if self.plot is None and self.characters is None and self.style is None:
            raise ValueError("укажите хотя бы один критерий: plot, characters или style")
        return self


class RatingBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plot: int
    characters: int
    style: int
    total: float
    updated_at: datetime

    @field_validator("total", mode="before")
    @classmethod
    def _to_float(cls, v):
        return float(v)


class RatingOut(RatingBrief):
    book_id: int


class PublicRatingOut(RatingBrief):
    """Оценка любого пользователя в списке оценок книги (без email и id)."""

    username: str


# ---------------------------------------------------------------------------
# Личная библиотека
# ---------------------------------------------------------------------------


class LibraryCreate(BaseModel):
    book_id: int = Field(ge=1)
    status: ReadingStatus = ReadingStatus.want_to_read


class LibraryUpdate(BaseModel):
    status: ReadingStatus


class LibraryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    status: ReadingStatus
    added_at: datetime
    book: BookOut
    rating: RatingBrief | None = None


class LibraryStats(BaseModel):
    total: int
    want_to_read: int
    in_progress: int
    read: int
    ratings_count: int
    avg_rating: float | None


# ---------------------------------------------------------------------------
# Рекомендации
# ---------------------------------------------------------------------------


class RecommendationSignals(BaseModel):
    similar_to: str | None = None  # название понравившейся книги, на которую похожа рекомендация
    genres: list[str] = []  # общие с вашими любимыми книгами жанры


class RecommendationOut(BaseModel):
    id: int
    book: BookOut
    reason: str | None = None  # пояснение языковой модели; None — модель недоступна
    score: float | None = None
    signals: RecommendationSignals = Field(default_factory=RecommendationSignals)
    feedback: Literal["helpful", "not_helpful"] | None = None


class RecommendationsPage(Page[RecommendationOut]):
    personalized: bool
    ratings_count: int
    min_ratings: int
    message: str | None = None
    explanations: bool = False  # есть ли у подборки пояснения языковой модели


class FeedbackIn(BaseModel):
    recommendation_id: int = Field(ge=1)
    feedback: Literal["helpful", "not_helpful"]


class FeedbackOut(BaseModel):
    recommendation_id: int
    feedback: Literal["helpful", "not_helpful"]


# Для стабильной сортировки/фильтров (белые списки — ТЗ 15.3)
CatalogSort = Literal["relevance", "title", "year", "created"]
LibrarySort = Literal["added", "title", "status", "rating"]
SortOrder = Literal["asc", "desc"]
