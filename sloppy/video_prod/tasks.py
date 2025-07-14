import logging
import os
import traceback
from datetime import datetime

import fal_client
from langfuse import get_client, observe

from sloppy.celery_app import app
from sloppy.db.script_model import ScriptRepository, ScriptState
from sloppy.socketio_client import emit_task_completed, emit_task_failed
from sloppy.utils import load_envs

logger = logging.getLogger(__name__)

script_repository = ScriptRepository()
langfuse = get_client()


@observe(name="tts_generation")
def generate_audio_from_text(text_content: str) -> tuple[str, float]:
    generation_start_time = datetime.now()

    def on_queue_update(update):
        if hasattr(update, "logs"):
            for log in update.logs:
                logger.info(f"TTS log: {log}")

    # Use the correct endpoint and subscribe pattern
    tts_result = fal_client.subscribe(
        "fal-ai/playai/tts/dialog",
        arguments={"input": text_content},
        with_logs=True,
        on_queue_update=on_queue_update,
    )
    logger.info(f"TTS subscribe result: {tts_result}")
    # The result should have an 'audio' dict with a 'url' and 'duration'
    audio_url = tts_result["audio"]["url"]
    audio_duration_seconds = tts_result["audio"].get("duration", 0)
    audio_duration_minutes = audio_duration_seconds / 60.0
    estimated_cost_dollars = 0.05 * audio_duration_minutes
    processing_duration_seconds = (
        datetime.now() - generation_start_time
    ).total_seconds()

    langfuse.update_current_generation(
        model="fal-ai/playai/tts/dialog",
        input=text_content,
        output=f"Generated audio at {audio_url}",
        cost_details={"total": estimated_cost_dollars},
        usage_details={"audio_duration_seconds": audio_duration_seconds},
        metadata={
            "provider": "fal-ai",
            "processing_time_seconds": processing_duration_seconds,
            "audio_duration_seconds": audio_duration_seconds,
            "cost_per_minute": 0.05,
        },
    )
    return audio_url, estimated_cost_dollars


@app.task(bind=True)
@observe(name="video_generation")
def generate_video(
    self, script_identifier: str, script_text: str, generation_settings: dict
):
    celery_task_id = self.request.id
    load_envs()
    try:
        fal_api_key = os.getenv("FAL_KEY")
        if not fal_api_key:
            raise ValueError("FAL_KEY not found in environment")
        # Set API key if needed (if fal_client supports it)
        # fal_client.api_key = fal_api_key

        audio_file_url, tts_cost = generate_audio_from_text(script_text)

        langfuse.update_current_span(
            input={"script": script_text, "settings": generation_settings},
            metadata={
                "script_id": script_identifier,
                "task_id": celery_task_id,
                "script_length": len(script_text),
                "timestamp": datetime.now().isoformat(),
            },
            output={
                "audio_path": audio_file_url,
                "success": True,
            },
        )

        script_repository.update_script(
            script_identifier,
            {
                "audio_file": audio_file_url,
                "state": ScriptState.PRODUCED,
                "video_cost": tts_cost,
            },
        )
        script_repository.clear_active_task(script_identifier)
        emit_task_completed(celery_task_id)
        return True

    except Exception as task_error:
        error_message = str(task_error)
        traceback.print_exc()
        langfuse.update_current_span(
            output={"error": error_message, "success": False}, level="ERROR"
        )
        script_repository.update_script(
            script_identifier, {"state": ScriptState.GENERATED}
        )
        script_repository.clear_active_task(script_identifier)
        emit_task_failed(celery_task_id, error_message)
        return False
