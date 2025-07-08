"""
Unit tests for agent context window issues:
1. Tool messages not appearing in agent context
2. Missing timestamps for temporal awareness

These tests document the current behavior before fixes.
"""

import pytest
from datetime import datetime, timezone
from typing import List

from letta.schemas.message import Message, MessageCreate
from letta.schemas.enums import MessageRole
from letta.schemas.letta_message_content import TextContent
from letta.server.rest_api.utils import convert_in_context_letta_messages_to_openai
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall as OpenAIToolCall
from openai.types.chat.chat_completion_message_tool_call import Function as OpenAIFunction


class TestAgentContextWindow:
    """Test suite for agent context window issues"""
    
    def create_test_messages(self) -> List[Message]:
        """Create a set of test messages including tool calls"""
        messages = []
        
        # System message
        messages.append(Message(
            role=MessageRole.system,
            content=[TextContent(text="You are a test agent.")],
            organization_id="test-org",
            agent_id="test-agent",
            created_at=datetime.now(timezone.utc),
        ))
        
        # User message
        messages.append(Message(
            role=MessageRole.user,
            content=[TextContent(text="What time is it?")],
            organization_id="test-org",
            agent_id="test-agent",
            created_at=datetime.now(timezone.utc),
        ))
        
        # Assistant message with tool call
        tool_call = OpenAIToolCall(
            id="call_123",
            function=OpenAIFunction(
                name="get_current_time",
                arguments="{}"
            ),
            type="function"
        )
        messages.append(Message(
            role=MessageRole.assistant,
            content=[],
            tool_calls=[tool_call],
            organization_id="test-org",
            agent_id="test-agent",
            created_at=datetime.now(timezone.utc),
        ))
        
        # Tool response message
        messages.append(Message(
            role=MessageRole.tool,
            content=[TextContent(text="2024-01-15T10:30:00Z")],
            name="get_current_time",
            tool_call_id="call_123",
            organization_id="test-org",
            agent_id="test-agent",
            created_at=datetime.now(timezone.utc),
        ))
        
        # Assistant final response
        messages.append(Message(
            role=MessageRole.assistant,
            content=[TextContent(text="The current time is 10:30 AM UTC.")],
            organization_id="test-org",
            agent_id="test-agent",
            created_at=datetime.now(timezone.utc),
        ))
        
        return messages
    
    def test_tool_messages_filtered_out(self):
        """Test that tool messages are being filtered out in conversion"""
        messages = self.create_test_messages()
        
        # Verify we have tool messages in the original list
        tool_message_count = sum(1 for m in messages if m.role == MessageRole.tool)
        assert tool_message_count > 0, "Test setup should include tool messages"
        
        # Convert to OpenAI format
        openai_messages = convert_in_context_letta_messages_to_openai(messages)
        
        # Check if tool messages are preserved
        tool_in_openai = sum(1 for m in openai_messages if m.get('role') == 'tool')
        
        # This test documents the current behavior (tool messages are filtered)
        assert tool_in_openai == 0, "Currently, tool messages are filtered out"
        
        print(f"Original messages: {len(messages)}")
        print(f"Converted messages: {len(openai_messages)}")
        print(f"Tool messages filtered out: {tool_message_count}")
    
    def test_no_timestamps_in_content(self):
        """Test that timestamps are not included in message content"""
        messages = self.create_test_messages()
        
        # Convert to OpenAI format
        openai_messages = convert_in_context_letta_messages_to_openai(messages)
        
        # Check for timestamps in content
        messages_with_timestamps = 0
        for msg in openai_messages:
            content = msg.get('content', '')
            if isinstance(content, str):
                # Look for timestamp patterns
                if any(pattern in content for pattern in ['UTC]', '[20', 'T', 'Z']):
                    messages_with_timestamps += 1
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        text = item['text']
                        if any(pattern in text for pattern in ['UTC]', '[20', 'T', 'Z']):
                            messages_with_timestamps += 1
                            
        # This documents current behavior (no timestamps)
        assert messages_with_timestamps == 0, "Currently, no timestamps in message content"
    
    def test_agent_cannot_see_tool_responses(self):
        """Test that agent cannot reference previous tool responses"""
        messages = self.create_test_messages()
        
        # Add a user message asking about previous tool use
        messages.append(Message(
            role=MessageRole.user,
            content=[TextContent(text="What was the result of get_current_time?")],
            organization_id="test-org",
            agent_id="test-agent",
            created_at=datetime.now(timezone.utc),
        ))
        
        # Convert to see what agent sees
        openai_messages = convert_in_context_letta_messages_to_openai(messages)
        
        # Check if any message contains the tool response
        tool_response_visible = False
        for msg in openai_messages:
            content = str(msg.get('content', ''))
            if "2024-01-15T10:30:00Z" in content:
                tool_response_visible = True
                break
                
        # This documents current behavior
        assert not tool_response_visible, "Tool responses are not visible to agent"
    
    def test_message_count_reduction(self):
        """Test the reduction in message count after conversion"""
        messages = self.create_test_messages()
        original_count = len(messages)
        
        # Convert
        openai_messages = convert_in_context_letta_messages_to_openai(messages)
        converted_count = len(openai_messages)
        
        # Calculate reduction
        reduction = original_count - converted_count
        
        # We expect at least one message to be filtered (the tool message)
        assert reduction >= 1, f"Expected message reduction, got {reduction}"
        
        print(f"Message reduction: {reduction} messages filtered out")
        

def test_current_behavior_documentation():
    """
    This test documents the current behavior that needs to be fixed:
    
    1. Tool messages (role='tool') are filtered out in convert_in_context_letta_messages_to_openai
       - See lines 382-386 in letta/server/rest_api/utils.py
       - This prevents agents from referencing previous tool executions
       
    2. No timestamps are included in message content
       - Agents have no temporal awareness
       - Cannot answer questions like "how long ago" or "when did"
       
    3. The agent's context is missing critical information about tool executions
       - This limits the agent's ability to provide informed responses
       - Breaks continuity in multi-turn conversations involving tools
    """
    print("Current issues documented:")
    print("1. Tool messages filtered out (lines 382-386 in utils.py)")
    print("2. No timestamps in message content")
    print("3. Agent cannot reference tool execution history")
    

if __name__ == "__main__":
    # Run the documentation test
    test_current_behavior_documentation()
    
    # Run the test suite
    test = TestAgentContextWindow()
    
    print("\n=== Running Context Window Tests ===")
    
    try:
        test.test_tool_messages_filtered_out()
        print("✓ Confirmed: Tool messages are filtered out")
    except AssertionError as e:
        print(f"✗ Unexpected: {e}")
        
    try:
        test.test_no_timestamps_in_content()
        print("✓ Confirmed: No timestamps in content")
    except AssertionError as e:
        print(f"✗ Unexpected: {e}")
        
    try:
        test.test_agent_cannot_see_tool_responses()
        print("✓ Confirmed: Agent cannot see tool responses")
    except AssertionError as e:
        print(f"✗ Unexpected: {e}")
        
    try:
        test.test_message_count_reduction()
        print("✓ Confirmed: Messages are reduced in conversion")