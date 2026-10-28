"""Начальная схема БД (раздел 14 ТЗ) + таблица refresh_tokens

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


UPGRADE_SQL = [
    # --- перечисление статусов чтения ---
    "CREATE TYPE reading_status AS ENUM ('want_to_read', 'in_progress', 'read')",

    # --- основные таблицы ---
    """
    CREATE TABLE users (
        id BIGSERIAL PRIMARY KEY,
        username VARCHAR(50) NOT NULL UNIQUE,
        email VARCHAR(254) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        role VARCHAR(20) NOT NULL DEFAULT 'user' CHECK (role IN ('user','admin')),
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE books (
        id BIGSERIAL PRIMARY KEY,
        title VARCHAR(300) NOT NULL,
        description TEXT,
        publication_year INT CHECK (publication_year IS NULL OR publication_year > 0),
        cover_url TEXT,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE authors (
        id BIGSERIAL PRIMARY KEY,
        name VARCHAR(200) NOT NULL UNIQUE
    )
    """,
    """
    CREATE TABLE genres (
        id BIGSERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL UNIQUE
    )
    """,
    """
    CREATE TABLE book_authors (
        book_id BIGINT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
        author_id BIGINT NOT NULL REFERENCES authors(id) ON DELETE RESTRICT,
        PRIMARY KEY (book_id, author_id)
    )
    """,
    """
    CREATE TABLE book_genres (
        book_id BIGINT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
        genre_id BIGINT NOT NULL REFERENCES genres(id) ON DELETE RESTRICT,
        PRIMARY KEY (book_id, genre_id)
    )
    """,
    """
    CREATE TABLE user_books (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        book_id BIGINT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
        status reading_status NOT NULL DEFAULT 'want_to_read',
        added_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        UNIQUE (user_id, book_id)
    )
    """,
    """
    CREATE TABLE ratings (
        id BIGSERIAL PRIMARY KEY,
        user_book_id BIGINT NOT NULL UNIQUE REFERENCES user_books(id) ON DELETE CASCADE,
        plot INT NOT NULL CHECK (plot BETWEEN 1 AND 10),
        characters INT NOT NULL CHECK (characters BETWEEN 1 AND 10),
        style INT NOT NULL CHECK (style BETWEEN 1 AND 10),
        total NUMERIC(3,1) NOT NULL CHECK (total BETWEEN 1 AND 10),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE recommendations (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        book_id BIGINT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
        reason TEXT,
        feedback VARCHAR(20) CHECK (feedback IS NULL OR feedback IN ('helpful','not_helpful')),
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        UNIQUE (user_id, book_id)
    )
    """,

    # --- refresh-токены (ТЗ 15.2): хранятся только хеши ---
    """
    CREATE TABLE refresh_tokens (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        token_hash VARCHAR(64) NOT NULL UNIQUE,
        expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
        revoked_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
    )
    """,

    # --- индексы (ТЗ 14.1) ---
    "CREATE INDEX idx_user_books_user_id ON user_books(user_id)",
    "CREATE INDEX idx_user_books_status ON user_books(status)",
    "CREATE INDEX idx_user_books_book_id ON user_books(book_id)",
    "CREATE INDEX idx_ratings_user_book_id ON ratings(user_book_id)",
    "CREATE INDEX idx_recommendations_user_id ON recommendations(user_id)",
    "CREATE INDEX idx_recommendations_book_id ON recommendations(book_id)",
    "CREATE INDEX idx_book_authors_author_id ON book_authors(author_id)",
    "CREATE INDEX idx_book_genres_genre_id ON book_genres(genre_id)",
    "CREATE INDEX idx_books_year ON books(publication_year)",
    "CREATE INDEX idx_books_title_lower ON books(lower(title))",
    "CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id)",

    # --- полнотекстовый поиск: вектор обновляет приложение (services/books.py) ---
    "ALTER TABLE books ADD COLUMN search_vector tsvector",
    "CREATE INDEX idx_books_search_vector ON books USING GIN(search_vector)",

    # --- триггер: пересчёт итоговой оценки ---
    """
    CREATE OR REPLACE FUNCTION recalc_rating_total()
    RETURNS trigger AS $$
    BEGIN
        NEW.total := ROUND((NEW.plot + NEW.characters + NEW.style)::numeric / 3, 1);
        NEW.updated_at := now();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql
    """,
    """
    CREATE TRIGGER trg_recalc_rating_total
    BEFORE INSERT OR UPDATE OF plot, characters, style ON ratings
    FOR EACH ROW EXECUTE FUNCTION recalc_rating_total()
    """,

    # --- аудит изменений оценок ---
    """
    CREATE TABLE rating_audit (
        id BIGSERIAL PRIMARY KEY,
        rating_id BIGINT,
        user_book_id BIGINT,
        old_plot INT, old_characters INT, old_style INT, old_total NUMERIC(3,1),
        new_plot INT, new_characters INT, new_style INT, new_total NUMERIC(3,1),
        changed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
        changed_by BIGINT
    )
    """,
    # changed_by берётся из переменной сеанса app.current_user_id, которую
    # приложение выставляет перед изменением оценки (set_config(..., true)).
    """
    CREATE OR REPLACE FUNCTION audit_rating_change()
    RETURNS trigger AS $$
    BEGIN
        INSERT INTO rating_audit(rating_id, user_book_id, old_plot, old_characters, old_style, old_total,
                                 new_plot, new_characters, new_style, new_total, changed_by)
        VALUES (OLD.id, OLD.user_book_id, OLD.plot, OLD.characters, OLD.style, OLD.total,
                NEW.plot, NEW.characters, NEW.style, NEW.total,
                NULLIF(current_setting('app.current_user_id', true), '')::bigint);
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql
    """,
    """
    CREATE TRIGGER trg_audit_rating_change
    AFTER UPDATE OF plot, characters, style ON ratings
    FOR EACH ROW EXECUTE FUNCTION audit_rating_change()
    """,
]

DOWNGRADE_SQL = [
    "DROP TRIGGER IF EXISTS trg_audit_rating_change ON ratings",
    "DROP FUNCTION IF EXISTS audit_rating_change()",
    "DROP TABLE IF EXISTS rating_audit",
    "DROP TRIGGER IF EXISTS trg_recalc_rating_total ON ratings",
    "DROP FUNCTION IF EXISTS recalc_rating_total()",
    "DROP TABLE IF EXISTS refresh_tokens",
    "DROP TABLE IF EXISTS recommendations",
    "DROP TABLE IF EXISTS ratings",
    "DROP TABLE IF EXISTS user_books",
    "DROP TABLE IF EXISTS book_genres",
    "DROP TABLE IF EXISTS book_authors",
    "DROP TABLE IF EXISTS genres",
    "DROP TABLE IF EXISTS authors",
    "DROP TABLE IF EXISTS books",
    "DROP TABLE IF EXISTS users",
    "DROP TYPE IF EXISTS reading_status",
]


def upgrade() -> None:
    for statement in UPGRADE_SQL:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_SQL:
        op.execute(statement)
