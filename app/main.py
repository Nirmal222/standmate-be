import sys
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add current directory to sys.path to resolve imports when running from root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.v1.router import api_router
from core.database import engine

# Import all models to ensure they are registered with SQLAlchemy
from models.base import Base
from models.user import User
# Import leaf models first (to ensure they are in registry if parents reference them)
# But parents usually reference them by string, so order shouldn't matter...
# Unless specific circular dependency issues arise.
# Let's import everything.
from models.risk import Risk, Assumption
from models.scenario import Scenario, Milestone
from models.task_dependency import TaskDependency
from models.conversation import ConversationLog
from models.version import ProjectVersion
from models.task import Task
from models.project import Project
# Add other models if needed


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan)

# CORS Configuration
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
