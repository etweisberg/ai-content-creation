import uuid

from langgraph.checkpoint.memory import MemorySaver
from open_deep_research.multi_agent import supervisor_builder

from sloppy.celery_app import app

# Agent setup
checkpointer = MemorySaver()
agent = supervisor_builder.compile(name="news_researcher", checkpointer=checkpointer)
config = {
    "thread_id": str(uuid.uuid4()),
    "search_api": "tavily",
    "supervisor_model": "openai:o3",
    "researcher_model": "openai:o3",
    "mcp_server_config": {
        "youtube-transcript": {
            "command": "npx",
            "args": ["-y", "@kimtaeyoon83/mcp-server-youtube-transcript"],
        }
    },
}
# Set up thread configuration with the specified parameters
thread_config = {"configurable": config}


# Script generation task
@app.task
async def generate_news_script(topic):
    """Generate news script"""
    msg = [
        {
            "role": "system",
            "content": """
            You are an AI agent with the ability tasked with generating
            a script for a news podcast. You have the ability to search
            the internet using tavily.

            Here is some documentation about your search capability:
            How does the Search API work?
            Traditional search APIs such as Google, Serp and Bing retrieve search
            results
            based on a user query. However, the results are sometimes irrelevant
            to the goal of the
            search, and return simple URLs and snippets of content which are
            not always relevant.
            Because of this, any developer would need to then scrape the sites to
            extract
            relevant content, filter irrelevant information, optimize the content
            to fit
            LLM context limits, and more.
            This task is a burden and requires a lot of time and effort to complete.
            The Tavily Search API takes care of all of this for you in a single
            API call.
            The Tavily Search API aggregates up to 20 sites per a single API call,
            and uses proprietary AI to score, filter and rank the top most
            relevant sources and content to your task, query or goal.
            In addition, Tavily allows developers to add custom fields such as
            context and limit response tokens to enable the optimal search experience
            for LLMs.

            Tavily can also help your AI agent make better decisions by including
            a short answer for cross-agent communication.
            Your job is to generate a script for a podcast
            for the user about the news topic they requested.
            The script should be formatted like the following example:
            [S1] Hey. how are you doing?
            [S2] Pretty good. Pretty good. What about you?
            [S1] I'm great. So happy to be speaking to you.
            [S2] Me too. This is some cool stuff. Huh?
            [S1] Yeah. I have been reading more about speech generation.
            [S2] Yeah.
            [S1] And it really seems like context is important.
            [S2] Definitely.
            It should involve 2 speakers that are co-hosts of the news discussion show.
            They should go back and forth and have disagreements and debates.
            Try to make the interaction as fiery as possible while maintaining
            believability that it is a professional news show. So, fierce debate
            without disrespect.
            You should look for YouTube debates / podcasts about the same topic
            and try to emulate that conversation without copying. Use the
            get_transcript tool from the youtube-transcript MCP server.
            """,
        },
        {"role": "user", "content": f"Generate a script about {topic}"},
    ]
    response = await agent.ainvoke({"messages": msg}, config=thread_config)
    return response
