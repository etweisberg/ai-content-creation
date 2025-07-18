import asyncio
import traceback
import uuid
from typing import Any, TypedDict

from langchain_community.callbacks.manager import get_openai_callback
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langfuse import get_client
from langfuse.langchain import CallbackHandler
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from open_deep_research.multi_agent import supervisor_builder
from pydantic import BaseModel, Field

from sloppy.celery_app import app
from sloppy.db.script_model import ScriptRepository, ScriptState
from sloppy.socketio_client import emit_task_completed, emit_task_failed
from sloppy.utils import load_envs

# DB Connection
script_mongo = ScriptRepository()
if script_mongo.test_connection():
    print("✅☘️ MongoDB Connected Succesfully!")
else:
    print("❌ Failed to Connect")


# Define structured output schema for the script
class ScriptLine(BaseModel):
    speaker: str = Field(
        description="Either 'Speaker 1:' or 'Speaker 2:' to identify the speaker"
    )
    line_content: str = Field(description="The actual content/dialogue for this line")


class PodcastScript(BaseModel):
    title: str = Field(description="Title of the podcast episode")
    topic: str = Field(description="Main topic being discussed")
    script_lines: list[ScriptLine] = Field(
        description="List of dialogue lines between the two speakers"
    )

    def to_formatted_script(self) -> str:
        """Convert structured script to the desired Speaker 1:/Speaker 2: format"""
        formatted_lines = []
        for line in self.script_lines:
            formatted_lines.append(f"{line.speaker} {line.line_content}")
        return "\n".join(formatted_lines)


# Define our custom state
class ScriptGenerationState(TypedDict):
    cost: float
    messages: list
    final_script: str | None
    script_ready: bool


def extract_structured_script(state: ScriptGenerationState) -> dict[str, Any]:
    """Extract script from the last AIMessage"""
    print("🎬 Extracting script from state...")

    messages = state.get("messages", [])
    print(f"   Found {len(messages)} messages in state")

    # Get the last AIMessage (this is where the script always is)
    for message in reversed(messages):
        if (
            isinstance(message, AIMessage)
            and message.content
            and ("Speaker 1:" in message.content or "Speaker 2:" in message.content)
        ):
            content = message.content
            print(f"   Found script in AIMessage (length: {len(content)} chars)")

            # Parse into structured format
            script_lines = []
            lines = content.split("\n")  # type: ignore

            for line in lines:
                line = line.strip()
                if line.startswith("Speaker 1:") or line.startswith("Speaker 2:"):
                    speaker = (
                        "Speaker 1:" if line.startswith("Speaker 1:") else "Speaker 2:"
                    )
                    line_content = line[
                        len(speaker) :
                    ].strip()  # Remove 'Speaker 1:' or 'Speaker 2:'
                    if line_content:
                        script_lines.append(
                            ScriptLine(speaker=speaker, line_content=line_content)
                        )

            if len(script_lines) >= 10:
                print(f"   ✅ Successfully parsed {len(script_lines)} script lines")
                formatted_script = PodcastScript(
                    title="NewsBreak Podcast",
                    topic="Current News",
                    script_lines=script_lines,
                ).to_formatted_script()

                return {
                    "final_script": formatted_script,
                    "script_ready": True,
                    "cost": state.get("cost", 0.0),
                }

    # If we get here, no script found
    print("   ❌ No script found in messages!")
    return {"final_script": None, "script_ready": False, "cost": state.get("cost", 0.0)}


# Agent setup
print("🔧 Setting up agent...")
checkpointer = MemorySaver()

try:
    # Compile the original agent
    original_agent = supervisor_builder.compile(
        name="news_researcher", checkpointer=checkpointer
    )
    print(f"   Original agent compiled: {type(original_agent)}")

    async def call_original_agent(state: ScriptGenerationState) -> dict[str, Any]:
        """Call original agent and extract results from state"""
        print("🤖 Calling original agent...")

        messages = state.get("messages", [])
        input_dict = {"messages": messages}

        config = {
            "configurable": {
                "thread_id": str(uuid.uuid4()),
                "search_api": "tavily",
                "supervisor_model": "openai:o1",
                "researcher_model": "openai:o1",
            }
        }

        # Call agent (always returns None)
        with get_openai_callback() as cb:
            await original_agent.ainvoke(input_dict, config=config)  # type: ignore

            # Extract results from state (this is where the actual results are)
            final_state = original_agent.get_state(config)  # type: ignore
            result = final_state.values

            print(
                f"   ✅ Agent completed, extracted {len(result['messages'])} "
                "messages from state"
            )

            return {"messages": result["messages"], "cost": cb.total_cost}

    # Create the wrapper graph
    wrapper_graph = StateGraph(ScriptGenerationState)
    wrapper_graph.add_node("call_agent", call_original_agent)
    wrapper_graph.add_node("extract_script", extract_structured_script)
    wrapper_graph.add_edge(START, "call_agent")
    wrapper_graph.add_edge("call_agent", "extract_script")
    wrapper_graph.add_edge("extract_script", END)

    # Compile the wrapper
    agent = wrapper_graph.compile(checkpointer=checkpointer)
    print(f"   Wrapper agent compiled: {list(agent.nodes.keys())}")

except Exception as e:
    print(f"❌ Error compiling agent: {e}")
    raise


# Script generation task
langfuse_client = get_client()
langfuse_handler = CallbackHandler()


@app.task(bind=True)
def generate_news_script(self, topic):
    """Generate news script"""
    load_envs()
    task_id = self.request.id
    print(f"\n🚀 Starting script generation for topic: {topic}")

    langfuse = get_client()
    script_gen_prompt = langfuse.get_prompt("script-gen").prompt
    print(f"✅ Script-gen prompt fetched from Langfuse: {script_gen_prompt}")

    messages = [
        SystemMessage(content=script_gen_prompt),
        HumanMessage(
            content=f"Generate a complete news podcast script about {topic}. "
            "Create a heated debate between two co-hosts."
        ),
    ]
    input_dict = {"messages": messages, "final_script": None, "script_ready": False}

    async def run_async():
        config = {
            "configurable": {"thread_id": str(uuid.uuid4())},
            "callbacks": [langfuse_handler],
        }
        response = await asyncio.wait_for(
            agent.ainvoke(input_dict, config=config),  # type: ignore
            timeout=300,
        )
        return response

    try:
        result = asyncio.run(run_async())
        if (
            result
            and result.get("script_ready")
            and result.get("final_script")
            and result.get("cost")
        ):
            script = result["final_script"]
            cost = result["cost"]
            response_dict = {
                "script": script,
                "state": ScriptState.GENERATED,
                "script_cost": cost,
                "success": True,
            }
            print(f"✅ Script generated: {len(script)} characters")
            script_mongo.update_script(
                task_id,
                response_dict,
            )
            script_mongo.clear_active_task(task_id)
            emit_task_completed(task_id)
            return response_dict
        else:
            emit_task_failed(task_id, "ValueError - Script generation failed")
            raise ValueError("Script generation failed")
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        script_mongo.clear_active_task(task_id)
        emit_task_failed(task_id, f"SCRIPT_GENERATION_FAILED: {str(e)}")
        raise
