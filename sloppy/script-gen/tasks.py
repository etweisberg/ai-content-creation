from sloppy.celery_app import app


@app.task
def generate_script(prompt):
    """Generate script task - to be implemented"""
    return {"status": "pending", "task": "generate_script", "prompt": prompt}
