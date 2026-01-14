from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.lifespan import lifespan
from .core.config import settings as app_settings
from .core.exceptions import global_exception_handler
import os
from .routers import sessions, agent_settings, instance, messages, chat

app = FastAPI(
    title="Smart Agents Service",
    description="A FastAPI service for smart agents",
    version="1.0.0",
    lifespan=lifespan
)

app.add_exception_handler(Exception, global_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(sessions.router)
app.include_router(instance.router)
app.include_router(messages.router)
app.include_router(chat.router)
app.include_router(agent_settings.router)

@app.get("/")
async def root():
    return {"message": "Smart Agents Service", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
