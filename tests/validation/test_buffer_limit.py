"""
Test for the message buffer limits and summarization.
"""
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from letta.agents.base_agent import BaseAgent
from letta.constants import DEFAULT_MAX_MESSAGE_BUFFER_LENGTH, DEFAULT_MIN_MESSAGE_BUFFER_LENGTH
from letta.schemas.enums import MessageRole
from letta.schemas.letta_message_content import TextContent
from letta.schemas.message import Message
from letta.services.summarizer.enums import SummarizationMode
from letta.services.summarizer.summarizer import Summarizer

# Test parameters
MESSAGE_BUFFER_LIMIT = DEFAULT_MAX_MESSAGE_BUFFER_LENGTH
MESSAGE_BUFFER_MIN = DEFAULT_MIN_MESSAGE_BUFFER_LENGTH
SUMMARY_TEXT = "Discussion about Earl Grey tea: User mentioned enjoying Earl Grey tea, particularly its bergamot flavor and how it pairs well with milk."

@pytest.fixture
def mock_summarizer_agent():
    agent = AsyncMock(spec=BaseAgent)
    agent.step.return_value = [Message(role=MessageRole.assistant, content=[TextContent(type="text", text=SUMMARY_TEXT)])]
    agent.update_message_transcript = AsyncMock(return_value=None)
    return agent

@pytest.fixture
def tea_messages():
    base_time = datetime.now(timezone.utc)
    return [
        Message(
            role=MessageRole.user,
            content=[TextContent(type="text", text=json.dumps({"message": "I love drinking tea. My favorite is Earl Grey."}))],
            created_at=base_time
        ),
        Message(
            role=MessageRole.assistant,
            content=[TextContent(type="text", text=json.dumps({"message": "That's great! Earl Grey is a classic choice. I'd love to hear more about what you enjoy about it."}))],
            created_at=base_time
        ),
        Message(
            role=MessageRole.user,
            content=[TextContent(type="text", text=json.dumps({"message": "I love the bergamot flavor and how it goes well with milk."}))],
            created_at=base_time
        )
    ] + [
        # Add filler messages to exceed buffer
        Message(
            role=MessageRole.user if i % 2 == 0 else MessageRole.assistant,
            content=[TextContent(type="text", text=json.dumps({"message": f"Message {i}"}))],
            created_at=base_time
        )
        for i in range(MESSAGE_BUFFER_LIMIT + 5)
    ]

def test_buffer_summarization_retains_context(mock_summarizer_agent, tea_messages):
    """Test that buffer summarization retains important context about tea preferences."""
    summarizer = Summarizer(
        SummarizationMode.STATIC_MESSAGE_BUFFER,
        mock_summarizer_agent,
        message_buffer_limit=MESSAGE_BUFFER_LIMIT,
        message_buffer_min=MESSAGE_BUFFER_MIN
    )
    
    # Force summarization by sending more messages than the limit
    updated_messages, was_updated = summarizer._static_buffer_summarization(tea_messages, [], None)
    
    # Verify that summarization happened
    assert was_updated
    assert len(updated_messages) == MESSAGE_BUFFER_MIN
    
    # Verify the mock was called
    mock_summarizer_agent.step.assert_called()
    
    # The mock will return our SUMMARY_TEXT which contains the tea context
    summary_message = next(msg for msg in updated_messages if "earl grey" in msg.content[0].text.lower())
    assert summary_message is not None, "Tea context was lost in summarization"
    print("✅ TEST PASSED: Context about Earl Grey tea was retained in summary!")
    print(f"Summary message: {summary_message.content[0].text}")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
