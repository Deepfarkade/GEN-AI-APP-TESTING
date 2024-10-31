from fastapi import FastAPI, Request, Response, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from api.routes import auth, chat
from core.config import settings
import uvicorn
from contextlib import asynccontextmanager
from database.mongodb import MongoDB
from database.redis import RedisClient
import logging
import os
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Startup: Connect to databases
        await MongoDB.connect_db()
        await RedisClient.connect_redis()
        logger.info("Successfully connected to databases")
        yield
    finally:
        # Shutdown: Close connections
        await MongoDB.close_db()
        await RedisClient.close_redis()
        logger.info("Database connections closed")

app = FastAPI(
    title="SmartChat API",
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])

# Ensure static directory exists
static_path = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_path, exist_ok=True)

# Mount static files from frontend build
app.mount("/assets", StaticFiles(directory=os.path.join(static_path, "assets")), name="assets")

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve frontend static files and handle client-side routing"""
    # If API request, let it pass through to the API routes
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")
        
    # For all other routes, serve the index.html
    index_path = os.path.join(static_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return JSONResponse(
            status_code=404,
            content={"message": "Frontend not built. Please run 'npm run build' first."}
        )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )