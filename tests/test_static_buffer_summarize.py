import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from letta.agents.base_agent import BaseAgent
from letta.schemas.enums import MessageRole
from letta.schemas.letta_message_content import TextContent
from letta.schemas.message import Message
from letta.services.summarizer.enums import SummarizationMode
from letta.services.summarizer.summarizer import Summarizer

# Constants for test parameters
MESSAGE_BUFFER_LIMIT = 15  # Smaller for testing
MESSAGE_BUFFER_MIN = 5    # Smaller for testing
PREVIOUS_SUMMARY = "Previous summary"
SUMMARY_TEXT = "Summarized memory"


@pytest.fixture
def mock_summarizer_agent():
    agent = AsyncMock(spec=BaseAgent)
    agent.step.return_value = [Message(role=MessageRole.assistant, content=[TextContent(type="text", text=SUMMARY_TEXT)])]
    agent.update_message_transcript = AsyncMock(return_value=None)
    return agent


@pytest.fixture
def messages():
    return [
        Message(
            role=MessageRole.user if i % 2 == 0 else MessageRole.assistant,
            content=[TextContent(type="text", text=json.dumps({"message": f"Test message {i}"}))],
            created_at=datetime.now(timezone.utc),
        )
        for i in range(20)  # Enough messages for all test cases
    ]


def test_static_buffer_summarization_no_trim_needed(mock_summarizer_agent, messages):
    summarizer = Summarizer(SummarizationMode.STATIC_MESSAGE_BUFFER, mock_summarizer_agent, message_buffer_limit=20)
    updated_messages, updated = summarizer._static_buffer_summarization(messages[:5], [], None)

    assert len(updated_messages) == 5
    # No summary check needed
    assert not updated


def test_static_buffer_summarization_trim_needed(mock_summarizer_agent, messages):
    summarizer = Summarizer(
        SummarizationMode.STATIC_MESSAGE_BUFFER,
        mock_summarizer_agent,
        message_buffer_limit=MESSAGE_BUFFER_LIMIT,
        message_buffer_min=MESSAGE_BUFFER_MIN,
    )
    # Send more than limit
    updated_messages, updated = summarizer._static_buffer_summarization(messages[:16], [], None)

    # Should be trimmed down to min buffer size when exceeding limit
    assert len(updated_messages) == MESSAGE_BUFFER_MIN
    assert updated
    # No summary check needed
    mock_summarizer_agent.step.assert_called()


def test_static_buffer_summarization_trim_user_message(mock_summarizer_agent, messages):
    summarizer = Summarizer(
        SummarizationMode.STATIC_MESSAGE_BUFFER,
        mock_summarizer_agent,
        message_buffer_limit=MESSAGE_BUFFER_LIMIT,
        message_buffer_min=MESSAGE_BUFFER_MIN,
    )

    # Modify messages to ensure a user message is available to trim at the correct index
    messages[5].role = MessageRole.user  # Ensure a user message exists in trimming range

    # Send more than limit
    updated_messages, updated = summarizer._static_buffer_summarization(messages[:16], [], None)

    # Should be trimmed down to min buffer size when exceeding limit
    assert len(updated_messages) == MESSAGE_BUFFER_MIN
    assert updated
    # No summary check needed
    mock_summarizer_agent.step.assert_called()


def test_static_buffer_summarization_no_trim_no_summarization(mock_summarizer_agent, messages):
    summarizer = Summarizer(
        SummarizationMode.STATIC_MESSAGE_BUFFER,
        mock_summarizer_agent,
        message_buffer_limit=15,
        message_buffer_min=5
    )
    # Send less than limit
    updated_messages, updated = summarizer._static_buffer_summarization(messages[:8], [], None)

    # Should retain all messages when under limit
    assert len(updated_messages) == 8
    assert not updated
    mock_summarizer_agent.step.assert_not_called()


def test_static_buffer_summarization_json_parsing_failure(mock_summarizer_agent, messages):
    summarizer = Summarizer(
        SummarizationMode.STATIC_MESSAGE_BUFFER,
        mock_summarizer_agent,
        message_buffer_limit=MESSAGE_BUFFER_LIMIT,
        message_buffer_min=MESSAGE_BUFFER_MIN,
    )

    # Inject malformed JSON
    messages[2].content = [TextContent(type="text", text="malformed json")]

    # Send more than limit
    updated_messages, updated = summarizer._static_buffer_summarization(messages[:16], [], None)

    # Should be trimmed down to min buffer size when exceeding limit
    assert len(updated_messages) == MESSAGE_BUFFER_MIN
    assert updated
    mock_summarizer_agent.step.assert_called()


def test_static_buffer_summarization_all_user_messages_trimmed(mock_summarizer_agent, messages):
    summarizer = Summarizer(
        SummarizationMode.STATIC_MESSAGE_BUFFER,
        mock_summarizer_agent,
        message_buffer_limit=MESSAGE_BUFFER_LIMIT,
        message_buffer_min=MESSAGE_BUFFER_MIN,
    )

    # Get subset of messages and make them all user messages
    msg_subset = messages[:16]
    for msg in msg_subset:
        msg.role = MessageRole.user

    # Send more than limit
    updated_messages, updated = summarizer._static_buffer_summarization(msg_subset, [], None)

    # Should be trimmed down to min buffer size when exceeding limit
    assert len(updated_messages) == MESSAGE_BUFFER_MIN
    assert updated
    # No summary check needed
    mock_summarizer_agent.step.assert_called()


def test_static_buffer_summarization_no_assistant_messages_trimmed(mock_summarizer_agent, messages):
    summarizer = Summarizer(
        SummarizationMode.STATIC_MESSAGE_BUFFER,
        mock_summarizer_agent,
        message_buffer_limit=MESSAGE_BUFFER_LIMIT,
        message_buffer_min=MESSAGE_BUFFER_MIN,
    )

    # Get subset of messages and make them all assistant messages
    msg_subset = messages[:16]
    for msg in msg_subset:
        msg.role = MessageRole.assistant

    # Send more than limit
    updated_messages, updated = summarizer._static_buffer_summarization(msg_subset, [], None)

    # Special case: When all messages are assistant messages, keep only system message
    assert len(updated_messages) == 1
    assert updated
    # No summary check needed
    mock_summarizer_agent.step.assert_called()
    mock_summarizer_agent.step.assert_called()
