from celery import Celery

app = Celery("ai_tt_generator")

app.config_from_object(
    {
        "broker_url": "redis://localhost:6379/0",
        "result_backend": "redis://localhost:6379/0",
        "task_serializer": "json",
        "accept_content": ["json"],
        "result_serializer": "json",
        "timezone": "UTC",
        "enable_utc": True,
        "imports": (
            "sloppy.script_gen.tasks",
            "sloppy.upload_tt.tasks",
            "sloppy.video_prod.tasks",
        ),
    }
)

if __name__ == "__main__":
    app.start()
