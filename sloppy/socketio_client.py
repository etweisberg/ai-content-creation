# sloppy/socketio_client.py
import socketio

# Use synchronous RedisManager with write_only=True
redis_manager = socketio.RedisManager("redis://redis:6379/0", write_only=True)


def emit_task_completed(task_id: str):
    """Emit task completion"""
    try:
        redis_manager.emit(
            "task_update",
            {"task_id": task_id, "type": "completed"},
            room=f"task_{task_id}",
        )
        print(f"✅ Emitted completion for task {task_id}")
    except Exception as e:
        print(f"❌ Failed to emit completion: {e}")
        print(f"   Task ID: {task_id}")
        print(f"   Room: task_{task_id}")


def emit_task_failed(task_id: str, error: str):
    """Emit task failure"""
    try:
        redis_manager.emit(
            "task_update",
            {"task_id": task_id, "type": "failed", "error": error},
            room=f"task_{task_id}",
        )
        print(f"✅ Emitted failure for task {task_id}")
    except Exception as e:
        print(f"❌ Failed to emit failure: {e}")
