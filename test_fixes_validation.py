#!/usr/bin/env python3
"""
Test script to validate the agent context window fixes:
1. Tool messages now appear in agent context
2. Timestamps are included in messages
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
from letta.server.rest_api.utils import convert_in_context_letta_messages_to_openai


def main():
    print("=== Testing Agent Context Window Fixes ===")
    print(f"Started at: {datetime.now(timezone.utc)}")
    
    # Create client
    client = create_client()
    print(f"\n1. Client type: {type(client).__name__}")
    
    # Create a test tool
    tool_code = '''
def test_tool(message: str) -> str:
    """
    A test tool that returns a specific response.
    
    Args:
        message (str): Input message
        
    Returns:
        str: Tool response with timestamp
    """
    from datetime import datetime, timezone
    timestamp = datetime.now(timezone.utc).isoformat()
    return f"TOOL_RESPONSE: {message} at {timestamp}"
'''
    
    tool = client.create_tool(Tool(
        name="test_tool",
        description="Test tool for validation",
        source_code=tool_code,
        source_type="python"
    ))
    print(f"2. Created tool: {tool.name}")
    
    # Create agent with timestamps enabled
    agent = client.create_agent(CreateAgent(
        name="FixTestAgent",
        system="You are a test agent. Always use tools when asked.",
        tool_ids=[tool.id],
        llm_config=LLMConfig(model="gpt-4o-mini"),
        include_timestamps=True  # Enable timestamps
    ))
    print(f"3. Created agent: {agent.name} (timestamps: {agent.include_timestamps})")
    
    # Test 1: Use the tool
    print("\n=== Test 1: Tool Usage ===")
    response1 = client.send_message(
        agent_id=agent.id,
        role="user",
        message="Please use the test_tool with message 'validation test'"
    )
    print(f"Response received")
    
    # Test 2: Ask about tool result
    print("\n=== Test 2: Tool Memory ===")
    response2 = client.send_message(
        agent_id=agent.id,
        role="user",
        message="What was the exact response from test_tool including the timestamp?"
    )
    if response2.messages:
        response_text = response2.messages[-1].content[0].text
        print(f"Agent response: {response_text}")
        
        # Check if agent could reference the tool response
        if "TOOL_RESPONSE" in response_text or "timestamp" in response_text.lower():
            print("✅ SUCCESS: Agent can reference tool responses!")
        else:
            print("❌ ISSUE: Agent cannot see tool responses")
    
    # Get message history
    messages = client.get_messages(agent_id=agent.id, limit=20)
    
    # Test the conversion
    print("\n=== Testing Message Conversion ===")
    
    # Test without timestamps
    openai_format_no_ts = convert_in_context_letta_messages_to_openai(messages, include_timestamps=False)
    
    # Test with timestamps
    openai_format_with_ts = convert_in_context_letta_messages_to_openai(messages, include_timestamps=True)
    
    # Analyze results
    print(f"\nOriginal messages: {len(messages)}")
    print(f"Converted messages: {len(openai_format_no_ts)}")
    
    # Count tool messages
    tool_messages_original = sum(1 for m in messages if str(m.role.value if hasattr(m.role, 'value') else m.role) == "tool")
    tool_messages_converted = sum(1 for m in openai_format_no_ts if m.get('role') == 'tool')
    
    print(f"\nTool messages:")
    print(f"  Original: {tool_messages_original}")
    print(f"  Converted: {tool_messages_converted}")
    
    if tool_messages_original > 0 and tool_messages_converted > 0:
        print("✅ SUCCESS: Tool messages are preserved!")
    else:
        print("❌ ISSUE: Tool messages are still being filtered")
    
    # Check timestamps
    print("\n=== Timestamp Check ===")
    timestamps_found = 0
    for i, msg in enumerate(openai_format_with_ts):
        content = str(msg.get('content', ''))
        # Look for timestamp pattern [YYYY-MM-DD HH:MM:SS UTC]
        if '[20' in content and 'UTC]' in content:
            timestamps_found += 1
            if i < 3:  # Show first few examples
                print(f"  Message {i}: {content[:80]}...")
    
    print(f"\nMessages with timestamps: {timestamps_found}/{len(openai_format_with_ts)}")
    
    if timestamps_found > 0:
        print("✅ SUCCESS: Timestamps are included in messages!")
    else:
        print("❌ ISSUE: No timestamps found")
    
    # Final summary
    print("\n=== Summary ===")
    print(f"Tool message visibility: {'FIXED' if tool_messages_converted > 0 else 'NOT FIXED'}")
    print(f"Timestamp inclusion: {'WORKING' if timestamps_found > 0 else 'NOT WORKING'}")
    
    return agent.id


if __name__ == "__main__":
    try:
        agent_id = main()
        print(f"\nTest completed. Agent ID: {agent_id}")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()