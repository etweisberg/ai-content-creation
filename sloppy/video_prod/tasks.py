import logging
import os
import tempfile
import traceback
from datetime import datetime

import fal_client
import requests
from langfuse import get_client, observe
from moviepy import AudioFileClip, VideoFileClip

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

    logger.info("TTS Cost Calculation:")
    logger.info(
        f"  - Duration: {audio_duration_seconds} seconds"
        f" ({audio_duration_minutes:.4f} minutes)"
    )
    logger.info("  - Cost per minute: $0.05")
    logger.info(f"  - Estimated cost: ${estimated_cost_dollars:.4f}")
    logger.info(f"  - Processing time: {processing_duration_seconds:.2f} seconds")

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


def generate_video_from_audio(audio_file_url: str, task_id: str) -> tuple[bool, str]:
    try:
        # Download audio file to a temp file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_audio:
            audio_response = requests.get(audio_file_url, stream=True)
            if audio_response.status_code != 200:
                logger.error(f"Failed to download audio: {audio_file_url}")
                return False, ""
            for chunk in audio_response.iter_content(chunk_size=8192):
                tmp_audio.write(chunk)
            audio_path = tmp_audio.name

        # Load audio and get duration
        try:
            audio_clip = AudioFileClip(audio_path)
            audio_duration = audio_clip.duration
            logger.info(f"Successfully loaded audio duration: {audio_duration} seconds")
        except Exception as e:
            logger.error(f"Failed to load audio clip: {e}")
            return False, ""

        # Load source video (surf.mp4 in same dir as this file)
        video_path = os.path.join(os.path.dirname(__file__), "surf.mp4")
        if not os.path.exists(video_path):
            logger.error(f"Source video not found: {video_path}")
            return False, ""
        try:
            video_clip = VideoFileClip(video_path)
            logger.info(f"Successfully loaded duration: {video_clip.duration} seconds")
        except Exception as e:
            logger.error(f"Failed to load video clip: {e}")
            return False, ""

        # Trim video to audio duration
        try:
            trim_duration = min(audio_duration, video_clip.duration)
            logger.info(f"Trimming video to duration: {trim_duration} seconds")
            trimmed_video = video_clip.subclipped(0, trim_duration)
            logger.info("Successfully created trimmed video clip")
        except Exception as e:
            logger.error(f"Failed to trim video: {e}")
            return False, ""

        # Set audio - ensure audio clip is properly loaded
        if audio_clip is not None:
            try:
                logger.info("Attempting to set audio on video clip")
                logger.info(f"trimmed_video type: {type(trimmed_video)}")
                logger.info(f"audio_clip type: {type(audio_clip)}")
                # Try the standard set_audio method
                final_video = trimmed_video.set_audio(audio_clip)
                logger.info("Successfully set audio on video clip")
            except AttributeError as e:
                logger.error(f"set_audio method not found: {e}")
                return False, ""
            except Exception as e:
                logger.error(f"Failed to set audio on video clip: {e}")
                return False, ""
        else:
            logger.error("Audio clip is None, cannot set audio")
            return False, ""

        # Output path
        av_path = os.getenv("AV_PATH")
        if not av_path:
            logger.error("AV_PATH environment variable not set")
            return False, ""
        output_path = os.path.join(av_path, f"{task_id}.mp4")

        # Write the video file
        try:
            logger.info(f"Writing video file to: {output_path}")
            final_video.write_videofile(
                output_path, codec="libx264", audio_codec="aac", threads=2, logger=None
            )
            logger.info("Successfully wrote video file")
        except Exception as e:
            logger.error(f"Failed to write video file: {e}")
            return False, ""

        # Cleanup
        audio_clip.close()
        video_clip.close()
        trimmed_video.close()
        final_video.close()
        os.remove(audio_path)
        return True, output_path
    except Exception as e:
        logger.error(
            f"Error in generate_video_from_audio: {e}\n{traceback.format_exc()}"
        )
        return False, ""


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

        if generation_settings.get("video_only"):
            try:
                script = script_repository.get_script(script_identifier)
                if script is None:
                    logger.error(f"Script not found: {script_identifier}")
                    raise ValueError(f"Script not found: {script_identifier}")
                audio_file_url = script.audio_file
                if not audio_file_url:
                    logger.error(f"No audio file found for script: {script_identifier}")
                    raise ValueError(
                        f"No audio file found for script: {script_identifier}"
                    )
            except Exception as e:
                logger.error(f"Failed to get audio file url: {e}")
                raise

            video_success, video_file_path = generate_video_from_audio(
                audio_file_url, celery_task_id
            )
            if video_success:
                script_repository.update_script(
                    script_identifier, {"video_file": video_file_path}
                )

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

        # Call video generation
        video_success, video_file_path = generate_video_from_audio(
            audio_file_url, celery_task_id
        )
        if video_success:
            script_repository.update_script(
                script_identifier,
                {"video_file": video_file_path},
            )
            script_repository.clear_active_task(script_identifier)
            emit_task_completed(celery_task_id)
            return True
        else:
            error_message = "Video generation failed"
            langfuse.update_current_span(
                output={"error": error_message, "success": False}, level="ERROR"
            )
            script_repository.update_script(
                script_identifier, {"state": ScriptState.GENERATED}
            )
            script_repository.clear_active_task(script_identifier)
            emit_task_failed(celery_task_id, error_message)
            raise RuntimeError(error_message)

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
        raise
