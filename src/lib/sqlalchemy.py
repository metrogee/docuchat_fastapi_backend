from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Database URL
DATABASE_URL = "sqlite:///./app.db"

# Create ONE engine for the entire application
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Create ONE session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# Base class for database models
class Base(DeclarativeBase):
    pass


# Database dependency
def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()