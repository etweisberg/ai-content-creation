import logging

import streamlit as st

from sloppy.client.db_manager import script_mongo, task_manager
from sloppy.db.script_model import ScriptState
from sloppy.utils import load_envs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_required_env_vars():
    """Check if all required environment variables are set"""
    import os

    # Ensure environment variables are loaded
    load_envs()

    env_vars = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
        "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY", ""),
        "HF_TOKEN": os.getenv("HF_TOKEN", ""),
    }
    missing = [key for key, value in env_vars.items() if not value]
    return missing


def create_video_task(script_id):
    """Create a new video generation task"""
    missing_vars = check_required_env_vars()
    if missing_vars:
        st.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    try:
        future = task_manager.new_video_task(script_id)

        # Store future in session state for tracking completion
        if "video_futures" not in st.session_state:
            st.session_state.video_futures = []
        st.session_state.video_futures.append(future)

        st.success("Video task submitted!")
        return True
    except Exception as e:
        st.error(f"Failed to create video task: {str(e)}")
        return False


def render_generated_scripts_container():
    """Render the generated scripts container component"""
    st.markdown(
        '<div class="section-header">📄 Generated Scripts</div>', unsafe_allow_html=True
    )

    # Check for ongoing tasks and show spinner if needed
    no_ongoing_tasks = task_manager.cleanup_completed_futures()
    if not no_ongoing_tasks:
        logger.info("SHOWING SPINNER")
        st.spinner("Tasks are running in the background...")

    # Check if any script tasks just completed and trigger rerun
    if hasattr(st.session_state, "script_futures"):
        logger.info(f"CHECKING FUTURES: {st.session_state.script_futures}")
        completed_any = False
        for future in st.session_state.script_futures[
            :
        ]:  # Copy to avoid modification during iteration
            if future.done():
                st.session_state.script_futures.remove(future)
                completed_any = True

        if completed_any:
            logger.info("RERUN BECAUSE COMPLETED FUTURES")
            st.rerun()

    try:
        generated_scripts = script_mongo.get_scripts_by_state(ScriptState.GENERATED)  # type: ignore

        if generated_scripts:
            for script in generated_scripts:
                if st.button(
                    f"📄 Script {script.id[:8]}...",
                    key=f"gen_{script.id}",
                    use_container_width=True,
                ):
                    st.session_state.selected_script = script
        else:
            st.info("No generated scripts found.")
    except Exception as e:
        st.error(f"Failed to load generated scripts: {str(e)}")
