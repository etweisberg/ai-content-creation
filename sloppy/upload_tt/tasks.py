from sloppy.celery_app import app
from sloppy.db.script_model import ScriptRepository, ScriptState
from sloppy.socketio_client import emit_task_completed, emit_task_failed

# DB Connection
script_mongo = ScriptRepository()


@app.task(bind=True)
def upload_tiktok(self, script_id, video_path, metadata):
    """Upload to TikTok task - to be implemented"""
    task_id = self.request.id

    try:
        # TODO: Implement actual TikTok upload logic here
        # For now, just simulate completion

        # Update script state to uploaded
        script_mongo.update_script(script_id, {"state": ScriptState.UPLOADED})
        script_mongo.clear_active_task(script_id)

        emit_task_completed(task_id)

        return {
            "status": "completed",
            "task": "upload_tiktok",
            "video_path": video_path,
            "metadata": metadata,
        }
    except Exception as e:
        # Revert state on failure
        script_mongo.update_script(script_id, {"state": ScriptState.PRODUCED})
        script_mongo.clear_active_task(script_id)

        emit_task_failed(task_id, str(e))

        return {
            "status": "failed",
            "error": str(e),
            "task": "upload_tiktok",
            "video_path": video_path,
            "metadata": metadata,
        }
