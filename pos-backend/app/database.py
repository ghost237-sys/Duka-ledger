import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# --- Database URL ---
# For local dev we default to SQLite (zero setup, just works).
# For production, set DATABASE_URL to a Postgres connection string, e.g.:
#   postgresql://user:password@host:5432/posdb
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pos_dev.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
