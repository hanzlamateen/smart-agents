from contextlib import asynccontextmanager
from fastapi import FastAPI
from .logging import setup_logging
from ..infra.database import engine, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    
    ## Setup logging
    setup_logging()

    ## Setup database
    Base.metadata.create_all(bind=engine)

    yield
    # Shutdown
    pass