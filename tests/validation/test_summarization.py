"""
Test for the message summarization functionality, specifically checking the tea problem fix.
"""
import asyncio
from datetime import datetime, timezone
from typing import List, Optional

from letta.streaming_interface import StreamingRefreshCLIInterface

from letta.agent import AgentState
from letta.constants import DEFAULT_MAX_MESSAGE_BUFFER_LENGTH, DEFAULT_MIN_MESSAGE_BUFFER_LENGTH
from letta.memory import summarize_messages
from letta.schemas.agent import AgentType, LLMConfig
from letta.schemas.embedding_config import EmbeddingConfig
from letta.schemas.enums import MessageRole, ProviderCategory
from letta.schemas.memory import Memory
from letta.schemas.message import Message, TextContent
from letta.schemas.user import User

def create_test_messages() -> List[Message]:
    """Create a sequence of test messages about tea with various conversation patterns."""
    agent_id = "agent-test-1"
    base_time = datetime.now(timezone.utc)
    
    # Initial tea conversation
    messages = [
        Message(
            id="message-abcdef01",
            agent_id=agent_id,
            role=MessageRole.user,
            content=[TextContent(text="I love drinking tea. My favorite is Earl Grey.")],
            created_at=base_time
        ),
        Message(
            id="message-abcdef02",
            agent_id=agent_id,
            role=MessageRole.assistant,
            content=[TextContent(text="That's great! Earl Grey is a classic choice. I'd love to hear more about what you enjoy about it.")],
            created_at=base_time
        ),
        Message(
            id="message-abcdef03",
            agent_id=agent_id,
            role=MessageRole.user,
            content=[TextContent(text="I love the bergamot flavor and how it goes well with milk.")],
            created_at=base_time
        )
    ]
    
    # Add some unrelated conversation to create distance
    for i in range(10):
        messages.extend([
            Message(
                id=f"message-abcdef{i+10:02d}",
                agent_id=agent_id,
                role=MessageRole.user,
                content=[TextContent(text=f"Let's talk about something else. Topic {i}: weather.")],
                created_at=base_time
            ),
            Message(
                id=f"message-abcdef{i+20:02d}",
                agent_id=agent_id,
                role=MessageRole.assistant,
                content=[TextContent(text=f"The weather is quite nice today! What else would you like to discuss?")],
                created_at=base_time
            )
        ])
    
    # Return to tea topic to test context retention
    messages.extend([
        Message(
            id="message-abcdef99",
            agent_id=agent_id,
            role=MessageRole.user,
            content=[TextContent(text="By the way, do you remember what kind of tea I mentioned I liked?")],
            created_at=base_time
        ),
        Message(
            id="message-abcdefa0",
            agent_id=agent_id,
            role=MessageRole.assistant,
            content=[TextContent(text="Yes! You mentioned enjoying Earl Grey tea, particularly its bergamot flavor and how well it goes with milk.")],
            created_at=base_time
        ),
        Message(
            id="message-abcdefa1",
            agent_id=agent_id,
            role=MessageRole.user,
            content=[TextContent(text="That's right! I also enjoy other teas, but Earl Grey remains my favorite.")],
            created_at=base_time
        )
    ])
    
    return messages

def create_test_state() -> AgentState:
    """Create a test agent state."""
    return AgentState(
        id="agent-test-1",
        name="Test Agent",
        memory=Memory(blocks=[], file_blocks=[]),
        system="You are a helpful AI assistant.",
        llm_config=LLMConfig(
            model="gpt-4",
            model_endpoint_type="openai",
            context_window=8192,
            provider_name="openai",
            provider_category=ProviderCategory.base,
            model_endpoint="https://api.openai.com/v1"
        ),
        agent_type=AgentType.memgpt_agent,
        embedding_config=EmbeddingConfig.default_config(
            model_name="text-embedding-3-small",
            provider="openai"
        ),
        tools=[],
        sources=[],
        tags=["test"],
        message_ids=[],
        created_by_id="user-abcdef01"
    )

def create_test_user() -> User:
    """Create a test user."""
    return User(
        id="user-abcdef01",
        name="Test User",
        organization_id="org-00000000-0000-4000-8000-000000000000"
    )

def test_summarization():
    """Test that summarization preserves important context across a longer conversation."""
    messages = create_test_messages()
    agent_state = create_test_state()
    user = create_test_user()
    
    # Enable streaming for production
    agent_state.llm_config.stream = True
    
    # Initialize streaming interface
    streaming_interface = StreamingRefreshCLIInterface(fancy=True, separate_send_message=True)
    streaming_interface.stream_start()
    
    print(f"\nTesting summarization with {len(messages)} messages...")
    print(f"Buffer limits: max={DEFAULT_MAX_MESSAGE_BUFFER_LENGTH}, min={DEFAULT_MIN_MESSAGE_BUFFER_LENGTH}")
    
    # Get summary
    summary = summarize_messages(
        agent_state=agent_state,
        message_sequence_to_summarize=messages,
        actor=user
    )
    
    # Check for key elements in the summary
    checks = {
        "tea type": "earl grey" in summary.lower(),
        "flavor profile": "bergamot" in summary.lower(),
        "preparation": "milk" in summary.lower(),
        "context retention": "favorite" in summary.lower() or "prefer" in summary.lower(),
        "conversation flow": any(x in summary.lower() for x in ["mentioned", "discussed", "expressed", "shared", "attempted", "then"])
    }
    
    # Print detailed results
    print("\nContext Retention Check:")
    for aspect, retained in checks.items():
        print(f"  {'✅' if retained else '❌'} {aspect.title()}: {'Retained' if retained else 'Lost'}")
    
    print("\nFull Summary:")
    print(f"{summary}")
    
    # Overall test result
    if all(checks.values()):
        print("\n✅ TEST PASSED: All context elements were retained in summary!")
        return True
    else:
        print("\n❌ TEST FAILED: Some context elements were lost")
        print("Missing elements:", [k for k, v in checks.items() if not v])
        return False

if __name__ == "__main__":
    success = test_summarization()
    exit(0 if success else 1)
