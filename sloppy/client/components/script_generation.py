import logging

import streamlit as st

from sloppy.client.db_manager import task_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_required_env_vars():
    """Check if all required environment variables are set"""
    import os

    from sloppy.utils import load_envs

    # Ensure environment variables are loaded
    load_envs()

    env_vars = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
        "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY", ""),
        "HF_TOKEN": os.getenv("HF_TOKEN", ""),
    }
    missing = [key for key, value in env_vars.items() if not value]
    return missing


def create_script_task(prompt):
    """Create a new script generation task"""
    missing_vars = check_required_env_vars()
    if missing_vars:
        st.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return None

    try:
        future = task_manager.new_script_task(prompt)

        # Store future in session state for tracking completion
        if "script_futures" not in st.session_state:
            st.session_state.script_futures = []
        st.session_state.script_futures.append(future)
        logger.info(
            f"ADDING FUTURE TO SESSION STATE: {st.session_state.script_futures}"
        )

        st.success("Script task submitted!")
    except Exception as e:
        st.error(f"Failed to create script task: {str(e)}")
        return None


def render_script_generation():
    """Render the script generation component"""
    st.markdown(
        '<div class="section-header">📝 Generate Script</div>', unsafe_allow_html=True
    )

    col1, col2 = st.columns([6, 1])

    with col1:
        with st.form("script_form"):
            user_prompt = st.text_area(
                "Enter your script prompt:",
                placeholder="Describe the type of content you want to generate...",
                height=100,
            )
            submitted = st.form_submit_button(
                "🚀 Generate Script", use_container_width=True
            )

            if submitted and user_prompt:
                st.session_state.show_env_modal = False
                create_script_task(user_prompt)

    with col2:
        if st.button("⚙️", help="Edit Environment Variables"):
            st.session_state.show_env_modal = True
