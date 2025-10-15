from typing import List, Dict, Optional, Tuple
import re
from datetime import datetime

class ConversationContextService:
    def __init__(self):
        self.max_context_messages = 10
        self.max_context_tokens = 4000
        self.summary_trigger_length = 15

    def build_structured_context(
        self,
        messages: List[Dict],
        current_query: str,
        max_messages: int = None
    ) -> Dict:
        """Build structured conversation context"""
        if max_messages is None:
            max_messages = self.max_context_messages

        # Get recent messages
        recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages

        # Extract key information
        topics = self._extract_topics(recent_messages)
        entities = self._extract_entities_from_history(recent_messages)
        questions_asked = self._extract_questions(recent_messages)

        # Detect references in current query
        references = self._detect_references(current_query)

        # Resolve references
        resolved_context = self._resolve_references(
            current_query,
            recent_messages,
            entities,
            references
        )

        # Build context summary
        context_summary = self._build_context_summary(
            recent_messages,
            topics,
            entities
        )

        return {
            'recent_messages': recent_messages,
            'topics': topics,
            'entities': entities,
            'questions_asked': questions_asked,
            'references': references,
            'resolved_context': resolved_context,
            'context_summary': context_summary,
            'message_count': len(recent_messages),
            'needs_summarization': len(messages) > self.summary_trigger_length
        }

    def _extract_topics(self, messages: List[Dict]) -> List[str]:
        """Extract main topics from conversation"""
        topics = set()

        for msg in messages:
            if msg.get('role') != 'user':
                continue

            content = msg.get('content', '').lower()

            # Extract capitalized words (likely topics/entities)
            capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', msg.get('content', ''))
            topics.update(capitalized)

            # Extract quoted terms
            quoted = re.findall(r'["\']([^"\']+)["\']', content)
            topics.update(quoted)

        return list(topics)[:10]

    def _extract_entities_from_history(self, messages: List[Dict]) -> Dict[str, List[str]]:
        """Extract and categorize entities from conversation history"""
        entities = {
            'documents': [],
            'topics': [],
            'values': [],
            'dates': []
        }

        for msg in messages:
            content = msg.get('content', '')

            # Document names (usually capitalized or quoted)
            docs = re.findall(r'\b(?:document|file|report|paper|article)[\s:]+"?([^".,;]+)"?', content, re.IGNORECASE)
            entities['documents'].extend(docs)

            # Values (numbers with units)
            values = re.findall(r'\b\d+(?:\.\d+)?(?:\s*(?:GB|MB|KB|%|dollars?|\$|euros?|€))\b', content, re.IGNORECASE)
            entities['values'].extend(values)

            # Dates
            dates = re.findall(r'\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4})\b', content)
            entities['dates'].extend(dates)

        # Deduplicate
        for key in entities:
            entities[key] = list(set(entities[key]))[:5]

        return entities

    def _extract_questions(self, messages: List[Dict]) -> List[str]:
        """Extract questions from user messages"""
        questions = []

        for msg in messages:
            if msg.get('role') == 'user':
                content = msg.get('content', '')
                if '?' in content:
                    questions.append(content)

        return questions[-5:]

    def _detect_references(self, query: str) -> Dict:
        """Detect pronouns and references in query"""
        query_lower = query.lower()

        references = {
            'has_references': False,
            'pronouns': [],
            'demonstratives': [],
            'vague_references': []
        }

        # Pronouns
        pronouns = ['it', 'its', 'they', 'them', 'their', 'he', 'she', 'him', 'her']
        for pronoun in pronouns:
            if re.search(rf'\b{pronoun}\b', query_lower):
                references['pronouns'].append(pronoun)
                references['has_references'] = True

        # Demonstratives
        demonstratives = ['this', 'that', 'these', 'those', 'the same', 'such']
        for demo in demonstratives:
            if re.search(rf'\b{demo}\b', query_lower):
                references['demonstratives'].append(demo)
                references['has_references'] = True

        # Vague references
        vague = ['the document', 'the file', 'the previous', 'earlier', 'mentioned', 'above']
        for vague_term in vague:
            if vague_term in query_lower:
                references['vague_references'].append(vague_term)
                references['has_references'] = True

        return references

    def _resolve_references(
        self,
        current_query: str,
        messages: List[Dict],
        entities: Dict,
        references: Dict
    ) -> str:
        """Resolve references in query using conversation history"""
        if not references.get('has_references') or len(messages) < 2:
            return current_query

        resolved_query = current_query
        query_lower = current_query.lower()

        # Get recent context (last 3 messages)
        recent_context = messages[-3:] if len(messages) >= 3 else messages

        # Build context string
        context_parts = []
        for msg in recent_context:
            role = msg.get('role', '')
            content = msg.get('content', '')
            if role == 'user':
                context_parts.append(f"User previously asked: {content}")
            elif role == 'assistant':
                # Get first sentence
                first_sentence = content.split('.')[0] if '.' in content else content[:100]
                context_parts.append(f"Assistant replied: {first_sentence}")

        context_info = " | ".join(context_parts[-3:])

        # Resolve pronouns with document references
        if references.get('pronouns') or references.get('demonstratives'):
            if entities.get('documents'):
                latest_doc = entities['documents'][-1]
                # Replace "it" or "this" with document name in context
                resolved_query = f"[Referring to: {latest_doc}] {current_query}"

        # Add explicit context for vague references
        if references.get('vague_references'):
            resolved_query = f"[Previous context: {context_info}] Current question: {current_query}"

        return resolved_query

    def _build_context_summary(
        self,
        messages: List[Dict],
        topics: List[str],
        entities: Dict
    ) -> str:
        """Build a concise summary of conversation context"""
        if not messages:
            return ""

        summary_parts = []

        # Count messages
        user_msgs = sum(1 for m in messages if m.get('role') == 'user')
        summary_parts.append(f"{user_msgs} questions asked")

        # Add topics
        if topics:
            summary_parts.append(f"Topics discussed: {', '.join(topics[:3])}")

        # Add document references
        if entities.get('documents'):
            summary_parts.append(f"Documents referenced: {', '.join(entities['documents'][:2])}")

        # Add key values
        if entities.get('values'):
            summary_parts.append(f"Values mentioned: {', '.join(entities['values'][:2])}")

        return " | ".join(summary_parts)

    def get_sliding_window_context(
        self,
        messages: List[Dict],
        current_query: str,
        max_tokens: int = None
    ) -> List[Dict]:
        """Get messages within token budget using sliding window"""
        if max_tokens is None:
            max_tokens = self.max_context_tokens

        # Start from most recent and work backwards
        selected_messages = []
        estimated_tokens = self._estimate_tokens(current_query)

        for msg in reversed(messages):
            content = msg.get('content', '')
            msg_tokens = self._estimate_tokens(content)

            if estimated_tokens + msg_tokens > max_tokens:
                break

            selected_messages.insert(0, msg)
            estimated_tokens += msg_tokens

        return selected_messages

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 characters)"""
        return len(text) // 4

    def summarize_conversation(
        self,
        messages: List[Dict],
        openai_service = None
    ) -> str:
        """Generate conversation summary using AI"""
        if len(messages) < 5:
            return ""

        # Build conversation text
        conversation_text = []
        for msg in messages:
            role = msg.get('role', '')
            content = msg.get('content', '')
            conversation_text.append(f"{role.upper()}: {content}")

        full_conversation = "\n\n".join(conversation_text)

        # Use OpenAI to summarize if available
        if openai_service:
            try:
                summary_prompt = f"""Summarize this conversation in 2-3 sentences, focusing on:
1. Main topics discussed
2. Key information provided
3. Current context

Conversation:
{full_conversation}

Summary:"""

                summary = openai_service.generate_response(
                    system_prompt="You are a conversation summarizer. Create brief, informative summaries.",
                    user_message=summary_prompt,
                    context="",
                    is_document_query=False
                )
                return summary
            except:
                pass

        # Fallback: Simple extractive summary
        return self._simple_summary(messages)

    def _simple_summary(self, messages: List[Dict]) -> str:
        """Create simple extractive summary"""
        user_questions = []
        key_points = []

        for msg in messages:
            if msg.get('role') == 'user':
                user_questions.append(msg.get('content', ''))
            elif msg.get('role') == 'assistant':
                # Get first sentence
                content = msg.get('content', '')
                first_sentence = content.split('.')[0] if '.' in content else content[:150]
                key_points.append(first_sentence)

        summary_parts = []
        if user_questions:
            summary_parts.append(f"User asked about: {user_questions[-1][:100]}")
        if key_points:
            summary_parts.append(f"Key information: {key_points[-1][:100]}")

        return ". ".join(summary_parts)

    def should_summarize(self, message_count: int) -> bool:
        """Determine if conversation should be summarized"""
        return message_count >= self.summary_trigger_length

    def prepare_context_for_llm(
        self,
        structured_context: Dict,
        include_summary: bool = True
    ) -> str:
        """Prepare context string for LLM consumption"""
        parts = []

        # Add summary if available and requested
        if include_summary and structured_context.get('context_summary'):
            parts.append(f"Conversation Summary: {structured_context['context_summary']}")

        # Add recent questions
        if structured_context.get('questions_asked'):
            recent_questions = structured_context['questions_asked'][-3:]
            parts.append(f"Recent questions: {' | '.join(recent_questions)}")

        # Add entities
        entities = structured_context.get('entities', {})
        entity_parts = []
        for entity_type, values in entities.items():
            if values:
                entity_parts.append(f"{entity_type}: {', '.join(values)}")

        if entity_parts:
            parts.append(f"Referenced: {' | '.join(entity_parts)}")

        # Add resolved context if references were detected
        if structured_context.get('references', {}).get('has_references'):
            parts.append(f"Context resolution: {structured_context.get('resolved_context', '')}")

        return "\n\n".join(parts)

    def get_relevant_context_for_query(
        self,
        messages: List[Dict],
        current_query: str,
        query_intent: str = None
    ) -> Dict:
        """Get most relevant context based on query characteristics"""

        # Build full structured context
        structured_context = self.build_structured_context(messages, current_query)

        # For follow-up questions, prioritize recent messages
        if structured_context['references']['has_references']:
            relevant_messages = messages[-5:] if len(messages) > 5 else messages
        # For new topics, include broader context
        elif query_intent in ['comparison', 'analytical']:
            relevant_messages = self.get_sliding_window_context(messages, current_query)
        # For simple lookups, minimal context needed
        elif query_intent in ['factual_lookup', 'specific_value']:
            relevant_messages = messages[-3:] if len(messages) > 3 else messages
        else:
            relevant_messages = messages[-7:] if len(messages) > 7 else messages

        return {
            **structured_context,
            'relevant_messages': relevant_messages,
            'context_string': self.prepare_context_for_llm(structured_context)
        }

    def enhance_query_with_context(
        self,
        query: str,
        context: Dict
    ) -> str:
        """Enhance query with resolved context"""
        if not context.get('references', {}).get('has_references'):
            return query

        enhanced_query = context.get('resolved_context', query)

        # Add entity context if helpful
        entities = context.get('entities', {})
        entity_hints = []

        if entities.get('documents'):
            entity_hints.append(f"Documents: {', '.join(entities['documents'][:2])}")

        if entity_hints:
            enhanced_query = f"{enhanced_query} [Context: {' | '.join(entity_hints)}]"

        return enhanced_query
