import asyncio
import os
import traceback
import uuid
from pathlib import Path
from typing import Any, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from open_deep_research.multi_agent import supervisor_builder
from pydantic import BaseModel, Field

from sloppy.celery_app import app

# Load environment variables
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# Checking keys
print(f"OPENAI_API_KEY loaded: {'OPENAI_API_KEY' in os.environ}")
print(f"TAVILY_API_KEY loaded: {'TAVILY_API_KEY' in os.environ}")


# Define structured output schema for the script
class ScriptLine(BaseModel):
    """A single line in the podcast script"""

    speaker: str = Field(description="Either 'S1' or 'S2' to identify the speaker")
    line_content: str = Field(description="The actual content/dialogue for this line")


class PodcastScript(BaseModel):
    """Complete podcast script with structured dialogue"""

    title: str = Field(description="Title of the podcast episode")
    topic: str = Field(description="Main topic being discussed")
    script_lines: list[ScriptLine] = Field(
        description="List of dialogue lines between the two speakers",
        min_length=10,  # Ensure we get a substantial script
    )

    def to_formatted_script(self) -> str:
        """Convert structured script to the desired [S1]/[S2] format"""
        formatted_lines = []
        for line in self.script_lines:
            formatted_lines.append(f"[{line.speaker}] {line.line_content}")
        return "\n".join(formatted_lines)


# Define our custom state
class ScriptGenerationState(TypedDict):
    messages: list
    structured_script: PodcastScript | None
    final_script: str | None
    script_ready: bool
    completed_sections: list | None


def extract_structured_script(state: ScriptGenerationState) -> dict[str, Any]:
    """
    Extract and validate the structured script from the agent's response.
    Fails explicitly if no proper script is found.
    """
    print("🎬 Extracting structured script from state...")

    messages = state.get("messages", [])
    print(f"   Found {len(messages)} messages in state")

    structured_script = None

    # Look for the last AIMessage with script content
    for message in reversed(messages):
        if isinstance(message, AIMessage) and message.content:
            content = message.content
            print(f"   Found AIMessage with content length: {len(content)}")

            # Check if the content contains script-like dialogue
            if "[S1]" in content and "[S2]" in content:
                print("   ✅ Found script markers, attempting to parse...")

                # Parse the script format into our structured format
                try:
                    script_lines = []
                    lines = content.split("\n")  # type: ignore

                    for line in lines:
                        line = line.strip()
                        if line.startswith("[S1]") or line.startswith("[S2]"):
                            speaker = "S1" if line.startswith("[S1]") else "S2"
                            # Extract content after the speaker tag
                            line_content = line[4:].strip()  # Remove '[S1] ' or '[S2] '
                            if line_content:  # Only add non-empty lines
                                script_lines.append(
                                    ScriptLine(
                                        speaker=speaker, line_content=line_content
                                    )
                                )

                    if len(script_lines) >= 10:  # Ensure we have substantial content
                        # Extract topic from messages
                        topic = "current news"
                        for msg in messages:
                            if (
                                isinstance(msg, HumanMessage)
                                and "Generate a script about" in msg.content
                            ):
                                topic = msg.content.split("Generate a script about")[  # type: ignore
                                    -1
                                ].strip()
                                break

                        structured_script = PodcastScript(
                            title=f"NewsBreak: {topic.title()}",
                            topic=topic,
                            script_lines=script_lines,
                        )
                        print(
                            f"   ✅ Successfully parsed {len(script_lines)}"
                            " script lines"
                        )
                        break
                    else:
                        print(
                            f"   ⚠️ Found script format but insufficient lines:"
                            f" {len(script_lines)}"
                        )

                except Exception as e:
                    print(f"   ❌ Error parsing script format: {e}")

            elif content and len(content) > 100:
                print("   ⚠️ AIMessage found but no script format detected")
                print(f"   Content preview: {content[:200]}...")

    if structured_script is None:
        print("   ❌ No valid structured script found!")
        return {
            "structured_script": None,
            "final_script": None,
            "script_ready": False,
            "error": "No structured script was generated by the agent",
        }

    # Convert to formatted script
    formatted_script = structured_script.to_formatted_script()

    print("   ✅ Successfully extracted structured script:")
    print(f"      Title: {structured_script.title}")
    print(f"      Topic: {structured_script.topic}")
    print(f"      Lines: {len(structured_script.script_lines)}")
    print(f"      Formatted length: {len(formatted_script)} characters")

    return {
        "structured_script": structured_script,
        "final_script": formatted_script,
        "script_ready": True,
    }


# Agent setup with debugging
print("🔧 Setting up agent...")
checkpointer = MemorySaver()
print(f"   Checkpointer type: {type(checkpointer)}")

try:
    # Compile the original agent
    original_agent = supervisor_builder.compile(
        name="news_researcher", checkpointer=checkpointer
    )
    print(f"   Original agent compiled: {type(original_agent)}")
    print(f"   Original agent nodes: {list(original_agent.nodes.keys())}")

    # Create wrapper with enhanced prompting
    print("🔧 Creating wrapper agent...")

    async def call_original_agent(state: ScriptGenerationState) -> dict[str, Any]:
        """Call the original agent and return its messages"""
        print("🤖 Calling original agent...")

        # Use proper LangChain message objects
        messages = state.get("messages", [])
        input_dict = {"messages": messages}

        config = {
            "configurable": {
                "thread_id": str(uuid.uuid4()),
                "search_api": "tavily",
                "supervisor_model": "openai:o1",
                "researcher_model": "openai:o1",
                "mcp_server_config": {
                    "youtube-transcript": {
                        "command": "npx",
                        "args": ["-y", "@kimtaeyoon83/mcp-server-youtube-transcript"],
                    }
                },
            }
        }

        try:
            # Call the original agent
            result = await original_agent.ainvoke(input_dict, config=config)  # type: ignore

            print(f"   Original agent result type: {type(result)}")

            if result is None:
                print("   ⚠️ Original agent returned None, getting state...")
                final_state = original_agent.get_state(config)  # type: ignore
                if final_state and hasattr(final_state, "values"):
                    result = final_state.values
                    print(
                        f"   Retrieved state values:"
                        f"{list(result.keys()) if isinstance(result, dict) else 'None'}"
                    )
                    print("   State values content preview:")
                    if isinstance(result, dict) and "messages" in result:
                        messages = result["messages"]
                        print(f"      Found {len(messages)} messages in state")
                        for i, msg in enumerate(messages):
                            if hasattr(msg, "content") and msg.content:
                                print(
                                    f"      Message {i}: {type(msg).__name__}"
                                    f" - {msg.content[:100]}..."
                                )
                            elif isinstance(msg, dict) and "content" in msg:
                                print(
                                    f"      Message {i}: {msg.get('role', 'unknown')} -"
                                    f" {str(msg['content'])[:100]}..."
                                )
                    else:
                        print(f"      State keys: {list(result.keys())}")

            # Return the messages for processing
            if isinstance(result, dict) and "messages" in result:
                return {
                    "messages": result["messages"],
                    "completed_sections": result.get("completed_sections", []),
                }
            else:
                print(f"   ⚠️ Unexpected result format: {result}")
                return {
                    "messages": messages,  # Return original messages as fallback
                    "completed_sections": [],
                    "error": "Original agent returned unexpected format",
                }

        except Exception as e:
            print(f"   ❌ Error calling original agent: {e}")
            print(f"   Traceback: {traceback.format_exc()}")
            return {"messages": messages, "completed_sections": [], "error": str(e)}

    # Create the wrapper graph
    wrapper_graph = StateGraph(ScriptGenerationState)

    # Add nodes
    wrapper_graph.add_node("call_agent", call_original_agent)
    wrapper_graph.add_node("extract_script", extract_structured_script)

    # Add edges
    wrapper_graph.add_edge(START, "call_agent")
    wrapper_graph.add_edge("call_agent", "extract_script")
    wrapper_graph.add_edge("extract_script", END)

    # Compile the wrapper
    agent = wrapper_graph.compile(checkpointer=checkpointer)

    print(f"   Wrapper agent compiled successfully: {type(agent)}")
    print(f"   Wrapper agent nodes: {list(agent.nodes.keys())}")

except Exception as e:
    print(f"❌ Error compiling agent: {e}")
    print(f"   Traceback: {traceback.format_exc()}")
    raise

config = {
    "thread_id": str(uuid.uuid4()),
    "search_api": "tavily",
    "supervisor_model": "openai:o1",
    "researcher_model": "openai:o1",
    "mcp_server_config": {
        "youtube-transcript": {
            "command": "npx",
            "args": ["-y", "@kimtaeyoon83/mcp-server-youtube-transcript"],
        }
    },
}

# Set up thread configuration
thread_config = {"configurable": config}

print("🔧 Configuration:")
print(f"   Config keys: {list(config.keys())}")


# Script generation task
@app.task(bind=True)
def generate_news_script(self, topic):
    """Generate news script with structured output validation"""
    try:
        print(f"\n{'=' * 60}")
        print(f"🚀 Starting script generation for topic: {topic}")
        print(f"{'=' * 60}")

        # Create proper LangChain messages - single clear system prompt
        messages = [
            SystemMessage(
                content="""You are an AI agent tasked with
                generating a script for a news podcast.
You have the ability to search the internet using tavily.

Your ONLY job is to generate a complete podcast script about the requested topic.
The script MUST be in this EXACT format:
[S1] First speaker's dialogue
[S2] Second speaker's dialogue
[S1] More from first speaker
[S2] More from second speaker

REQUIREMENTS:
- Generate a heated but professional debate between two news co-hosts
- Minimum 15 exchanges between speakers
- Use ONLY [S1] and [S2] as speaker identifiers
- Make it engaging and argumentative while professional
- Do NOT ask questions or request clarification
- Generate the complete script immediately

End your response with the complete script in [S1]/[S2] format."""
            ),
            HumanMessage(
                content=f"Generate a complete news podcast script about {topic}."
                "Create a heated debate between two co-hosts."
            ),
        ]

        # Create the input dict using proper LangChain message objects
        input_dict = {
            "messages": messages,
            "structured_script": None,
            "final_script": None,
            "script_ready": False,
            "completed_sections": [],
        }

        async def run_async():
            print("\n🔍 Pre-invoke debugging:")
            print(f"   Agent type: {type(agent)}")
            print(f"   Agent nodes: {list(agent.nodes.keys())}")
            print(f"   Message types: {[type(msg).__name__ for msg in messages]}")

            try:
                print("\n🚀 Calling wrapper agent...")

                response = await asyncio.wait_for(
                    agent.ainvoke(input_dict, config=thread_config),  # type: ignore
                    timeout=300,
                )

                print("🎉 Response received!")
                print(f"   Response type: {type(response)}")

                if response is not None and isinstance(response, dict):
                    print(f"   Response keys: {list(response.keys())}")

                    # Check for explicit errors first
                    if "error" in response:
                        error_msg = response["error"]
                        print(f"   ❌ Explicit error found: {error_msg}")
                        raise ValueError(f"Script generation failed: {error_msg}")

                    # Check if script was successfully generated
                    script_ready = response.get("script_ready", False)
                    final_script = response.get("final_script")
                    structured_script = response.get("structured_script")

                    print(f"   Script ready: {script_ready}")
                    print(f"   Has final script: {final_script is not None}")
                    print(f"   Has structured script: {structured_script is not None}")

                    if script_ready and final_script:
                        print("   ✅ Script successfully generated!")
                        print(f"   Script length: {len(final_script)} characters")

                        if structured_script:
                            print("   Structured script details:")
                            print(f"      Title: {structured_script.title}")
                            print(f"      Topic: {structured_script.topic}")
                            print(f"      Lines: {len(structured_script.script_lines)}")

                        return final_script

                    elif not script_ready:
                        error_msg = "Script generation failed - script_ready is False"
                        print(f"   ❌ {error_msg}")
                        raise ValueError(error_msg)

                    elif final_script is None:
                        error_msg = (
                            "Script generation failed - no final_script generated"
                        )
                        print(f"   ❌ {error_msg}")
                        raise ValueError(error_msg)

                # If we get here, something went wrong
                error_msg = f"Unexpected response format: {response}"
                print(f"   ❌ {error_msg}")
                raise ValueError(error_msg)

            except TimeoutError as e:
                error_msg = "Script generation timed out after 5 minutes"
                print(f"❌ {error_msg}")
                raise ValueError(error_msg) from e

            except ValueError:
                # Re-raise ValueError as-is (these are our explicit failures)
                raise

            except Exception as e:
                error_msg = f"Unexpected error during script generation: {str(e)}"
                print(f"❌ {error_msg}")
                print(f"   Exception type: {type(e)}")
                traceback.print_exc()
                raise ValueError(error_msg) from e

        # Execute the async function
        print("\n⚡ Running async execution...")

        result = asyncio.run(run_async())

        print("\n📊 Final result analysis:")
        print(f"   Result type: {type(result)}")

        if isinstance(result, str):
            print(f"   Script length: {len(result)} characters")
            # Validate the script format
            if "[S1]" in result and "[S2]" in result:
                line_count = len(
                    [
                        line
                        for line in result.split("\n")
                        if line.strip().startswith("[S")
                    ]
                )
                print(f"   Script lines: {line_count}")
                if line_count >= 10:
                    print("   ✅ Script validation passed!")
                    return result
                else:
                    raise ValueError(
                        f"Generated script too short: only {line_count} lines"
                    )
            else:
                raise ValueError(
                    "Generated script does not contain required [S1]/[S2] format"
                )
        else:
            raise ValueError(f"Expected string result, got {type(result)}")

    except ValueError as e:
        # These are explicit failures we want to surface
        print(f"❌ Script generation failed: {str(e)}")
        return f"SCRIPT_GENERATION_FAILED: {str(e)}"

    except Exception as e:
        print("❌ Fatal error in generate_news_script:")
        print(f"   Error type: {type(e)}")
        print(f"   Error message: {str(e)}")
        traceback.print_exc()
        return f"FATAL_ERROR: {str(e)}"
