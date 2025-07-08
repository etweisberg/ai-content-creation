import streamlit as st

from sloppy.client.db_manager import script_mongo, task_manager
from sloppy.db.script_model import ScriptState


def render_produced_videos_container():
    """Render the produced videos container component"""
    st.markdown(
        '<div class="section-header">🎥 Produced Videos</div>', unsafe_allow_html=True
    )

    # Check for ongoing tasks and show spinner if needed
    no_ongoing_tasks = task_manager.cleanup_completed_futures()
    if not no_ongoing_tasks:
        st.spinner("Tasks are running in the background...")

    # Check if any video tasks just completed and trigger rerun
    if hasattr(st.session_state, "video_futures"):
        completed_any = False
        for future in st.session_state.video_futures[:]:
            if future.done():
                st.session_state.video_futures.remove(future)
                completed_any = True

        if completed_any:
            st.rerun()

    try:
        produced_scripts = script_mongo.get_scripts_by_state(ScriptState.PRODUCED)  # type: ignore

        if produced_scripts:
            for script in produced_scripts:
                if st.button(
                    f"🎥 Video {script.id[:8]}...",
                    key=f"prod_{script.id}",
                    use_container_width=True,
                ):
                    st.session_state.selected_script = script
        else:
            st.info("No produced videos found.")
    except Exception as e:
        st.error(f"Failed to load produced videos: {str(e)}")
