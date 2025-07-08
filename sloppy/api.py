import logging
import uuid
from typing import Any  # noqa: UP035

import socketio
from celery.result import AsyncResult
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from sloppy.celery_app import app as celery_app
from sloppy.db.script_model import Script, ScriptRepository, ScriptState
from sloppy.script_gen.tasks import generate_news_script
from sloppy.upload_tt.tasks import upload_tiktok
from sloppy.utils import load_envs
from sloppy.video_prod.tasks import generate_video

load_envs()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Sloppy API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Web sockets
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=[
        "http://localhost:3000",
    ],
    logger=True,
    # Use Redis as the message queue directly
    client_manager=socketio.AsyncRedisManager("redis://redis:6379/0"),
)


# Socket.IO event handlers
@sio.event
async def connect(sid, environ):
    logger.info("Connection")
    logger.info(f"Session ID: {sid}")
    logger.info(f"Origin: {environ.get('HTTP_ORIGIN', 'No origin')}")
    await sio.emit("connected", {"status": "Connected to Sloppy API"}, room=sid)


@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")


@sio.event
async def join_task_room(sid, data):  # Remove 'environ' parameter
    """Join a room to receive updates for a specific task"""
    task_id = data.get("task_id")
    logger.info(f"🔗 Client {sid} joining room: task_{task_id}")
    if task_id:
        await sio.enter_room(sid, f"task_{task_id}")
        await sio.emit("joined_room", {"task_id": task_id}, room=sid)
        logger.info(f"✅ Client {sid} successfully joined room: task_{task_id}")


@sio.event
async def leave_task_room(sid, data):  # Remove 'environ' parameter
    """Leave a task room"""
    task_id = data.get("task_id")
    logger.info(f"🚪 Client {sid} leaving room: task_{task_id}")
    if task_id:
        await sio.leave_room(sid, f"task_{task_id}")
        await sio.emit("left_room", {"task_id": task_id}, room=sid)
        logger.info(f"✅ Client {sid} successfully left room: task_{task_id}")


# Initialize repository
script_repo = ScriptRepository()


# Request models
class ScriptGenerationRequest(BaseModel):
    topic: str


class VideoGenerationRequest(BaseModel):
    script_id: str
    script: str
    settings: dict[str, Any] | None = {}


class TikTokUploadRequest(BaseModel):
    video_path: str
    metadata: dict[str, Any] | None = {}


class ScriptUpdateRequest(BaseModel):
    script: str | None = None
    cost: float | None = None
    tiktok_url: str | None = None
    audio_file: str | None = None
    video_file: str | None = None
    state: ScriptState | None = None


# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# Database health check
@app.get("/health/db")
async def db_health_check():
    if script_repo.test_connection():
        return {"status": "healthy", "database": "connected"}
    else:
        raise HTTPException(status_code=503, detail="Database connection failed")


# Celery task endpoints
@app.post("/tasks/generate-script")
async def create_script_generation_task(request: ScriptGenerationRequest):
    """Create a new script generation task"""
    try:
        # Generate unique task ID
        task_id = str(uuid.uuid4())

        # Create script document in database
        script = Script(
            id=task_id, user_prompt=request.topic, state=ScriptState.GENERATING
        )
        script_repo.create_script(script)

        # Start Celery task with custom task ID
        generate_news_script.apply_async(args=[request.topic], task_id=task_id)  # type: ignore

        return {"task_id": task_id, "topic": request.topic}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/tasks/generate-video")
async def create_video_generation_task(request: VideoGenerationRequest):
    """Create a new video generation task"""
    try:
        task = generate_video.delay(request.script_id, request.script, request.settings)  # type: ignore
        return {
            "task_id": task.id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/tasks/upload-tiktok")
async def create_tiktok_upload_task(request: TikTokUploadRequest):
    """Create a new TikTok upload task"""
    try:
        task = upload_tiktok.delay(request.video_path, request.metadata)  # type: ignore
        return {"task_id": task.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# Task status endpoints
@app.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    """Get the status of a Celery task"""
    try:
        result = AsyncResult(task_id, app=celery_app)

        if result.state == "PENDING":
            return {"task_id": task_id, "status": "pending", "result": None}
        elif result.state == "SUCCESS":
            return {"task_id": task_id, "status": "success", "result": result.result}
        elif result.state == "FAILURE":
            return {"task_id": task_id, "status": "failure", "error": str(result.info)}
        else:
            return {"task_id": task_id, "status": result.state, "result": result.info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# Script CRUD endpoints
@app.post("/scripts", response_model=str)
async def create_script(script: Script):
    """Create a new script"""
    try:
        script_id = script_repo.create_script(script)
        return script_id
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/scripts/studio-scripts", response_model=list[Script])
async def studio_scripts():
    try:
        scripts = script_repo.get_scripts_not_in_state(ScriptState.UPLOADED)
        return scripts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/scripts/{script_id}", response_model=Script)
async def get_script(script_id: str):
    """Get a script by ID"""
    try:
        script = script_repo.get_script(script_id)
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")
        return script
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.put("/scripts/{script_id}")
async def update_script(script_id: str, request: ScriptUpdateRequest):
    """Update a script"""
    try:
        # Filter out None values
        update_data = {k: v for k, v in request.dict().items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No update data provided")

        success = script_repo.update_script(script_id, update_data)
        if not success:
            raise HTTPException(status_code=404, detail="Script not found")

        return {"message": "Script updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.delete("/scripts/{script_id}")
async def delete_script(script_id: str):
    """Delete a script"""
    try:
        success = script_repo.delete_script(script_id)
        if not success:
            raise HTTPException(status_code=404, detail="Script not found")

        return {"message": "Script deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/scripts", response_model=list[Script])
async def list_scripts():
    """List all scripts"""
    try:
        scripts = script_repo.get_all_scripts()
        return scripts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/scripts/state/{state}", response_model=list[Script])
async def list_scripts_by_state(state: ScriptState):
    """List scripts by state"""
    try:
        scripts = script_repo.get_scripts_by_state(state)
        return scripts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


socket_app = socketio.ASGIApp(sio, app)

__all__ = ["app", "socket_app"]

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(socket_app, host="0.0.0.0", port=8000)
