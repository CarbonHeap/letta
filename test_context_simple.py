#!/usr/bin/env python3
"""
Simple test script to validate agent context window issues.
This version doesn't use async for easier testing.
"""

import os
import sys
from datetime import datetime, timezone

# Add the letta directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from letta import create_client
from letta.schemas.agent import CreateAgent
from letta.schemas.llm_config import LLMConfig
from letta.schemas.tool import Tool


def main():
    print("=== Letta Agent Context Window Test ===")
    print(f"Started at: {datetime.now(timezone.utc)}")
    
    # Create client
    client = create_client()
    print(f"\n1. Client type: {type(client).__name__}")
    
    # Create a simple test tool
    tool_code = '''
def test_tool(message: str) -> str:
    """
    A simple test tool that echoes a message with timestamp.
    
    Args:
        message (str): Message to echo
        
    Returns:
        str: Echoed message with timestamp
    """
    from datetime import datetime, timezone
    timestamp = datetime.now(timezone.utc).isoformat()
    return f"[{timestamp}] Tool executed: {message}"
'''
    
    tool = client.create_tool(Tool(
        name="test_tool",
        description="Test tool that echoes with timestamp",
        source_code=tool_code,
        source_type="python"
    ))
    print(f"2. Created tool: {tool.name}")
    
    # Create agent
    agent = client.create_agent(CreateAgent(
        name="TestAgent",
        system="You are a test agent. Use the test_tool when asked.",
        tool_ids=[tool.id],
        llm_config=LLMConfig(model="gpt-4o-mini")
    ))
    print(f"3. Created agent: {agent.name}")
    
    # Test 1: Use the tool
    print("\n=== Test 1: Tool Usage ===")
    response1 = client.send_message(
        agent_id=agent.id,
        role="user",
        message="Please use the test_tool with message 'Hello World'"
    )
    print(f"User: Please use the test_tool with message 'Hello World'")
    print(f"Agent: {response1.messages[-1].content[0].text if response1.messages else 'No response'}")
    
    # Test 2: Ask about previous tool use
    print("\n=== Test 2: Tool Memory ===")
    response2 = client.send_message(
        agent_id=agent.id,
        role="user",
        message="What was the result when you used the test_tool?"
    )
    print(f"User: What was the result when you used the test_tool?")
    print(f"Agent: {response2.messages[-1].content[0].text if response2.messages else 'No response'}")
    
    # Get message history
    messages = client.get_messages(agent_id=agent.id, limit=20)
    
    # Analyze messages
    print(f"\n=== Message Analysis ===")
    print(f"Total messages: {len(messages)}")
    
    role_counts = {}
    tool_messages = []
    
    for msg in messages:
        role = str(msg.role.value if hasattr(msg.role, 'value') else msg.role)
        role_counts[role] = role_counts.get(role, 0) + 1
        
        if role == "tool":
            tool_messages.append(msg)
            
    print("\nMessage breakdown:")
    for role, count in role_counts.items():
        print(f"  {role}: {count}")
        
    print(f"\nTool messages found: {len(tool_messages)}")
    
    # Check what convert function does
    print("\n=== Testing Message Conversion ===")
    from letta.server.rest_api.utils import convert_in_context_letta_messages_to_openai
    
    openai_format = convert_in_context_letta_messages_to_openai(messages)
    print(f"Original messages: {len(messages)}")
    print(f"Converted messages: {len(openai_format)}")
    
    # Count roles in converted format
    converted_roles = {}
    for msg in openai_format:
        role = msg.get('role', 'unknown')
        converted_roles[role] = converted_roles.get(role, 0) + 1
        
    print("\nConverted message roles:")
    for role, count in converted_roles.items():
        print(f"  {role}: {count}")
        
    # Check for tool messages in converted format
    tool_in_converted = sum(1 for m in openai_format if m.get('role') == 'tool')
    print(f"\nTool messages in converted format: {tool_in_converted}")
    
    if len(tool_messages) > 0 and tool_in_converted == 0:
        print("\n❌ ISSUE CONFIRMED: Tool messages are being filtered out!")
    else:
        print("\n✓ Tool messages are preserved")
        
    # Check for timestamps
    print("\n=== Timestamp Check ===")
    timestamps_found = 0
    for msg in openai_format[1:]:  # Skip system message
        content = str(msg.get('content', ''))
        # Look for ISO timestamp patterns
        if 'T' in content and 'Z' in content:
            timestamps_found += 1
            
    print(f"Messages with timestamps: {timestamps_found}")
    
    if timestamps_found == 0:
        print("❌ ISSUE CONFIRMED: No timestamps in message content!")
    else:
        print("✓ Timestamps found in messages")
        
    print("\n=== Test Complete ===")
    return agent.id


if __name__ == "__main__":
    try:
        agent_id = main()
        print(f"\nTest agent created with ID: {agent_id}")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()