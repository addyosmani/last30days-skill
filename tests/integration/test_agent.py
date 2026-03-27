"""Integration tests for the last30days ADK agent.

Tests the agent loads correctly and tools are properly registered.
Follows the agent-starter-pack testing pattern using Runner + InMemorySessionService.
"""

import pytest
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import root_agent


def test_agent_loads():
    """Agent should load with correct name and tools."""
    assert root_agent.name == "last30days"
    tool_names = [t.__name__ for t in root_agent.tools]
    assert "research_topic" in tool_names
    assert "search_reddit" in tool_names
    assert "search_x" in tool_names
    assert "search_youtube" in tool_names
    assert "search_web" in tool_names
    assert "search_hackernews" in tool_names


def test_agent_has_instruction():
    """Agent should have a non-empty system instruction."""
    assert root_agent.instruction
    assert "research" in root_agent.instruction.lower()


def test_runner_creates_session():
    """Runner should be able to create a session for the agent."""
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        session_service=session_service,
        app_name="test",
    )
    session = session_service.create_session_sync(
        user_id="test_user",
        app_name="test",
    )
    assert session.id is not None


@pytest.mark.skipif(
    not __import__("os").environ.get("GOOGLE_API_KEY")
    and not __import__("os").environ.get("GOOGLE_GENAI_USE_VERTEXAI"),
    reason="No Google AI credentials configured",
)
def test_agent_responds():
    """Agent should produce a response when given a message (requires API key)."""
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        session_service=session_service,
        app_name="test",
    )
    session = session_service.create_session_sync(
        user_id="test_user",
        app_name="test",
    )

    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text="Hello, what can you help me with?")],
    )

    events = list(
        runner.run(
            new_message=message,
            user_id="test_user",
            session_id=session.id,
        )
    )

    assert len(events) > 0
    has_text = any(
        event.content
        and event.content.parts
        and any(part.text for part in event.content.parts)
        for event in events
    )
    assert has_text
