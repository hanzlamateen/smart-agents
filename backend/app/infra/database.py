import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from ..core.config import settings

# DeclarativeBase is best kept at module level for model registry
Base = declarative_base()

class Database:
    def __init__(self):
        # Default to a local sqlite for dev if mysql not present
        # self.db_url = os.getenv("DATABASE_URL", "mysql+pymysql://user:password@db/smart_agents")
        self.db_url = settings.database_url
        
        self.engine = create_engine(
            self.db_url,
            pool_pre_ping=True if "mysql" in self.db_url else False,
            connect_args={"check_same_thread": False} if "sqlite" in self.db_url else {}
        )
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def get_db(self):
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

# Global instance
database = Database()

# Export for compatibility/dependencies
engine = database.engine
get_db = database.get_db
SessionLocal = database.SessionLocal

