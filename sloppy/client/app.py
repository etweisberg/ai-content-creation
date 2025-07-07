#!/usr/bin/env python3
import os
from pathlib import Path

import streamlit as st
from dotenv import set_key

from sloppy.client.db_manager import script_mongo, task_manager
from sloppy.db.script_model import ScriptState
from sloppy.utils import load_envs

# Initialize session state for environment tracking
if "env_loaded" not in st.session_state:
    st.session_state.env_loaded = False
if "env_file_mtime" not in st.session_state:
    st.session_state.env_file_mtime = None


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


# Load/reload environment variables on every page load
check_and_reload_env()

# Configure Streamlit page
st.set_page_config(
    page_title="AI TT Generator",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS for dark theme with red accents
st.markdown(
    """
<style>
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }

    .main-header {
        text-align: center;
        color: #ff4b4b;
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 2rem;
    }

    .section-header {
        color: #ff4b4b;
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }

    .script-card {
        background-color: #262730;
        border: 1px solid #3d3d3d;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        cursor: pointer;
        transition: all 0.3s ease;
    }

    .script-card:hover {
        border-color: #ff4b4b;
        background-color: #2d2d38;
    }

    .script-id {
        font-family: monospace;
        color: #ff4b4b;
        font-weight: bold;
    }

    .env-var-row {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1rem;
        padding: 0.5rem;
        background-color: #262730;
        border-radius: 4px;
    }

    .env-var-label {
        min-width: 150px;
        font-weight: bold;
        color: #fafafa;
    }

    .missing-env {
        color: #ff4b4b;
        font-weight: bold;
    }

    .stButton > button {
        background-color: #ff4b4b;
        color: white;
        border: none;
        border-radius: 4px;
    }

    .stButton > button:hover {
        background-color: #ff6b6b;
    }

    .stTextInput > div > div > input {
        background-color: #262730;
        color: #fafafa;
        border: 1px solid #3d3d3d;
    }

    .stTextArea > div > div > textarea {
        background-color: #262730;
        color: #fafafa;
        border: 1px solid #3d3d3d;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Initialize session state
if "show_env_modal" not in st.session_state:
    st.session_state.show_env_modal = False
if "selected_script" not in st.session_state:
    st.session_state.selected_script = None
if "editing_env" not in st.session_state:
    st.session_state.editing_env = {}


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


def update_env_var(key, value):
    """Update environment variable in .env file"""
    env_path = Path("/app/.env")
    try:
        set_key(env_path, key, value)
        os.environ[key] = value

        # Force reload on next check by updating session state
        st.session_state.env_file_mtime = None

        return True
    except Exception as e:
        st.error(f"Failed to update {key}: {str(e)}")
        return False


def create_video_task(script_id):
    """Create a new video generation task"""
    missing_vars = check_required_env_vars()
    if missing_vars:
        st.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    try:
        task_manager.new_video_task(script_id)
        st.success("Video task submitted!")
        return True
    except Exception as e:
        st.error(f"Failed to create video task: {str(e)}")
        return False


def create_script_task(prompt):
    """Create a new script generation task"""
    missing_vars = check_required_env_vars()
    if missing_vars:
        st.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return None

    try:
        task_manager.new_script_task(prompt)
        st.success("Script task submitted!")
    except Exception as e:
        st.error(f"Failed to create script task: {str(e)}")
        return None


# Main app header
st.markdown('<div class="main-header">🎬 AI TT Generator</div>', unsafe_allow_html=True)

# Script submission section
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

# Environment variables modal
if st.session_state.show_env_modal:

    @st.dialog("⚙️ Environment Variables")
    def show_env_dialog():
        st.markdown("Configure your API keys:")

        env_vars = get_env_vars()

        with st.form("env_form"):
            new_env_vars = {}
            for key, current_value in env_vars.items():
                col1, col2 = st.columns([1, 3])

                with col1:
                    if current_value:
                        st.markdown(f"**{key}**")
                    else:
                        st.markdown(
                            f'<span class="missing-env">**{key}** (Required)</span>',
                            unsafe_allow_html=True,
                        )

                with col2:
                    new_value = st.text_input(
                        f"Enter {key}",
                        value=current_value,
                        key=f"env_{key}",
                        label_visibility="collapsed",
                        type="password" if current_value else "default",
                        placeholder=f"Enter your {key}...",
                    )
                    new_env_vars[key] = new_value

            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("💾 Save Changes", use_container_width=True):
                    success_count = 0
                    for key, value in new_env_vars.items():
                        if update_env_var(key, value):
                            success_count += 1

                    if success_count == len(new_env_vars):
                        st.success("Environment variables updated successfully!")
                        st.session_state.show_env_modal = False
                        st.rerun()

            with col2:
                if st.form_submit_button("❌ Cancel", use_container_width=True):
                    st.session_state.show_env_modal = False
                    st.rerun()

    show_env_dialog()

# Script review sections
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.markdown(
        '<div class="section-header">📄 Generated Scripts</div>', unsafe_allow_html=True
    )

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

with col2:
    st.markdown(
        '<div class="section-header">🎥 Produced Videos</div>', unsafe_allow_html=True
    )

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

# Script details modal
if st.session_state.selected_script:
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
