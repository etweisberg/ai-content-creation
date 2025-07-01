from sloppy.celery_app import app


@app.task
def generate_video(script, settings):
    """Generate video task - to be implemented"""
    return {
        "status": "pending",
        "task": "generate_video",
        "script": script,
        "settings": settings,
    }
