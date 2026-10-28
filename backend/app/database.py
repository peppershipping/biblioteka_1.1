<<<<<<< HEAD
"""SQLAlchemy: движок с пулом соединений, фабрика сессий, зависимость FastAPI."""
=======
"""SQLAlchemy: движок, фабрика сессий, базовый класс моделей, зависимость FastAPI."""
>>>>>>> 088ebc434e4e609566051a7126e169906afacece

from collections.abc import Generator

from sqlalchemy import create_engine
<<<<<<< HEAD
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
=======
from sqlalchemy.orm import DeclarativeBase, sessionmaker
>>>>>>> 088ebc434e4e609566051a7126e169906afacece

from .config import get_settings

settings = get_settings()

<<<<<<< HEAD
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
=======
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
>>>>>>> 088ebc434e4e609566051a7126e169906afacece


class Base(DeclarativeBase):
    pass


<<<<<<< HEAD
def get_db() -> Generator[Session, None, None]:
    """Одна сессия на запрос; при исключении транзакция откатывается."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
=======
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
    finally:
        db.close()
