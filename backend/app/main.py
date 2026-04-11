from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import bookmarks, notes, pdfs, search, settings, tags, wiki, wiki_compile, wiki_graph
from app.config import settings as app_settings
from app.database import engine
from app.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Second Brain API")
    yield
    await engine.dispose()
    logger.info("Second Brain API shut down")


app = FastAPI(
    title="Second Brain API",
    description="Personal Knowledge Base with AI-Powered Search",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3110",
        "https://brain.armandointeligencia.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(notes.router, prefix="/api/v1/notes", tags=["notes"])
app.include_router(bookmarks.router, prefix="/api/v1/bookmarks", tags=["bookmarks"])
app.include_router(pdfs.router, prefix="/api/v1/pdfs", tags=["pdfs"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(tags.router, prefix="/api/v1/tags", tags=["tags"])
app.include_router(settings.router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(wiki.router, prefix="/api/v1/wiki/pages", tags=["wiki"])
app.include_router(wiki_compile.router, prefix="/api/v1/wiki/compile", tags=["wiki"])
app.include_router(wiki_graph.router, prefix="/api/v1/wiki", tags=["wiki"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "environment": app_settings.environment}
