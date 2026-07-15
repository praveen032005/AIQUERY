import os
import httpx
import asyncio
import logging
from fastapi import FastAPI, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from .config import settings
from .database import db_instance
from .chat_llm import chat_llm_service

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="Classroom AI Standalone Assessment Service")

# Add CORS Middleware to support local frontend development on separate port
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatQueryRequest(BaseModel):
    trainee_id: str
    question_text: str

async def keep_awake_loop():
    # Render automatically sets RENDER_EXTERNAL_URL for web services
    url = os.getenv("RENDER_EXTERNAL_URL")
    if not url:
        logger.info("RENDER_EXTERNAL_URL environment variable not set. Skipping keep-awake self-ping loop.")
        return
        
    logger.info(f"Starting keep-awake self-ping loop targeting: {url} every 10 minutes")
    # Wait 2 minutes initially to allow the application server to finish starting up
    await asyncio.sleep(120)
    
    async with httpx.AsyncClient() as client:
        while True:
            try:
                # Ping the public root URL
                response = await client.get(url, timeout=30)
                logger.info(f"Keep-awake self-ping status: {response.status_code}")
            except Exception as e:
                logger.warning(f"Keep-awake self-ping failed: {e}")
            # Sleep for 10 minutes (600 seconds)
            await asyncio.sleep(600)

@app.on_event("startup")
async def startup_event():
    # Connect to database or establish local fallback
    await db_instance.connect()
    # Start the keep-awake loop in the background
    asyncio.create_task(keep_awake_loop())

@app.get("/api/trainees")
async def list_trainees():
    return await db_instance.get_trainees()

@app.post("/api/analytics/chat-query")
async def submit_chat_query(request: ChatQueryRequest):
    if not request.question_text.strip():
        raise HTTPException(status_code=400, detail="Question text cannot be blank.")
    
    try:
        # Run analysis (will automatically resolve details, run CrewAI/Fallback, and score competency)
        analysis = await chat_llm_service.analyze_question(request.trainee_id, request.question_text)
        
        # Save to database (MongoDB or local in-memory)
        await db_instance.save_analysis(analysis)
        
        # Return analysis to client
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM chat evaluation failed: {e}")

@app.get("/api/analytics/question-analyses")
async def get_question_analyses(trainee_id: Optional[str] = None):
    try:
        analyses = await db_instance.get_analyses(trainee_id=trainee_id)
        
        # Backwards compatibility key checks for frontend
        for item in analyses:
            if "category" not in item and "classification" in item:
                item["category"] = item["classification"]
            if "resolved_text" not in item and "question_text" in item:
                item["resolved_text"] = item["question_text"]
            if "trainee_name" not in item:
                trainee = await db_instance.get_trainee(item.get("trainee_id"))
                item["trainee_name"] = trainee.get("name", "Unknown Trainee") if trainee else "Unknown Trainee"
        return analyses
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch analyses: {e}")

@app.delete("/api/analytics/question-analyses", status_code=status.HTTP_204_NO_CONTENT)
async def clear_question_analyses():
    try:
        await db_instance.clear_analyses()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear analyses: {e}")

# Render Static File Serving Configuration
# Mount React frontend build directory if it exists
frontend_dist_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist"))

if os.path.exists(frontend_dist_path):
    assets_path = os.path.join(frontend_dist_path, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
        
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Prevent hijacking API endpoints
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        # Serve index.html for all other paths to support client routing
        index_file = os.path.join(frontend_dist_path, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
else:
    @app.get("/")
    async def hello_api():
        return {
            "message": "Classroom AI Chat API is active. Frontend static build is not compiled yet. Build it in frontend/ and rebuild.",
            "endpoints": ["/api/trainees", "/api/analytics/chat-query", "/api/analytics/question-analyses"]
        }
