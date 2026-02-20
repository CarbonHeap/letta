# Tea Problem Test Configuration

This configuration is designed to validate the fix for the "tea problem" - where the agent loses context about earlier conversation details (specifically tea preferences) after extended conversation.

## Test Environment Setup

1. Use the `tea-problem-test.json` configuration
2. Ensure OpenAI API credentials are properly set
3. Create the test_logs/tea_problem directory for transcripts

## Test Protocol

### Initial Context Setting (Messages 1-3)
```
User: "I like Earl Grey tea with a splash of milk"
[Agent Response]
User: "And I prefer it quite hot, just below boiling"
[Agent Response]
```

### Buffer Filling (Messages 4-18)
- Engage in conversation about various topics:
  - Current events
  - Technical questions
  - General chat
  - Weather
  - Any topic except tea

### Context Verification (Messages 19-20)
```
User: "What kind of tea did I say I like, and how do I take it?"
[Agent should recall: Earl Grey, splash of milk, very hot]
```

### Extended Validation (Optional)
- Continue conversation for another 10-15 messages
- Make another tea reference
- Verify context is still maintained

## Metrics to Monitor

1. Token Usage
   - Before/after summarization
   - Total for conversation

2. Response Times
   - Normal responses
   - Post-summarization responses

3. Memory Retention
   - Accuracy of tea preference recall
   - Completeness of recalled details

## Success Criteria

1. Core Memory Retention
   - Agent correctly recalls tea type (Earl Grey)
   - Agent remembers preparation details (splash of milk, very hot)

2. Performance Impact
   - Response time increase < 20% after summarization
   - Token usage within acceptable limits

3. Context Quality
   - Natural inclusion of past context
   - No confusion or mixing of details

## Test Environment Variables

```bash
export OPENAI_API_KEY=your_key_here
export LETTA_TEST_CONFIG=./tests/configs/llm_model_configs/tea-problem-test.json
```
