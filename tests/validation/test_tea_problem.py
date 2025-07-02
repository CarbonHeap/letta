"""
Validation script for testing the tea problem fix (context retention).
This script simulates the tea conversation and verifies context retention
after buffer summarization.
"""
import asyncio
import json
import logging
from pathlib import Path

from letta.agent import Agent
from letta.constants import DEFAULT_MAX_MESSAGE_BUFFER_LENGTH, DEFAULT_MIN_MESSAGE_BUFFER_LENGTH

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_tea_conversation(agent: Agent) -> bool:
    """
    Run the tea conversation test scenario.
    Returns True if context is retained, False otherwise.
    """
    # Initial context about tea
    responses = []
    responses.append(await agent.step("I love drinking tea. My favorite is Earl Grey."))
    responses.append(await agent.step("What's your opinion on Earl Grey tea?"))
    
    # Force buffer summarization by exceeding DEFAULT_MAX_MESSAGE_BUFFER_LENGTH
    logger.info(f"Sending {DEFAULT_MAX_MESSAGE_BUFFER_LENGTH + 5} messages to force summarization...")
    for i in range(DEFAULT_MAX_MESSAGE_BUFFER_LENGTH + 5):
        await agent.step(f"Message {i} to fill buffer")
    
    # Test context retention
    response = await agent.step("What tea did I mention earlier?")
    responses.append(response)
    
    # Check if Earl Grey is mentioned in the response
    context_retained = "earl grey" in response.lower()
    
    # Log results
    logger.info("=== Test Results ===")
    logger.info(f"Buffer sizes: max={DEFAULT_MAX_MESSAGE_BUFFER_LENGTH}, min={DEFAULT_MIN_MESSAGE_BUFFER_LENGTH}")
    logger.info(f"Context retained: {context_retained}")
    logger.info(f"Final response: {response}")
    
    return context_retained

async def main():
    # Load test configuration
    config_path = Path(__file__).parent.parent / "configs" / "llm_model_configs" / "tea-problem-test.json"
    with open(config_path) as f:
        config = json.load(f)
    
    # Initialize agent with test config
    agent = Agent(config)
    
    try:
        logger.info("Starting tea problem validation test...")
        result = await run_tea_conversation(agent)
        
        if result:
            logger.info("✅ TEST PASSED: Context was retained after summarization")
            exit(0)
        else:
            logger.error("❌ TEST FAILED: Context was lost after summarization")
            exit(1)
            
    except Exception as e:
        logger.error(f"❌ TEST ERROR: {str(e)}")
        exit(2)

if __name__ == "__main__":
    asyncio.run(main())
