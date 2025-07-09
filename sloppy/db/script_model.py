import logging
import os
from enum import IntEnum
from typing import Any

from pydantic import BaseModel, Field
from pymongo import MongoClient
from pymongo.collection import Collection

from sloppy.utils import load_envs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScriptState(IntEnum):
    """Enum for script processing states"""

    GENERATING = 1
    GENERATED = 2
    PRODUCING = 3
    PRODUCED = 4
    UPLOADING = 5
    UPLOADED = 6


class Script(BaseModel):
    """Pydantic model for script documents"""

    id: str = Field(description="Primary key - matches celery task ID")
    user_prompt: str = Field(description="User's original prompt")
    script: str | None = Field(default=None, description="Generated script content")
    script_cost: float | None = Field(default=0.0, description="Cost of generation")
    tiktok_url: str | None = Field(default=None, description="TikTok upload URL")
    audio_file: str | None = Field(default=None, description="Audio filepath")
    video_file: str | None = Field(default=None, description="Video filepath")
    video_cost: float | None = Field(default=0.0, description="Cost of production")
    state: ScriptState = Field(
        default=ScriptState.GENERATING, description="Current processing state"
    )
    active_task_id: str | None = Field(
        default=None, description="ID of currently active task for this script"
    )

    class Config:
        use_enum_values = True
        json_encoders = {ScriptState: lambda v: v.value}

    def to_mongo_dict(self) -> dict[str, Any]:
        """Convert to MongoDB document format"""
        data = self.dict()
        data["_id"] = data.pop("id")  # Use custom ID as MongoDB _id
        return data

    @classmethod
    def from_mongo_dict(cls, data: dict[str, Any]) -> "Script":
        """Create Script instance from MongoDB document"""
        if "_id" in data:
            data["id"] = data.pop("_id")

        return cls(**data)


class ScriptRepository:
    """Repository class for Script CRUD operations"""

    def __init__(self, mongo_uri: str = "", database_name: str = ""):
        load_envs()
        self.mongo_uri = mongo_uri or os.getenv("MONGODB_URI", "")
        self.database_name = database_name or os.getenv("DATABASE_NAME", "")

        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[self.database_name]
        self.collection: Collection = self.db.scripts

        # Create index on state for efficient filtering
        self.collection.create_index("state")

    def create_script(self, script: Script) -> Script:
        """Insert a new script document"""
        doc = script.to_mongo_dict()
        res = self.collection.insert_one(doc)
        return res.inserted_id

    def get_script(self, script_id: str) -> Script | None:
        """Get a script by ID"""
        doc = self.collection.find_one({"_id": script_id})
        if doc:
            return Script.from_mongo_dict(doc)
        return None

    def update_script(self, script_id: str, update_data: dict[str, Any]) -> bool:
        """Update a script document"""
        # Convert ScriptState enum to int if present
        if "state" in update_data and isinstance(update_data["state"], ScriptState):
            update_data["state"] = update_data["state"].value

        result = self.collection.update_one({"_id": script_id}, {"$set": update_data})

        if result.modified_count:
            return True
        return False

    def delete_script(self, script_id: str) -> bool:
        """Delete a script by ID"""
        result = self.collection.delete_one({"_id": script_id})
        return result.deleted_count > 0

    def get_scripts_by_state(self, state: ScriptState) -> list[Script]:
        """Get all scripts with a specific state"""
        docs = self.collection.find({"state": state.value})
        return [Script.from_mongo_dict(doc) for doc in docs]

    def get_scripts_not_in_state(self, state: ScriptState) -> list[Script]:
        """Get all scripts that are NOT in a specific state"""
        docs = self.collection.find({"state": {"$ne": state.value}})
        return [Script.from_mongo_dict(doc) for doc in docs]

    def get_all_scripts(self) -> list[Script]:
        """Get all scripts"""
        docs = self.collection.find()
        return [Script.from_mongo_dict(doc) for doc in docs]

    def clear_active_task(self, script_id: str) -> bool:
        """Clear the active_task_id for a script"""
        result = self.collection.update_one(
            {"_id": script_id}, {"$unset": {"active_task_id": ""}}
        )
        return result.modified_count > 0

    def test_connection(self) -> bool:
        """Test if the database connection is working"""
        try:
            self.client.admin.command("ping")
            return True
        except Exception as e:
            print(f"Database connection failed: {e}")
            return False

    def close(self):
        """Close the MongoDB connection"""
        self.client.close()
