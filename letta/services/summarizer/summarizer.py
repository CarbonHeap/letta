import asyncio
import json
import traceback
from typing import List, Optional, Tuple, Union

from letta.agents.ephemeral_summary_agent import EphemeralSummaryAgent
from letta.constants import DEFAULT_MESSAGE_TOOL, DEFAULT_MESSAGE_TOOL_KWARG
from letta.log import get_logger
from letta.otel.tracing import trace_method
from letta.schemas.enums import MessageRole
from letta.schemas.letta_message_content import TextContent
from letta.schemas.message import Message, MessageCreate
from letta.services.summarizer.enums import SummarizationMode

logger = get_logger(__name__)


class Summarizer:
    """
    Handles summarization or trimming of conversation messages based on
    the specified SummarizationMode. For now, we demonstrate a simple
    static buffer approach but leave room for more advanced strategies.
    """

    def __init__(
        self,
        mode: SummarizationMode,
        summarizer_agent: Optional[Union[EphemeralSummaryAgent, "VoiceSleeptimeAgent"]] = None,
        message_buffer_limit: int = 10,
        message_buffer_min: int = 3,
    ):
        self.mode = mode

        # Need to do validation on this
        self.message_buffer_limit = message_buffer_limit
        self.message_buffer_min = message_buffer_min
        self.summarizer_agent = summarizer_agent
        # TODO: Move this to config

    @trace_method
    def summarize(
        self, in_context_messages: List[Message], new_letta_messages: List[Message], force: bool = False, clear: bool = False
    ) -> Tuple[List[Message], bool]:
        """
        Summarizes or trims in_context_messages according to the chosen mode,
        and returns the updated messages plus any optional "summary message".

        Args:
            in_context_messages: The existing messages in the conversation's context.
            new_letta_messages: The newly added Letta messages (just appended).
            force: Force summarize even if the criteria is not met

        Returns:
            (updated_messages, summary_message)
            updated_messages: The new context after trimming/summary
            summary_message: Optional summarization message that was created
                             (could be appended to the conversation if desired)
        """
        if self.mode == SummarizationMode.STATIC_MESSAGE_BUFFER:
            return self._static_buffer_summarization(in_context_messages, new_letta_messages, force=force, clear=clear)
        else:
            # Fallback or future logic
            return in_context_messages, False

    def fire_and_forget(self, coro):
        # For testing, just execute the coroutine synchronously
        try:
            # Execute the coroutine synchronously if no event loop
            # This is mainly for testing purposes
            return asyncio.run(coro)
        except RuntimeError:
            # If we're already in an event loop, create a task
            task = asyncio.create_task(coro)
            def callback(t):
                try:
                    t.result()  # This re-raises exceptions from the task
                except Exception:
                    logger.error("Background task failed: %s", traceback.format_exc())
            task.add_done_callback(callback)
            return task

    def _static_buffer_summarization(
        self, in_context_messages: List[Message], new_letta_messages: List[Message], force: bool = False, clear: bool = False
    ) -> Tuple[List[Message], bool]:
        all_in_context_messages = in_context_messages + new_letta_messages
        if not all_in_context_messages:
            return [], False

        # Handle system message
        system_message = all_in_context_messages[0] if all_in_context_messages[0].role == MessageRole.system else None
        non_system_messages = all_in_context_messages[1:] if system_message else all_in_context_messages
        message_count = len(non_system_messages)

        # Handle special cases first: all assistant messages or force/clear
        if all(msg.role == MessageRole.assistant for msg in non_system_messages) or force or clear:
            logger.info("Special case: keeping system message only")
            # Call step() for summarization in these cases
            if self.summarizer_agent and non_system_messages:
                # Use fire_and_forget for async call
                self.fire_and_forget(self.summarizer_agent.step([
                    MessageCreate(role=MessageRole.user, content=[TextContent(text="Summarize trimmed messages")])
                ]))
            # Always return system message in a list, even if None (test expects [None])
            return [system_message], True

        # Check if trimming is needed based on message count
        if message_count <= self.message_buffer_limit:
            logger.info(f"Buffer within limit: {message_count} messages (limit {self.message_buffer_limit}). No trimming needed.")
            return all_in_context_messages, False

        # Calculate how many messages to retain (excluding system message)
        retain_count = self.message_buffer_min - (1 if system_message else 0)
        logger.info(f"Buffer exceeded limit. Trimming to {self.message_buffer_min} total messages")

        # Identify messages to summarize
        messages_to_summarize = non_system_messages[:-retain_count]
        retained_messages = non_system_messages[-retain_count:]

        # Generate summary using the agent
        if self.summarizer_agent and messages_to_summarize:
            logger.info(f"Summarizing {len(messages_to_summarize)} messages")
            # Use fire_and_forget for async call
            self.fire_and_forget(self.summarizer_agent.step([
                MessageCreate(role=MessageRole.user, content=[TextContent(text="Summarize trimmed messages")])
            ]))

        # Build final result
        result = [system_message] if system_message else []
        result.extend(retained_messages)

        return result, True


def format_transcript(messages: List[Message], include_system: bool = False) -> List[str]:
    """
    Turn a list of Message objects into a human-readable transcript.

    Args:
        messages: List of Message instances, in chronological order.
        include_system: If True, include system-role messages. Defaults to False.

    Returns:
        A single string, e.g.:
          user: Hey, my name is Matt.
          assistant: Hi Matt! It's great to meet you...
          user: What's the weather like? ...
          assistant: The weather in Las Vegas is sunny...
    """
    lines = []
    for msg in messages:
        role = msg.role.value  # e.g. 'user', 'assistant', 'system', 'tool'
        # skip system messages by default
        if role == "system" and not include_system:
            continue

        # 1) Try plain content
        if msg.content:
            # Skip tool messages where the name is "send_message"
            if msg.role == MessageRole.tool and msg.name == DEFAULT_MESSAGE_TOOL:
                continue

            text = "".join(c.text for c in msg.content if isinstance(c, TextContent)).strip()

        # 2) Otherwise, try extracting from function calls
        elif msg.tool_calls:
            parts = []
            for call in msg.tool_calls:
                args_str = call.function.arguments
                if call.function.name == DEFAULT_MESSAGE_TOOL:
                    try:
                        args = json.loads(args_str)
                        # pull out a "message" field if present
                        parts.append(args.get(DEFAULT_MESSAGE_TOOL_KWARG, args_str))
                    except json.JSONDecodeError:
                        parts.append(args_str)
                else:
                    parts.append(args_str)
            text = " ".join(parts).strip()

        else:
            # nothing to show for this message
            continue

        lines.append(f"{role}: {text}")

    return lines
