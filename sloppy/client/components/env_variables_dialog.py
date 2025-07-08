import os
from pathlib import Path

import streamlit as st
from dotenv import set_key

from sloppy.utils import load_envs


def get_env_vars():
    """Get current environment variables"""
    return {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
        "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY", ""),
        "HF_TOKEN": os.getenv("HF_TOKEN", ""),
    }


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


def render_env_variables_dialog():
    """Render the environment variables dialog"""
    if not st.session_state.show_env_modal:
        return

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
                        # Reload environment variables using the utility
                        load_envs()
                        st.rerun()

            with col2:
                if st.form_submit_button("❌ Cancel", use_container_width=True):
                    st.session_state.show_env_modal = False
                    st.rerun()

    show_env_dialog()
