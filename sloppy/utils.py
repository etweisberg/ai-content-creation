import os
from pathlib import Path

from dotenv import load_dotenv


# Load environment variables
def load_envs():
    env_path = Path("/app/.env")
    load_dotenv(env_path, override=True)

    # Checking keys
    print(f"OPENAI_API_KEY loaded: {'OPENAI_API_KEY' in os.environ}")
    print(f"TAVILY_API_KEY loaded: {'TAVILY_API_KEY' in os.environ}")
    print(f"FAL_KEY loaded: {'FAL_KEY' in os.environ}")
