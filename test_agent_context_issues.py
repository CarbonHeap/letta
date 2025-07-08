#!/usr/bin/env python3
"""
Test script to validate agent context window issues:
1. Tool messages not appearing in agent context
2. Missing timestamps for temporal awareness

This script creates a test agent and demonstrates the issues before fixes.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from typing import List, Dict, Any

# Add the letta directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from letta import create_client
from letta.schemas.agent import CreateAgent
from letta.schemas.llm_config import LLMConfig
from letta.schemas.message import Message
from letta.schemas.tool import Tool
from letta.schemas.enums import MessageRole
from letta.client.client import LocalClient


def create_test_tool() -> Tool:
    """Create a simple test tool that returns the current time"""
    tool_code = '''
def get_current_time() -> str:
    """
    Get the current UTC time.
    
    Returns:
        str: Current UTC time in ISO format
    """
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
'''
    
    return Tool(
        name="get_current_time",
        description="Get the current UTC time",
        source_code=tool_code,
        source_type="python",
        tags=["test", "time"]
    )


def print_message_context(messages: List[Message], title: str = "Message Context"):
    """Pretty print the message context to understand what the agent sees"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    
    for i, msg in enumerate(messages):
        print(f"\n[{i}] Role: {msg.role}")
        print(f"    ID: {msg.id}")
        print(f"    Created: {msg.created_at}")
        
        # Print content
        if msg.content:
            for content in msg.content:
                if hasattr(content, 'text'):
                    print(f"    Content: {content.text[:100]}...")
                    
        # Print tool calls
        if msg.tool_calls:
            print(f"    Tool Calls:")
            for tc in msg.tool_calls:
                print(f"      - {tc.function.name}({tc.function.arguments})")
                
        # Print tool returns
        if msg.tool_returns:
            print(f"    Tool Returns:")
            for tr in msg.tool_returns:
                print(f"      - Status: {tr.status}")
                if tr.stdout:
                    print(f"        Stdout: {tr.stdout[:100]}...")
                    
        # Check if this is a tool message
        if msg.role == MessageRole.tool:
            print(f"    Tool Name: {msg.name}")
            print(f"    Tool Call ID: {msg.tool_call_id}")
    
    print(f"\n{'='*60}\n")


def analyze_openai_format(messages: List[Dict[str, Any]], title: str = "OpenAI Format"):
    """Analyze the OpenAI formatted messages"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    
    for i, msg in enumerate(messages):
        print(f"\n[{i}] Role: {msg.get('role')}")
        
        # Check for content
        if 'content' in msg and msg['content']:
            content = msg['content']
            if isinstance(content, str):
                print(f"    Content: {content[:100]}...")
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        print(f"    Content: {item['text'][:100]}...")
                        
        # Check for tool calls
        if 'tool_calls' in msg and msg['tool_calls']:
            print(f"    Tool Calls: {len(msg['tool_calls'])} calls")
            for tc in msg['tool_calls']:
                print(f"      - {tc.get('function', {}).get('name')}")
    
    print(f"\n{'='*60}\n")


async def test_context_window_issues():
    """Test the agent context window issues"""
    print("Starting agent context window test...")
    
    # Create client
    client = create_client()
    print(f"Client created: {type(client)}")
    
    # Create test tool
    test_tool = create_test_tool()
    created_tool = client.create_tool(test_tool)
    print(f"Created tool: {created_tool.name}")
    
    # Create test agent with timestamp feature
    agent = client.create_agent(
        CreateAgent(
            name="ContextTestAgent",
            description="Agent for testing context window issues",
            system="You are a test agent. Always use the get_current_time tool when asked about time.",
            tool_ids=[created_tool.id],
            llm_config=LLMConfig(
                model="gpt-4o-mini",
                temperature=0.7,
            ),
            # Enable timestamp feature (if implemented)
            # include_timestamps=True,  # This field doesn't exist yet
        )
    )
    print(f"Created agent: {agent.name} (ID: {agent.id})")
    
    # Send messages and trigger tool use
    print("\n--- Test 1: Basic tool usage ---")
    response1 = client.send_message(
        agent_id=agent.id,
        role="user",
        message="What time is it?"
    )
    print(f"Response 1: {response1.messages[-1].content[0].text if response1.messages else 'No response'}")
    
    # Wait a moment
    await asyncio.sleep(2)
    
    print("\n--- Test 2: Follow-up message ---")
    response2 = client.send_message(
        agent_id=agent.id,
        role="user", 
        message="What time did you tell me before?"
    )
    print(f"Response 2: {response2.messages[-1].content[0].text if response2.messages else 'No response'}")
    
    # Get all messages
    print("\n--- Analyzing message history ---")
    all_messages = client.get_messages(agent_id=agent.id, limit=50)
    print(f"Total messages in history: {len(all_messages)}")
    
    # Print full context
    print_message_context(all_messages, "Full Message History")
    
    # Check what the agent actually sees (simulate context compilation)
    print("\n--- Simulating Agent Context View ---")
    
    # Import the conversion function
    from letta.server.rest_api.utils import convert_in_context_letta_messages_to_openai
    
    # Convert messages as the agent would see them
    openai_messages = convert_in_context_letta_messages_to_openai(all_messages)
    analyze_openai_format(openai_messages, "Agent's Context (OpenAI Format)")
    
    # Count message types
    message_counts = {}
    tool_message_count = 0
    for msg in all_messages:
        role = str(msg.role)
        message_counts[role] = message_counts.get(role, 0) + 1
        if msg.role == MessageRole.tool:
            tool_message_count += 1
            
    print("\n--- Message Type Summary ---")
    for role, count in message_counts.items():
        print(f"{role}: {count}")
    print(f"\nTool messages in history: {tool_message_count}")
    print(f"Tool messages in agent context: {sum(1 for m in openai_messages if m.get('role') == 'tool')}")
    
    # Check for timestamps in messages
    print("\n--- Timestamp Analysis ---")
    messages_with_timestamps = 0
    for msg in openai_messages:
        content = msg.get('content', '')
        if isinstance(content, str) and any(ts in content for ts in ['UTC]', 'GMT]', '20']):
            messages_with_timestamps += 1
            
    print(f"Messages with visible timestamps: {messages_with_timestamps}/{len(openai_messages)}")
    
    # Test the agent's temporal awareness
    print("\n--- Test 3: Temporal awareness ---")
    response3 = client.send_message(
        agent_id=agent.id,
        role="user",
        message="How long ago was my first message?"
    )
    print(f"Response 3: {response3.messages[-1].content[0].text if response3.messages else 'No response'}")
    
    return agent.id


def main():
    """Main test function"""
    print("Letta Agent Context Window Issue Test")
    print("=====================================")
    print(f"Test started at: {datetime.now(timezone.utc).isoformat()}")
    
    try:
        # Run async test
        agent_id = asyncio.run(test_context_window_issues())
        
        print("\n--- Test Summary ---")
        print("✗ Tool messages are being skipped in agent context (lines 382-386 in utils.py)")
        print("✗ No timestamps in message content for temporal awareness")
        print("✗ Agent cannot reference previous tool executions")
        print(f"\nTest agent ID: {agent_id}")
        
    except Exception as e:
        print(f"\nError during test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()