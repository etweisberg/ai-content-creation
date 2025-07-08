#!/usr/bin/env python3
import streamlit as st

from sloppy.client.components.application_page import render_application_page

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

# Render the application page
render_application_page()
