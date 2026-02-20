# Letta Memory Mechanisms

## Core Memory

### Base Classes
```python
class Memory(BaseModel):
    blocks: List[Block]
    file_blocks: List[Block]
    prompt_template: str

    def compile(self) -> str
    def get_block(self, label: str) -> Block
    def update_block_value(self, label: str, value: str)
    def set_prompt_template(self, template: str)

class Block(BaseModel):
    value: str
    limit: int 
    label: str
    description: Optional[str]
    metadata_: Dict
```

### Core Memory Functions
```python
def core_memory_append(
    label: str,      # Block to append to
    content: str     # Content to append
) -> None

def core_memory_replace(
    label: str,      # Block to modify
    old_content: str,# Content to replace
    new_content: str # New content
) -> None
```

## Recall Memory

### Configuration
```python
MESSAGE_BUFFER_LIMIT = 10
MESSAGE_BUFFER_MIN = 3
```

### Functions
```python
def conversation_search(
    query: str,      # Search term
    page: int = 0    # Results page
) -> List[Message]

def get_in_context_messages(
    agent_id: str    # Agent to get messages for
) -> List[Message]

def retain_messages(
    messages: List[Message],
    min_retain: int  # Minimum to keep
) -> List[Message]
```

## Archival Memory

### Interface
```python
def archival_memory_insert(
    content: str,    # Content to store
    metadata: Dict   # Optional metadata
) -> str            # Memory ID

def archival_memory_search(
    query: str,      # Search query
    page: int = 0,   # Results page
    filters: Dict    # Optional filters
) -> List[Memory]

def get_archival_memory(
    memory_id: str   # Memory to retrieve
) -> Memory
```

## Context Window Management

### Classes
```python
class ContextWindowOverview(BaseModel):
    context_window_size_max: int
    context_window_size_current: int
    num_messages: int
    num_archival_memory: int
    num_recall_memory: int
    num_tokens_external_memory_summary: int
    external_memory_summary: str
    num_tokens_system: int
    num_tokens_core_memory: int
    num_tokens_summary_memory: int
    num_tokens_functions_definitions: int
    num_tokens_messages: int
```

### Functions
```python
def get_context_window(
    agent_id: str    # Agent to analyze
) -> ContextWindowOverview

def count_tokens(
    content: str     # Content to count
) -> int
```

## Memory Agent

### Core Functions
```python
def store_memories(
    chunks: List[Dict[
        start_index: int,
        end_index: int,
        context: str
    ]]
) -> None

def rethink_memory(
    new_memory: str  # Updated memory content
) -> None

def finish_rethinking_memory() -> None
```

### Memory Maintenance
```python
def compile_memory_metadata_block(
    memory_edit_timestamp: datetime,
    timezone: str,
    previous_message_count: int,
    archival_memory_size: int
) -> str

def segment_conversation(
    messages: List[Message]
) -> List[Dict]
```

## Memory Validation

### Functions
```python
def validate_block_content(
    block: Block,
    content: str
) -> bool

def validate_memory_size(
    memory: Memory
) -> bool

def validate_block_metadata(
    metadata: Dict
) -> bool
```
