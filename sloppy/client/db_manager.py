import logging
from concurrent.futures import ThreadPoolExecutor

from sloppy.db.script_model import Script, ScriptRepository, ScriptState
from sloppy.script_gen.tasks import generate_news_script
from sloppy.video_prod.tasks import generate_video

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

script_mongo = ScriptRepository()
if script_mongo.test_connection():
    print("✅☘️ MongoDB Connected Succesfully!")
else:
    print("❌ Failed to Connect")


class TaskManager:
    def __init__(self, max_workers=5):
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="task_handler"
        )
        self.futures = []

    def new_script_task(self, choice):
        script_task = generate_news_script.apply_async(args=(choice,))  # type: ignore
        script_obj = Script(
            id=script_task.id, user_prompt=choice, state=ScriptState.GENERATING
        )
        # Submit to thread pool
        future = self.executor.submit(handle_script_task, script_task, script_obj)
        self.futures.append(future)

        return future

    def new_video_task(self, script_id):
        script_obj = script_mongo.get_script(script_id)
        if not script_obj:
            raise FileNotFoundError("Script Not Found")
        video_task = generate_video.apply_async(  # type: ignore
            args=(
                script_obj.script,
                {},
            )
        )
        future = self.executor.submit(handle_video_task, video_task, script_obj)
        self.futures.append(future)

        return future


def handle_script_task(script_task, script_obj):
    try:
        # Create initial script in DB
        script_mongo.create_script(script_obj)
        logger.info("WE ARE IN SCRIPT TASK")

        # Poll task
        while not script_task.ready():
            continue

        logger.info("SCRIPT TASK FINISHED")

        # Get the result
        result = script_task.result
        logger.info(f"Task result type: {type(result)}")
        logger.info(f"Task result: {result}")

        # Check if task actually succeeded
        if not result.get("success", False):
            logger.error(
                f"Task failed with error: {result.get('error', 'Unknown error')}"
            )
            return

        # Extract data
        script_content = result["script"]
        cost = result["cost"]

        logger.info(f"About to update script {script_task.id}")
        logger.info(f"Script length: {len(script_content)} characters")
        logger.info(f"Cost: {cost}")

        # Update database
        update_result = script_mongo.update_script(
            script_task.id,
            {
                "script": script_content,
                "state": ScriptState.GENERATED,
                "cost": cost,
            },
        )

        logger.info(f"Database update result: {update_result}")
        logger.info("✅ Script task handling completed successfully")

    except Exception as e:
        logger.error(f"❌ Error in handle_script_task: {e}")
        logger.error(f"Exception type: {type(e)}")
        import traceback

        logger.error(f"Full traceback:\n{traceback.format_exc()}")


def handle_video_task(video_task, script_obj):
    script_mongo.update_script(script_obj.id, {"state": ScriptState.PRODUCING})

    while not video_task.ready():
        continue
    audio_filepath, video_filepath = video_task.result
    script_mongo.update_script(
        script_obj.id, {"audio_file": audio_filepath, "video_file": video_filepath}
    )


task_manager = TaskManager()
