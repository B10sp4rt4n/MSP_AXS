from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from ..core.config import settings


# Build engine in a dialect-aware way (SQLite needs connect_args)
engine_kwargs = {"echo": settings.ECHO_SQL}

if settings.is_sqlite():
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        **engine_kwargs,
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=settings.ENGINE_POOL_SIZE,
        max_overflow=settings.ENGINE_MAX_OVERFLOW,
        pool_timeout=settings.ENGINE_POOL_TIMEOUT,
        **engine_kwargs,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
