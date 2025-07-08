import io
import os
import re
import tempfile
import traceback
from pathlib import Path

import av
from huggingface_hub import InferenceClient

from sloppy.celery_app import app
from sloppy.db.script_model import ScriptRepository, ScriptState
from sloppy.socketio_client import emit_task_completed, emit_task_failed
from sloppy.utils import load_envs

# DB Connection
script_mongo = ScriptRepository()
if script_mongo.test_connection():
    print("✅☘️ MongoDB Connected Succesfully!")
else:
    print("❌ Failed to Connect")


def split_text_for_tts(text: str, max_length: int = 200) -> list[str]:
    """
    Split text into TTS-friendly chunks based on natural speech boundaries.

    Args:
        text: Input text to split
        max_length: Maximum character length per chunk

    Returns:
        List of text chunks suitable for TTS
    """
    if len(text) <= max_length:
        return [text.strip()]

    # Split on sentence boundaries first
    sentences = re.split(r"[.!?]+", text.strip())
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # If adding this sentence exceeds limit, save current chunk
        if len(current_chunk + sentence + ". ") > max_length:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
            else:
                # Single sentence is too long, split by commas
                parts = re.split(r"[,;]+", sentence)
                for part in parts:
                    part = part.strip()
                    if part:
                        if len(part) <= max_length:
                            chunks.append(part)
                        else:
                            # Even smaller chunks if needed
                            words = part.split()
                            word_chunk = ""
                            for word in words:
                                if len(word_chunk + word + " ") <= max_length:
                                    word_chunk += word + " "
                                else:
                                    if word_chunk:
                                        chunks.append(word_chunk.strip())
                                    word_chunk = word + " "
                            if word_chunk:
                                chunks.append(word_chunk.strip())
        else:
            current_chunk += sentence + ". "

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def bytes_to_audio_container(audio_bytes: bytes, format: str = "wav"):
    """
    Convert audio bytes to PyAV container.

    Args:
        audio_bytes: Raw audio data
        format: Audio format (wav, mp3, etc.)

    Returns:
        PyAV Container object
    """
    # Create a BytesIO object from the audio bytes
    audio_buffer = io.BytesIO(audio_bytes)

    # Open with PyAV - returns a Container object
    container = av.open(audio_buffer, format=format)
    return container


def concatenate_audio_segments(
    audio_segments: list[bytes], output_path: str = "", output_format: str = "wav"
) -> str:
    """
    Concatenate multiple audio segments using PyAV.

    Args:
        audio_segments: List of audio data as bytes
        output_path: Output file path (if empty, creates temp file)
        output_format: Output format (wav, mp3, etc.)

    Returns:
        Path to the concatenated audio file
    """
    if not audio_segments:
        raise ValueError("No audio segments provided")

    if not output_path:
        # Create temporary file
        temp_fd, output_path = tempfile.mkstemp(suffix=f".{output_format}")
        os.close(temp_fd)

    # Create temporary files for each segment to avoid template parameter issue
    temp_files = []
    try:
        for _, segment in enumerate(audio_segments):
            temp_fd, temp_path = tempfile.mkstemp(suffix=".wav")
            os.close(temp_fd)

            with open(temp_path, "wb") as f:
                f.write(segment)
            temp_files.append(temp_path)

        # Get audio properties from first file
        first_container = av.open(temp_files[0])
        first_stream = first_container.streams.audio[0]

        # Create output container and stream
        output_container = av.open(f"{output_path}.{output_format}", "w")
        output_stream = output_container.add_stream(
            codec_name="pcm_s16le", rate=first_stream.rate
        )

        pts = 0
        for temp_file in temp_files:
            input_container = av.open(temp_file)
            input_stream = input_container.streams.audio[0]

            for frame in input_container.decode(input_stream):  # type: ignore
                frame.pts = pts
                frame.time_base = output_stream.time_base  # type: ignore

                for packet in output_stream.encode(frame):
                    output_container.mux(packet)

                pts += frame.samples

            input_container.close()

        # Flush encoder
        for packet in output_stream.encode(None):
            output_container.mux(packet)

        first_container.close()
        output_container.close()

    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except OSError:
                pass

    return output_path


@app.task(bind=True)
def generate_video(self, script_id, script, settings):
    """Generate video task - generates audio from script using Dia with chunking"""
    task_id = self.request.id
    load_envs()
    try:
        print("\n🎬 Starting video generation...")
        print(f"   Script length: {len(script)} characters")
        print(f"   Settings: {settings}")

        # Get API key
        hf_token = os.getenv("HF_TOKEN")
        if not hf_token:
            raise ValueError("HF_TOKEN not found in environment variables")

        # Initialize Hugging Face Inference Client
        print("🤖 Initializing Hugging Face Inference Client...")
        client = InferenceClient(
            provider="fal-ai",
            api_key=hf_token,
        )

        # Check if script needs chunking
        max_length = 200  # Adjust this based on what works well with Dia model
        if len(script) <= max_length:
            # Script is short enough, generate directly
            print("🎙️ Generating audio with Dia model (single chunk)...")
            print(f"   Sending script to model: {script[:200]}...")

            audio_bytes = client.text_to_speech(
                script,
                model="nari-labs/Dia-1.6B",
            )

            print(f"   ✅ Generated audio: {len(audio_bytes)} bytes")

            # Save to file
            print("💾 Saving to av_output file...")
            audio_path = Path(f"/app/av_output/{task_id}.wav")
            audio_path.parent.mkdir(parents=True, exist_ok=True)
            audio_path.write_bytes(audio_bytes)

        else:
            # Script is too long, use chunking
            print(f"🔢 Script is long ({len(script)} chars), using chunking...")

            # Split text into chunks
            text_chunks = split_text_for_tts(script, max_length)
            print(f"   Split into {len(text_chunks)} chunks")

            # Generate audio for each chunk
            audio_segments = []
            for i, chunk in enumerate(text_chunks):
                print(f"🎙️ Processing chunk {i + 1}/{len(text_chunks)}: {chunk[:50]}...")

                try:
                    audio_bytes = client.text_to_speech(
                        chunk,
                        model="nari-labs/Dia-1.6B",
                    )
                    audio_segments.append(audio_bytes)
                    print(f"   ✅ Generated {len(audio_bytes)} bytes")

                except Exception as e:
                    print(f"❌ Error generating TTS for chunk {i + 1}: {e}")
                    raise

            # Concatenate all audio segments
            print(f"🔗 Concatenating {len(audio_segments)} audio segments...")
            audio_path = concatenate_audio_segments(
                audio_segments,
                output_path=f"/app/av_output/{task_id}",
                output_format="wav",
            )

        print(f"✅ Audio saved to temporary file: {audio_path}")
        print(f"   File size: {os.path.getsize(audio_path)} bytes")

        script_mongo.update_script(
            script_id, {"audio_file": audio_path, "state": ScriptState.PRODUCED}
        )

        emit_task_completed(task_id)

        return True

    except Exception as e:
        print(f"❌ Error generating video: {e}")
        traceback.print_exc()

        script_mongo.update_script(script_id, {"state": ScriptState.GENERATED})

        emit_task_failed(task_id, str(e))
        return False
