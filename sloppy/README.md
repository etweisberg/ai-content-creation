# Sloppy

Python backend infrastructure for AI TikTok Generation and Content Management.

## About the Name

The name "Sloppy" references the concept of AI-generated content or "AI slop" - low-quality, mass-produced content that floods digital platforms. This term was popularized by John Oliver in his segment on [AI and the Problems with AI-Generated Content](https://youtu.be/TWpg1RmzAbc?si=PIMhKjz-9KsY4bRT).

## Architecture

### Core Components

- **FastAPI Application** (`api.py`): REST API server handling HTTP requests
- **Celery Workers** (`celery_app.py`): Background task processing for video generation
- **Database Models** (`db/`): MongoDB schema definitions for scripts and content
- **Task Modules**:
  - `script_gen/`: AI script generation tasks
  - `video_prod/`: Video production and editing tasks  
  - `upload_tt/`: TikTok upload and publishing tasks
- **WebSocket Support** (`socketio_client.py`): Real-time updates for task progress

### Dependencies

Built with Python 3.11+ and key libraries:
- FastAPI for API framework
- Celery for distributed task processing
- PyMongo for MongoDB integration
- Socket.IO for real-time communications
- AV for video processing
- Hugging Face Hub for AI model integration

### Task Processing

The system uses Celery for async task processing with Redis as the message broker. Tasks are organized into separate modules for script generation, video production, and content uploading.
