import os
from pathlib import Path

import streamlit as st

from sloppy.client.components.env_variables_dialog import render_env_variables_dialog
from sloppy.client.components.generated_scripts_container import (
    render_generated_scripts_container,
)
from sloppy.client.components.produced_videos_container import (
    render_produced_videos_container,
)
from sloppy.client.components.script_generation import render_script_generation
from sloppy.client.db_manager import script_mongo
from sloppy.db.script_model import ScriptState
from sloppy.utils import load_envs


def check_and_reload_env():
    """Check if .env file has changed and reload if necessary"""
    env_path = Path("/app/.env")

    try:
        current_mtime = env_path.stat().st_mtime if env_path.exists() else 0

        # Load environment on first run or if file has changed
        if (
            not st.session_state.env_loaded
            or st.session_state.env_file_mtime != current_mtime
        ):
            load_envs()
            st.session_state.env_loaded = True
            st.session_state.env_file_mtime = current_mtime

            # Show reload notification if this wasn't the first load
            if st.session_state.env_file_mtime is not None:
                st.toast("Environment variables reloaded!", icon="🔄")

    except Exception as e:
        st.error(f"Failed to load environment variables: {str(e)}")


def get_env_vars():
    """Get current environment variables"""
    return {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
        "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY", ""),
        "HF_TOKEN": os.getenv("HF_TOKEN", ""),
    }


def check_required_env_vars():
    """Check if all required environment variables are set"""
    env_vars = get_env_vars()
    missing = [key for key, value in env_vars.items() if not value]
    return missing


def render_script_details():
    """Render script details modal"""
    if not st.session_state.selected_script:
        return

    script = st.session_state.selected_script

    with st.container():
        st.markdown("### 📋 Script Details")

        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"**Script ID:** `{script.id}`")
            st.markdown(f"**State:** {ScriptState(script.state).name}")
            st.markdown(f"**User Prompt:** {script.user_prompt}")

            if script.script:
                st.markdown("**Generated Script:**")
                st.text_area(
                    "Script Content", value=script.script, height=200, disabled=True
                )

            if script.cost:
                st.markdown(f"**Cost:** ${script.cost:.4f}")

            if script.audio_file:
                st.markdown(f"**Audio File:** `{script.audio_file}`")

            if script.video_file:
                st.markdown(f"**Video File:** `{script.video_file}`")

            if script.tiktok_url:
                st.markdown(f"**TikTok URL:** [Link]({script.tiktok_url})")

        with col2:
            if st.button("❌ Close", use_container_width=True):
                st.session_state.selected_script = None
                st.rerun()


def render_application_page():
    """Render the main application page"""
    # Initialize session state for environment tracking
    if "env_loaded" not in st.session_state:
        st.session_state.env_loaded = False
    if "env_file_mtime" not in st.session_state:
        st.session_state.env_file_mtime = None

    # Initialize session state
    if "show_env_modal" not in st.session_state:
        st.session_state.show_env_modal = False
    if "selected_script" not in st.session_state:
        st.session_state.selected_script = None
    if "editing_env" not in st.session_state:
        st.session_state.editing_env = {}

    # Load/reload environment variables on every page load
    check_and_reload_env()

    # Main app header
    st.markdown(
        '<div class="main-header">🎬 AI TT Generator</div>', unsafe_allow_html=True
    )

    # Script generation section
    render_script_generation()

    # Environment variables modal
    render_env_variables_dialog()

    # Script review sections
    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        render_generated_scripts_container()

    with col2:
        render_produced_videos_container()

    # Script details modal
    render_script_details()

    # Test database connection on startup
    if not script_mongo.test_connection():  # type: ignore
        st.error(
            "❌ Failed to connect to MongoDB. Please check your database configuration."
        )
    else:
        st.sidebar.success("✅ MongoDB Connected Successfully!")

    # Show missing environment variables warning
    missing_env_vars = check_required_env_vars()
    if missing_env_vars:
        st.sidebar.warning(
            f"⚠️ Missing environment variables: {', '.join(missing_env_vars)}"
        )
        st.sidebar.info("Click the ⚙️ button to configure your API keys.")
