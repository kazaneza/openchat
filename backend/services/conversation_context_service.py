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
            'dates': [],
            'mentioned_entities': []  # Entities mentioned in responses (like "IT policies")
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
            
            # Extract entities from assistant responses (e.g., "26 IT policies", "IT policies")
            # Pattern: number + capitalized phrase or just capitalized phrase
            if msg.get('role') == 'assistant':
                # Pattern: "You have X Y" or "There are X Y" or just "X Y"
                entity_patterns = [
                    r'(?:You have|There (?:are|is)|We have|I have)\s+(\d+)\s+((?:[A-Z]{2,}|[A-Z][a-z]+)(?:\s+[a-z]+)*)',
                    r'(\d+)\s+((?:[A-Z]{2,}|[A-Z][a-z]+)(?:\s+[a-z]+)*)\s+(?:policies?|documents?|files?|items?|things?)',
                    r'\b((?:[A-Z]{2,}|[A-Z][a-z]+)(?:\s+[a-z]+)+)\s+(?:policies?|documents?|procedures?|guidelines?)',
                    r'\b((?:[A-Z]{2,}|[A-Z][a-z]+)(?:\s+[a-z]+)+)\s+at\s+',
                    r'\b((?:[A-Z]{2,}|[A-Z][a-z]+)(?:\s+[a-z]+)+)\s+help',
                ]
                for pattern in entity_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        if isinstance(match, tuple):
                            # Combine number and entity if both present, or just take the entity part
                            entity = ' '.join([m for m in match if m and not m.isdigit()])
                            if not entity and len(match) > 1:
                                entity = match[1] if not match[1].isdigit() else match[0]
                            if entity:
                                entities['mentioned_entities'].append(entity)
                        else:
                            entities['mentioned_entities'].append(match)
                
                # Also extract capitalized phrases that might be entities (including all caps like "IT")
                capitalized_phrases = re.findall(r'\b((?:[A-Z]{2,}|[A-Z][a-z]+)(?:\s+(?:[A-Z]{2,}|[A-Z][a-z]+))+)', content)
                for phrase in capitalized_phrases[:5]:  # Increase limit
                    if len(phrase.split()) <= 4:  # Reasonable entity length
                        entities['mentioned_entities'].append(phrase)

        # Deduplicate and prioritize recent entities
        for key in entities:
            # Reverse to keep most recent first, then deduplicate
            entities[key] = list(dict.fromkeys(reversed(entities[key])))[:5]

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

        # Extract key entities from recent assistant responses
        extracted_entities = []
        for msg in reversed(recent_context):
            if msg.get('role') == 'assistant':
                content = msg.get('content', '')
                # Extract capitalized phrases and numbers (likely entities)
                import re
                
                # First, extract "IT policies" type patterns (all caps + lowercase)
                it_policies_pattern = re.findall(r'\b([A-Z]{2,}\s+[a-z]+(?:\s+[a-z]+)*)\b', content)
                if it_policies_pattern:
                    extracted_entities.extend(it_policies_pattern[:3])
                
                # Find capitalized phrases (potential entities)
                capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', content)
                # Find numbers followed by nouns (e.g., "26 IT policies") - handle both "IT" and regular caps
                number_entities = re.findall(r'\b\d+\s+((?:[A-Z]{2,}|[A-Z][a-z]+)(?:\s+[a-z]+)*)\b', content)
                # Find quoted phrases
                quoted = re.findall(r'["\']([^"\']+)["\']', content)
                
                if capitalized:
                    extracted_entities.extend(capitalized[:3])  # Limit to top 3
                if number_entities:
                    extracted_entities.extend(number_entities[:2])
                if quoted:
                    extracted_entities.extend(quoted[:2])
                
                # Also extract the main subject from the response
                # Look for patterns like "IT policies at", "IT policies help", etc.
                subject_patterns = [
                    r'\b((?:[A-Z]{2,}|[A-Z][a-z]+)(?:\s+[a-z]+)+)\s+(?:policies?|documents?|procedures?|guidelines?)\s+(?:at|help|establish)',
                    r'You have (\d+)\s+((?:[A-Z]{2,}|[A-Z][a-z]+)(?:\s+[a-z]+)*)',
                    r'There (?:are|is) (\d+)\s+((?:[A-Z]{2,}|[A-Z][a-z]+)(?:\s+[a-z]+)*)',
                    r'(\d+)\s+((?:[A-Z]{2,}|[A-Z][a-z]+)(?:\s+[a-z]+)*)',
                ]
                for pattern in subject_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        for match in matches[:1]:  # Take first match
                            if isinstance(match, tuple):
                                # Take the entity part (skip numbers)
                                entity = ' '.join([m for m in match if m and not m.isdigit()])
                            else:
                                entity = match
                            if entity and entity not in extracted_entities:
                                extracted_entities.append(entity)
                
                # Break after finding entities from most recent assistant response
                if extracted_entities:
                    break

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

        # Resolve pronouns with extracted entities or document references
        if references.get('pronouns') or references.get('demonstratives'):
            replacement_entity = None
            
            # First try mentioned entities from conversation history
            if entities.get('mentioned_entities'):
                # For "they/them/their", prefer plural entities
                if any(pronoun in query_lower for pronoun in ['they', 'them', 'their', 'these', 'those']):
                    # Look for plural-sounding entities
                    for entity in entities['mentioned_entities']:
                        if any(word.endswith('s') for word in entity.split()):
                            replacement_entity = entity
                            break
                    # If no plural found, use the most recent entity
                    if not replacement_entity:
                        replacement_entity = entities['mentioned_entities'][0]
                else:
                    # For "it/this/that", use the most recent entity
                    replacement_entity = entities['mentioned_entities'][0]
            
            # Fallback to extracted entities from current resolution
            if not replacement_entity and extracted_entities:
                # For "they/them/their", prefer plural entities
                if any(pronoun in query_lower for pronoun in ['they', 'them', 'their', 'these', 'those']):
                    # Look for plural-sounding entities or entities with numbers
                    for entity in extracted_entities:
                        if any(word.endswith('s') for word in entity.split()) or any(char.isdigit() for char in entity):
                            replacement_entity = entity
                            break
                    # If no plural found, use the most recent entity
                    if not replacement_entity:
                        replacement_entity = extracted_entities[0]
                else:
                    # For "it/this/that", use the most recent entity
                    replacement_entity = extracted_entities[0]
            
            # Fallback to document references
            if not replacement_entity and entities.get('documents'):
                replacement_entity = entities['documents'][-1]
            
            if replacement_entity:
                # Replace pronouns in the query
                import re
                # Replace "they" with the entity
                resolved_query = re.sub(
                    r'\b(they|them|their|it|this|that|these|those)\b',
                    replacement_entity,
                    current_query,
                    count=1,  # Only replace first occurrence
                    flags=re.IGNORECASE
                )
                # Add context prefix for clarity
                resolved_query = f"[Referring to: {replacement_entity}] {resolved_query}"

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
