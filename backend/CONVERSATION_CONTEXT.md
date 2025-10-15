# Multi-Turn Conversation Handling

## Overview

The enhanced conversation context system provides sophisticated multi-turn conversation handling with reference resolution, context window management, and automatic summarization for long threads.

## Key Features

### 1. Structured Context Management

**Context Components:**
- **Recent Messages**: Relevant conversation history
- **Topics**: Extracted main discussion themes
- **Entities**: Documents, values, dates referenced
- **Questions Asked**: Previous user queries
- **References**: Detected pronouns and demonstratives
- **Context Summary**: Concise conversation overview

**Example Context Structure:**
```python
{
    'recent_messages': [...],
    'topics': ['Product A', 'Performance', 'Pricing'],
    'entities': {
        'documents': ['technical_spec.pdf', 'pricing_guide.pdf'],
        'values': ['16GB', '$499', '2024'],
        'dates': ['2024-01-15']
    },
    'questions_asked': ['What is Product A?', 'How does it compare to B?'],
    'references': {
        'has_references': True,
        'pronouns': ['it', 'its'],
        'demonstratives': ['that'],
        'vague_references': ['the previous point']
    },
    'resolved_context': '[Referring to: Product A] How does it compare?',
    'context_summary': '3 questions asked | Topics: Product A, Pricing',
    'needs_summarization': False
}
```

### 2. Reference Resolution

Automatically detects and resolves ambiguous references in queries.

**Detected References:**
- **Pronouns**: it, its, they, them, their, he, she, him, her
- **Demonstratives**: this, that, these, those, the same, such
- **Vague References**: "the document", "the file", "the previous", "earlier", "mentioned"

**Resolution Strategy:**

**Example 1: Pronoun Resolution**
```
Conversation:
User: "What is Product A's memory capacity?"
Assistant: "Product A has 16GB RAM."
User: "How does it compare to Product B?"

Resolution:
Detected: pronoun "it"
Latest entity: "Product A"
Enhanced query: "[Referring to: Product A] How does it compare to Product B?"
```

**Example 2: Vague Reference Resolution**
```
Conversation:
User: "What are the pricing tiers?"
Assistant: "We have Basic ($99), Pro ($199), Enterprise ($499)."
User: "Tell me more about the previous pricing."

Resolution:
Detected: "the previous"
Context: "User previously asked about pricing tiers | Assistant replied about Basic/Pro/Enterprise"
Enhanced query: "[Previous context: pricing tiers discussion] Tell me more about the previous pricing."
```

### 3. Sliding Window Context Management

Intelligently manages context within token budgets to avoid overwhelming the model.

**Token Budget Management:**
- Maximum context: 4000 tokens
- Starts from most recent messages
- Works backwards until budget exhausted
- Estimates ~4 characters per token

**Adaptive Context Selection:**

| Query Type | Context Strategy | Message Count |
|------------|------------------|---------------|
| Follow-up with references | Last 5 messages | 5 |
| Comparison/Analytical | Full sliding window | Variable |
| Simple lookup | Last 3 messages | 3 |
| Default | Last 7 messages | 7 |

**Example:**
```python
# User has 50 messages in conversation
# Current query: "What about the pricing?"

messages = get_sliding_window_context(
    messages=all_50_messages,
    current_query="What about the pricing?",
    max_tokens=4000
)
# Returns last ~15-20 messages that fit in budget
```

### 4. Conversation Summarization

Automatically summarizes long conversations to maintain context efficiency.

**Trigger Conditions:**
- Message count ≥ 15
- Manual trigger by system
- Before context window overflow

**Summarization Methods:**

**AI-Powered Summary (Preferred):**
Uses OpenAI to generate intelligent summaries:
```python
summary = summarize_conversation(messages, openai_service)
# "User asked about Product A specifications and pricing.
#  Key info provided: 16GB RAM, $499 price point,
#  compared favorably to Product B."
```

**Fallback Simple Summary:**
Extractive summary when AI unavailable:
```python
summary = simple_summary(messages)
# "User asked about: Product A specifications |
#  Key information: Product A has 16GB RAM and costs $499"
```

**Summary Format:**
- 2-3 sentences
- Main topics discussed
- Key information provided
- Current context focus

### 5. Entity Extraction

Tracks important entities throughout the conversation.

**Extracted Entity Types:**
- **Documents**: Mentioned files, reports, papers
- **Topics**: Capitalized terms, quoted phrases
- **Values**: Numbers with units (GB, $, %, etc.)
- **Dates**: Various date formats

**Example:**
```python
entities = {
    'documents': ['technical_specs.pdf', 'user_manual.pdf'],
    'topics': ['Product A', 'Performance Metrics'],
    'values': ['16GB', '$499', '99%'],
    'dates': ['2024-01-15', '2024']
}
```

### 6. Context-Aware Query Enhancement

Enhances queries with resolved context before processing.

**Enhancement Process:**

1. **Detect References**
```python
query = "How does it compare?"
references = detect_references(query)
# {'has_references': True, 'pronouns': ['it']}
```

2. **Resolve References**
```python
resolved = resolve_references(query, history, entities)
# "[Referring to: Product A] How does it compare?"
```

3. **Add Entity Context**
```python
enhanced = enhance_query_with_context(query, context)
# "[Referring to: Product A] How does it compare?
#  [Context: Documents: technical_specs.pdf]"
```

## Integration with Query Processing

### Full Query Flow

```python
# 1. Get conversation history
messages = get_messages(conversation_id, limit=20)

# 2. Build structured context
context = get_relevant_context_for_query(
    messages=messages,
    current_query="How does it perform?",
    query_intent="analytical"
)

# 3. Enhance query with context
enhanced_query = enhance_query_with_context(
    "How does it perform?",
    context
)
# Result: "[Referring to: Product A] How does it perform?
#          [Context: Documents: technical_specs.pdf]"

# 4. Prepare context for LLM
context_string = prepare_context_for_llm(context)
# "Conversation Summary: 3 questions asked | Topics: Product A
#  Recent questions: What is Product A? | How much does it cost?
#  Referenced: documents: technical_specs.pdf | values: $499"

# 5. Pass to retrieval and generation
response = process_with_context(enhanced_query, context_string)
```

## Performance Optimizations

### 1. Context Caching
- Recent context cached per conversation
- Invalidated on new messages
- Reduces computation for rapid queries

### 2. Token Estimation
- Fast character-based estimation
- Avoids expensive tokenization
- ~4 characters per token rule

### 3. Lazy Summarization
- Only summarizes when needed (15+ messages)
- Summary cached until new messages
- Fallback to simple summary if AI fails

### 4. Selective Context Inclusion
- Intent-based context selection
- Simple queries get minimal context
- Complex queries get full context
- Reduces prompt size and costs

## Use Cases

### Use Case 1: Product Comparison Across Messages

```
User: "What are the specs of Product A?"
Bot: "Product A has 16GB RAM, 512GB SSD, Intel i7..."

User: "And Product B?"
# Reference resolved: "And [Product B specs]?"
# Context: Previous question about Product A specs
Bot: "Product B has 32GB RAM, 1TB SSD, Intel i9..."

User: "Which is better for gaming?"
# Context: Discussing Product A vs Product B
# Entity tracking: Both products in context
Bot: "Product B is better for gaming due to higher RAM..."
```

### Use Case 2: Multi-Document Discussion

```
User: "Summarize the technical specifications document"
# Entity tracked: technical_specs.pdf
Bot: "The technical specifications document outlines..."

User: "What about the pricing in that document?"
# Reference: "that document" → technical_specs.pdf
Bot: "The technical specifications document mentions..."

User: "Compare it to the competitor analysis"
# Reference: "it" → technical_specs.pdf
# New entity: competitor_analysis.pdf
Bot: "Comparing technical specifications to competitor analysis..."
```

### Use Case 3: Long Conversation with Summarization

```
[Messages 1-15: Discussing various products]

User: "What did we discuss about Product A?"
# Conversation summarized automatically
# Summary: "Discussion covered Products A-E, focus on pricing and specs"
Bot: "Earlier we discussed Product A's specifications: 16GB RAM..."
```

## Configuration Options

### Context Service Configuration

```python
context_service = ConversationContextService()
context_service.max_context_messages = 10  # Max messages to consider
context_service.max_context_tokens = 4000  # Token budget
context_service.summary_trigger_length = 15  # Messages before summary
```

### Query Service Integration

```python
# Get context adapted to query type
context = context_service.get_relevant_context_for_query(
    messages=conversation_history,
    current_query=user_query,
    query_intent='comparison'  # Affects context selection
)

# Enhance query
enhanced = context_service.enhance_query_with_context(
    query=user_query,
    context=context
)

# Prepare for LLM
context_string = context_service.prepare_context_for_llm(
    structured_context=context,
    include_summary=True  # Include AI summary if available
)
```

## Best Practices

### For System Design:
1. Always use sliding window for long conversations
2. Summarize conversations > 15 messages
3. Track entities throughout conversation
4. Resolve references before retrieval
5. Provide reference resolution feedback to LLM

### For Prompt Engineering:
1. Include context summary at top
2. List referenced entities explicitly
3. Add follow-up guidance for reference queries
4. Structure context with clear sections
5. Include retrieval metadata

### For Performance:
1. Cache context between rapid queries
2. Use simple summaries as fallback
3. Limit entity tracking to 5 per type
4. Estimate tokens, don't tokenize
5. Select context based on intent

## Monitoring & Debugging

### Context Logging

The system logs detailed context information:
```
Context: 8 msgs, References: True, Needs summary: False
Enhanced query: [Referring to: Product A] How does it compare?
Generated summary: User discussed Products A and B...
```

### Metrics to Track:
- Average context length (tokens)
- Reference resolution accuracy
- Summary generation rate
- Context cache hit rate
- Token budget utilization

## Future Enhancements

Potential improvements:
1. **Coreference Resolution**: Advanced NLP for better reference tracking
2. **Named Entity Recognition**: ML-based entity extraction
3. **Semantic Clustering**: Group related conversation segments
4. **User Preference Learning**: Adapt context selection to user patterns
5. **Multi-lingual Support**: Context management across languages
