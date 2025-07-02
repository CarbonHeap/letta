"""
Simple validation script for testing the tea problem fix (context retention).
Uses mock objects for testing.
"""
import asyncio
from datetime import datetime, timezone
from typing import List, Optional

from letta.agent import Agent
from letta.constants import DEFAULT_MAX_MESSAGE_BUFFER_LENGTH, DEFAULT_MIN_MESSAGE_BUFFER_LENGTH
from letta.schemas.user import User
from letta.schemas.agent import AgentState, LLMConfig, AgentType
from letta.schemas.embedding_config import EmbeddingConfig
from letta.schemas.memory import Memory
from letta.schemas.message import Message, MessageCreate, TextContent
from letta.schemas.block import Block
from letta.schemas.enums import MessageRole, ProviderCategory

async def run_test():
    # Create mock user
    # Create mock user with required fields
    mock_user = User(
        id="user-abcdef01",
        name="Test User",
        organization_id="org-00000000-0000-4000-8000-000000000000",
created_at=datetime.now(timezone.utc)
    )

    # Create mock memory with empty blocks
    mock_memory = Memory(
        blocks=[],
        file_blocks=[],
        prompt_template="You are a helpful AI assistant."
    )

    # Create mock agent state
    # Create mock agent state with all required fields
    mock_agent_state = AgentState(
        id="agent-test-1",
        name="Test Agent",
        memory=mock_memory,
        system="You are a helpful AI assistant.",
        llm_config=LLMConfig(
            model="gpt-4",
            model_endpoint_type="openai",
            context_window=8192,
            provider_name="openai",
            provider_category=ProviderCategory.base
        ),
        message_ids=[],
        created_by_id=mock_user.id,
        created_at=datetime.now(timezone.utc),
        agent_type=AgentType.memgpt_agent,
        embedding_config=EmbeddingConfig.default_config(model_name="text-embedding-3-small", provider="openai"),
        tools=[],
        sources=[],
        tags=["test"],
        tool_exec_environment_variables=[]
    )

    # Initialize agent
    agent = Agent(
        interface=None,  # CLI interface not needed for test
        agent_state=mock_agent_state,
        user=mock_user
    )

    # Test sequence
    responses = []
    responses.append(await agent.step([
        MessageCreate(
            role=MessageRole.user,
            content=[TextContent(text="I love drinking tea. My favorite is Earl Grey.")])
    ]))
    
    responses.append(await agent.step([
        MessageCreate(
            role=MessageRole.user,
            content=[TextContent(text="What's your opinion on Earl Grey tea?")])
    ]))
    
    # Force buffer summarization by exceeding buffer limit
    for i in range(DEFAULT_MAX_MESSAGE_BUFFER_LENGTH + 5):
        await agent.step([
            MessageCreate(
                role=MessageRole.user,
                content=[TextContent(text=f"Message {i} to fill buffer")])
        ])
    
    # Test context retention
    final_response = await agent.step([
        MessageCreate(
            role=MessageRole.user,
            content=[TextContent(text="What tea did I mention earlier?")])
    ])
    
    # Check last response for mention of Earl Grey
    messages = final_response.steps_messages[-1] if final_response.steps_messages else []
    final_message = messages[-1] if messages else None
    
    if final_message and isinstance(final_message, Message):
        content = final_message.content[0].text if final_message.content else ""
        if "earl grey" in content.lower():
            print("✅ TEST PASSED: Context was retained!")
            print(f"Response: {content}")
            return True
    
    print("❌ TEST FAILED: Context was lost")
    print(f"Final response: {final_message.content if final_message else 'No response'}")
    return False

if __name__ == "__main__":
    success = asyncio.run(run_test())
    exit(0 if success else 1)
