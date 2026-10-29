
"""Pydantic schemas for API requests and responses."""

import re
from datetime import datetime
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from .models import ReadingStatus

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    limit: int
    offset: int
    total: int


# Authentication

_USERNAME_RE = re.compile(r"^[\w.\-]+$")


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Username must contain at least 3 characters")
        if not _USERNAME_RE.fullmatch(value):
            raise ValueError("Only letters, digits, '.', '_' and '-' are allowed")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        value = str(value).strip().lower()
        if len(value) > 254:
            raise ValueError("Email address is too long")
        return value


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=256)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: str


# Authors and genres

class AuthorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class GenreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


# Books

def _names(value):
    """Convert Author/Genre ORM objects to their names."""
    return [getattr(item, "name", item) for item in (value or [])]


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None = None
    publication_year: int | None = None
    cover_url: str | None = None
    authors: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)

    @field_validator("authors", "genres", mode="before")
    @classmethod
    def convert_names(cls, value):
        return _names(value)


class BookListItem(BookOut):
    """Book card with the current user's status and rating."""

    my_status: ReadingStatus | None = None
    my_rating: float | None = None


class BookPage(Page[BookListItem]):
    interpreted: dict | None = None


class BookDetail(BookListItem):
    library_id: int | None = None
    avg_rating: float | None = None
    ratings_count: int = 0


class BookCreate(BaseModel):
    """Create a book in the shared catalog; administrator only."""

    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=10000)
    publication_year: int | None = Field(default=None, ge=1, le=2100)
    cover_url: str | None = Field(default=None, max_length=1000)
    authors: list[str] = Field(default_factory=list, max_length=10)
    genres: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be empty")
        return value

    @field_validator("authors", "genres")
    @classmethod
    def validate_names(cls, items: list[str]) -> list[str]:
        cleaned = []
        seen = set()

        for item in items:
            item = item.strip()
            if not item:
                continue
            if len(item) > 200:
                raise ValueError("A name cannot exceed 200 characters")

            key = item.casefold()
            if key not in seen:
                cleaned.append(item)
                seen.add(key)

        return cleaned

    @field_validator("cover_url")
    @classmethod
    def validate_cover_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None

        value = value.strip()
        if not re.match(r"^https?://", value, re.IGNORECASE):
            raise ValueError("Cover URL must start with http:// or https://")
        return value


# Ratings

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
    def require_at_least_one(self) -> "RatingPatch":
        if (
            self.plot is None
            and self.characters is None
            and self.style is None
        ):
            raise ValueError("Specify at least one rating criterion")
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
    def convert_total(cls, value):
        return float(value)


class RatingOut(RatingBrief):
    book_id: int


class PublicRatingOut(RatingBrief):
    """Public rating without user email or user ID."""

    username: str


# Personal library

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


# Recommendations

class RecommendationSignals(BaseModel):
    similar_to: str | None = None
    genres: list[str] = Field(default_factory=list)


class RecommendationOut(BaseModel):
    id: int
    book: BookOut
    reason: str | None = None
    score: float | None = None
    signals: RecommendationSignals = Field(
        default_factory=RecommendationSignals
    )
    feedback: Literal["helpful", "not_helpful"] | None = None


class RecommendationsPage(Page[RecommendationOut]):
    personalized: bool
    ratings_count: int
    min_ratings: int
    message: str | None = None
    explanations: bool = False


class FeedbackIn(BaseModel):
    recommendation_id: int = Field(ge=1)
    feedback: Literal["helpful", "not_helpful"]


class FeedbackOut(BaseModel):
    recommendation_id: int
    feedback: Literal["helpful", "not_helpful"]


# Sorting and filtering

CatalogSort = Literal["relevance", "title", "year", "created"]
LibrarySort = Literal["added", "title", "status", "rating"]
SortOrder = Literal["asc", "desc"]
