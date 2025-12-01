from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Create async SQLAlchemy engine
# Convert postgresql:// to postgresql+asyncpg://
database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
database_url = database_url.replace("postgresql+psycopg://", "postgresql+asyncpg://")

engine = create_async_engine(
    database_url,
    pool_pre_ping=True,
    echo=settings.ENVIRONMENT == "development",
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    }
)

# Create async SessionLocal class
SessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Create Base class for models
Base = declarative_base()


# Dependency to get async DB session
async def get_db():
    """
    Dependency function to get async database session.
    Yields a database session and closes it after use.
    """
    async with SessionLocal() as session:
        yield session
