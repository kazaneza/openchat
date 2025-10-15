from typing import List, Dict, Optional, Tuple
import re
from datetime import datetime

class QueryUnderstandingService:
    def __init__(self):
        # Intent patterns
        self.intent_patterns = {
            'factual_lookup': [
                r'\bwhat is\b', r'\bwhat are\b', r'\bwho is\b', r'\bwhere is\b',
                r'\bwhen is\b', r'\bdefine\b', r'\bdefinition\b'
            ],
            'procedural': [
                r'\bhow to\b', r'\bhow do\b', r'\bhow can\b', r'\bsteps\b',
                r'\bprocess\b', r'\bprocedure\b', r'\binstructions\b'
            ],
            'comparison': [
                r'\bcompare\b', r'\bversus\b', r'\bvs\b', r'\bdifference\b',
                r'\bbetter\b', r'\bworse\b', r'\bcontrast\b', r'\balternative\b'
            ],
            'analytical': [
                r'\bwhy\b', r'\bexplain\b', r'\breason\b', r'\bcause\b',
                r'\bimpact\b', r'\beffect\b', r'\banalyz\b', r'\bevaluat\b'
            ],
            'summarization': [
                r'\bsummariz\b', r'\boverview\b', r'\bmain points\b',
                r'\bkey\b.*\bpoints\b', r'\bhighlights\b', r'\bin brief\b'
            ],
            'list_enumeration': [
                r'\blist\b', r'\ball\b.*\b(documents|files|items)\b',
                r'\bshow me\b.*\b(documents|files)\b', r'\bwhat documents\b'
            ],
            'specific_value': [
                r'\bprice\b', r'\bcost\b', r'\bdate\b', r'\bnumber\b',
                r'\bversion\b', r'\bsize\b', r'\bquantity\b'
            ],
            'opinion_recommendation': [
                r'\bshould i\b', r'\brecommend\b', r'\bsuggestion\b',
                r'\badvice\b', r'\bbest\b', r'\btop\b'
            ]
        }

        # Multi-document indicators
        self.multi_doc_indicators = [
            r'\ball documents\b', r'\bevery document\b', r'\bacross documents\b',
            r'\bin all\b.*\b(files|pdfs)\b', r'\bthroughout\b',
            r'\bbetween\b.*\band\b', r'\bcompare\b', r'\bacross\b'
        ]

        # Follow-up indicators
        self.follow_up_indicators = [
            r'\balso\b', r'\badditionally\b', r'\bmoreover\b', r'\bfurthermore\b',
            r'\band\b.*\babout\b', r'\bwhat about\b', r'\bhow about\b',
            r'\btell me more\b', r'\bcan you\b.*\bmore\b'
        ]

        # Ambiguity indicators
        self.ambiguity_patterns = [
            r'\bit\b', r'\bthat\b', r'\bthis\b', r'\bthey\b', r'\bthem\b',
            r'\bthose\b', r'\bthese\b'
        ]

        # Clarification needed indicators
        self.vague_terms = [
            r'\bsomething\b', r'\bsomewhere\b', r'\bsomeone\b',
            r'\bthing\b(?!\s+is)', r'\bstuff\b', r'\bitems\b'
        ]

    def classify_intent(self, query: str) -> Dict:
        """Classify query intent"""
        query_lower = query.lower()
        intents = []
        confidence_scores = {}

        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    if intent not in intents:
                        intents.append(intent)
                        confidence_scores[intent] = 0
                    confidence_scores[intent] += 1

        # Determine primary intent
        if intents:
            primary_intent = max(confidence_scores, key=confidence_scores.get)
            confidence = min(confidence_scores[primary_intent] / 3, 1.0)
        else:
            primary_intent = 'general_inquiry'
            confidence = 0.5
            intents = ['general_inquiry']

        return {
            'primary_intent': primary_intent,
            'all_intents': intents,
            'confidence': confidence,
            'intent_scores': confidence_scores
        }

    def detect_multi_document_query(self, query: str, available_documents: int) -> Dict:
        """Detect if query spans multiple documents"""
        query_lower = query.lower()

        # Check for explicit multi-document indicators
        explicit_multi = any(
            re.search(pattern, query_lower)
            for pattern in self.multi_doc_indicators
        )

        # Check for comparison between documents
        is_comparison = 'compare' in query_lower or 'versus' in query_lower

        # Check for document name mentions
        doc_mentions = len(re.findall(r'\b(?:document|file|pdf)\b', query_lower))

        # Detect if multiple specific documents are referenced
        has_multiple_refs = doc_mentions > 1 or ' and ' in query_lower

        # Determine if query requires multiple documents
        requires_multiple = (
            explicit_multi or
            (is_comparison and available_documents > 1) or
            has_multiple_refs
        )

        return {
            'is_multi_document': requires_multiple,
            'explicit_multi': explicit_multi,
            'is_comparison': is_comparison,
            'confidence': 0.9 if explicit_multi else (0.7 if is_comparison else 0.5)
        }

    def detect_follow_up(self, current_query: str, conversation_history: List[Dict]) -> Dict:
        """Detect if query is a follow-up question"""
        if not conversation_history:
            return {
                'is_follow_up': False,
                'confidence': 0.0,
                'reference_type': None
            }

        query_lower = current_query.lower()

        # Check for explicit follow-up indicators
        has_follow_up_words = any(
            re.search(pattern, query_lower)
            for pattern in self.follow_up_indicators
        )

        # Check for pronouns (indicating reference to previous context)
        has_pronouns = any(
            re.search(pattern, query_lower)
            for pattern in self.ambiguity_patterns
        )

        # Check if query is short (likely relies on context)
        is_short = len(current_query.split()) < 5

        # Check for incomplete question structure
        question_words = ['what', 'when', 'where', 'who', 'why', 'how', 'which']
        starts_with_question = any(query_lower.startswith(qw) for qw in question_words)
        is_incomplete = not starts_with_question and '?' in current_query

        # Determine if follow-up
        is_follow_up = (
            has_follow_up_words or
            (has_pronouns and is_short) or
            is_incomplete
        )

        # Determine reference type
        reference_type = None
        if is_follow_up:
            if has_pronouns:
                reference_type = 'pronoun_reference'
            elif has_follow_up_words:
                reference_type = 'explicit_continuation'
            elif is_incomplete:
                reference_type = 'implicit_continuation'

        # Calculate confidence
        confidence = 0.0
        if has_follow_up_words:
            confidence = 0.9
        elif has_pronouns and is_short:
            confidence = 0.8
        elif is_incomplete:
            confidence = 0.6

        return {
            'is_follow_up': is_follow_up,
            'confidence': confidence,
            'reference_type': reference_type,
            'has_pronouns': has_pronouns,
            'recent_context': conversation_history[-3:] if len(conversation_history) >= 3 else conversation_history
        }

    def detect_ambiguity(self, query: str, conversation_history: List[Dict]) -> Dict:
        """Detect ambiguous or unclear queries"""
        query_lower = query.lower()
        ambiguities = []
        needs_clarification = False

        # Check for vague terms
        vague_found = []
        for pattern in self.vague_terms:
            if re.search(pattern, query_lower):
                vague_found.append(re.search(pattern, query_lower).group())

        if vague_found:
            ambiguities.append({
                'type': 'vague_terms',
                'terms': vague_found,
                'severity': 'medium'
            })

        # Check for unclear pronouns without recent context
        has_pronouns = any(re.search(pattern, query_lower) for pattern in self.ambiguity_patterns)
        if has_pronouns and len(conversation_history) < 2:
            ambiguities.append({
                'type': 'unclear_reference',
                'severity': 'high'
            })
            needs_clarification = True

        # Check for very short queries
        word_count = len(query.split())
        if word_count < 3:
            ambiguities.append({
                'type': 'too_brief',
                'word_count': word_count,
                'severity': 'medium'
            })

        # Check for multiple possible interpretations
        question_marks = query.count('?')
        if question_marks > 1:
            ambiguities.append({
                'type': 'multiple_questions',
                'count': question_marks,
                'severity': 'low'
            })

        # Check for contradictory terms
        has_and = ' and ' in query_lower
        has_or = ' or ' in query_lower
        if has_and and has_or:
            ambiguities.append({
                'type': 'complex_logic',
                'severity': 'medium'
            })

        needs_clarification = (
            len(ambiguities) > 0 and
            any(a['severity'] == 'high' for a in ambiguities)
        )

        return {
            'is_ambiguous': len(ambiguities) > 0,
            'needs_clarification': needs_clarification,
            'ambiguities': ambiguities,
            'severity': 'high' if needs_clarification else ('medium' if ambiguities else 'low')
        }

    def generate_clarification_prompt(self, ambiguity_info: Dict, intent_info: Dict, query: str) -> Optional[str]:
        """Generate clarification question for ambiguous queries"""
        if not ambiguity_info.get('needs_clarification'):
            return None

        ambiguities = ambiguity_info.get('ambiguities', [])

        for ambiguity in ambiguities:
            if ambiguity['type'] == 'unclear_reference':
                return "I notice you're referring to something, but I'm not sure what you're asking about. Could you please provide more details or rephrase your question?"

            elif ambiguity['type'] == 'vague_terms':
                terms = ', '.join(ambiguity['terms'])
                return f"I'd like to help, but your question contains some vague terms ({terms}). Could you be more specific about what you're looking for?"

            elif ambiguity['type'] == 'too_brief':
                return "Your question is quite brief. Could you provide more context or details so I can give you a better answer?"

        return "I want to make sure I understand your question correctly. Could you please provide more details or rephrase it?"

    def resolve_follow_up_context(self, current_query: str, conversation_history: List[Dict]) -> str:
        """Resolve follow-up question by adding context from history"""
        if not conversation_history:
            return current_query

        # Get recent messages
        recent_messages = conversation_history[-3:]

        # Build context from recent conversation
        context_parts = []
        for msg in recent_messages:
            if msg.get('role') == 'user':
                context_parts.append(f"Previously asked: {msg.get('content', '')}")
            elif msg.get('role') == 'assistant':
                # Get first sentence of response
                response = msg.get('content', '')
                first_sentence = response.split('.')[0] if response else ''
                if first_sentence:
                    context_parts.append(f"Previously answered: {first_sentence}")

        context_string = " | ".join(context_parts)

        # Create enhanced query
        enhanced_query = f"[Context: {context_string}] | Current question: {current_query}"

        return enhanced_query

    def extract_entities(self, query: str) -> Dict:
        """Extract named entities and key terms from query"""
        # Extract numbers
        numbers = re.findall(r'\b\d+(?:\.\d+)?\b', query)

        # Extract potential document names (capitalized words or quoted text)
        potential_docs = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
        quoted_text = re.findall(r'["\']([^"\']+)["\']', query)

        # Extract dates
        dates = re.findall(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b', query)

        # Extract technical terms (words with special chars or camelCase)
        technical_terms = re.findall(r'\b[a-z]+[A-Z][a-zA-Z]*\b|\b\w+[-_]\w+\b', query)

        return {
            'numbers': numbers,
            'potential_document_names': potential_docs,
            'quoted_phrases': quoted_text,
            'dates': dates,
            'technical_terms': technical_terms
        }

    def analyze_query(
        self,
        query: str,
        conversation_history: List[Dict] = None,
        available_documents: int = 0
    ) -> Dict:
        """Comprehensive query analysis"""
        conversation_history = conversation_history or []

        # Classify intent
        intent_info = self.classify_intent(query)

        # Detect multi-document query
        multi_doc_info = self.detect_multi_document_query(query, available_documents)

        # Detect follow-up
        follow_up_info = self.detect_follow_up(query, conversation_history)

        # Detect ambiguity
        ambiguity_info = self.detect_ambiguity(query, conversation_history)

        # Extract entities
        entities = self.extract_entities(query)

        # Generate clarification if needed
        clarification_prompt = self.generate_clarification_prompt(
            ambiguity_info,
            intent_info,
            query
        )

        # Resolve follow-up context
        enhanced_query = query
        if follow_up_info.get('is_follow_up') and not ambiguity_info.get('needs_clarification'):
            enhanced_query = self.resolve_follow_up_context(query, conversation_history)

        return {
            'original_query': query,
            'enhanced_query': enhanced_query,
            'intent': intent_info,
            'multi_document': multi_doc_info,
            'follow_up': follow_up_info,
            'ambiguity': ambiguity_info,
            'entities': entities,
            'needs_clarification': ambiguity_info.get('needs_clarification', False),
            'clarification_prompt': clarification_prompt,
            'timestamp': datetime.now().isoformat()
        }

    def get_query_metadata(self, analysis: Dict) -> Dict:
        """Extract metadata for logging and analytics"""
        return {
            'primary_intent': analysis['intent']['primary_intent'],
            'intent_confidence': analysis['intent']['confidence'],
            'is_multi_document': analysis['multi_document']['is_multi_document'],
            'is_follow_up': analysis['follow_up']['is_follow_up'],
            'is_ambiguous': analysis['ambiguity']['is_ambiguous'],
            'needs_clarification': analysis['needs_clarification'],
            'has_entities': any(analysis['entities'].values()),
            'query_length': len(analysis['original_query'].split())
        }
