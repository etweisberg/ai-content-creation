from sloppy.celery_app import app


@app.task
def upload_tiktok(video_path, metadata):
    """Upload to TikTok task - to be implemented"""
    return {
        "status": "pending",
        "task": "upload_tiktok",
        "video_path": video_path,
        "metadata": metadata,
    }
