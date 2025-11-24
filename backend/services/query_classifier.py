"""
Intelligent Query Classification Service
Distinguishes between general questions and document-specific queries
"""
from typing import Dict, List
import re

class QueryClassifier:
    def __init__(self):
        # Greeting patterns - always general (including Kinyarwanda and other languages)
        self.greeting_patterns = [
            r'^(hi|hello|hey|greetings|good morning|good afternoon|good evening)',
            r'^(hi|hello|hey|greetings|good morning|good afternoon|good evening)\s+',
            r'^how are you',
            r'^what can you do',
            r'^who are you',
            # Kinyarwanda greetings
            r'^(mwiriwe|mwaramutse|amakuru|bite)',
            # French greetings
            r'^(bonjour|salut|bonsoir|ça va)',
            # Spanish greetings
            r'^(hola|buenos días|buenas tardes)'
        ]
        
        # General question patterns (not document-specific)
        self.general_patterns = [
            r'\b(what is|what are|define|explain)\s+(?:a|an|the)?\s*[^?]+\?',
            r'\bhow (?:do|does|can|should|would|will)\s+',
            r'\bwhy\s+',
            r'\bwhen\s+(?:is|are|do|does|can|should)',
            r'\bwhere\s+(?:is|are|do|does|can)',
            r'^tell me about',
            r'^can you help',
            r'^help me'
        ]
        
        # Document-specific patterns
        self.document_patterns = [
            r'\b(?:in|from|according to|based on|per|as per)\s+(?:the|this|that|these|those)?\s*(?:document|file|pdf|upload|uploaded)',
            r'\b(?:document|file|pdf|upload)\s+(?:says|states|mentions|contains|includes)',
            r'\b(?:find|search|look for|extract|summarize|list)\s+(?:in|from|within)',
            r'\b(?:what|which|how many)\s+(?:document|file|policy|policies)',
            r'\b(?:show|display|list|enumerate)\s+(?:all|the|all the)\s*(?:document|file|policy)',
            r'\b(?:document|file|policy|policies)\s+(?:about|regarding|concerning)',
            r'\b(?:according to|based on|per)\s+[A-Z][a-z]+',  # Capitalized entity (likely document name)
        ]
        
        # Strong document indicators
        self.strong_document_indicators = [
            'document', 'file', 'pdf', 'upload', 'uploaded', 'policy', 'policies',
            'in the document', 'from the file', 'according to', 'based on the document'
        ]
    
    def classify(
        self,
        query: str,
        has_documents: bool = True,
        conversation_history: List[Dict] = None,
        language: str = "en"
    ) -> Dict:
        """
        Classify query as general or document-specific
        Returns: {
            'type': 'general' | 'document' | 'mixed',
            'confidence': float,
            'reason': str
        }
        """
        query_lower = query.lower().strip()
        conversation_history = conversation_history or []
        
        # 1) Greetings: always general
        if self._is_greeting(query_lower):
            return {
                'type': 'general',
                'confidence': 0.95,
                'reason': 'Greeting detected'
            }
        
        # 2) If no documents at all, it's general
        if not has_documents:
            return {
                'type': 'general',
                'confidence': 0.9,
                'reason': 'No documents available'
            }
        
        # 3) LANGUAGE-BASED SHORTCUT
        # If language is not English, default to GENERAL unless we clearly see document indicators.
        # This avoids sending Kinyarwanda/French questions straight to document mode.
        non_english = language and language != "en"
        
        # Check for strong doc indicators & patterns (English-based)
        has_strong_doc_indicator = any(
            indicator in query_lower for indicator in self.strong_document_indicators
        )
        
        doc_score = sum(
            1 for pattern in self.document_patterns
            if re.search(pattern, query_lower, re.IGNORECASE)
        )
        
        general_score = sum(
            1 for pattern in self.general_patterns
            if re.search(pattern, query_lower, re.IGNORECASE)
        )
        
        is_follow_up = self._is_follow_up(query_lower, conversation_history)
        
        # 3.a Non-English queries
        if non_english:
            # Only treat as document if the user very explicitly references docs (rare in Kinyarwanda)
            if has_strong_doc_indicator or doc_score >= 2:
                return {
                    'type': 'document',
                    'confidence': 0.7,
                    'reason': f'Non-English ({language}) but strong document indicators found'
                }
            # Otherwise default to general
            return {
                'type': 'general',
                'confidence': 0.85,
                'reason': f'Non-English query ({language}), defaulting to general'
            }
        
        # 4) Normal English logic below
        if has_strong_doc_indicator or doc_score >= 2:
            return {
                'type': 'document',
                'confidence': 0.9,
                'reason': 'Strong document indicators found'
            }
        elif doc_score > general_score and doc_score > 0:
            return {
                'type': 'document',
                'confidence': 0.7,
                'reason': 'Document patterns detected'
            }
        elif is_follow_up and self._might_reference_documents(query_lower, conversation_history):
            return {
                'type': 'document',
                'confidence': 0.6,
                'reason': 'Follow-up question likely referencing documents'
            }
        elif general_score > 0 and doc_score == 0:
            return {
                'type': 'general',
                'confidence': 0.8,
                'reason': 'General question patterns detected'
            }
        else:
            # DEFAULT for English: your old behavior
            return {
                'type': 'document',
                'confidence': 0.5,
                'reason': 'Default: attempting document search first'
            }
    
    def _is_greeting(self, query: str) -> bool:
        """Check if query is a greeting"""
        return any(re.match(pattern, query, re.IGNORECASE) for pattern in self.greeting_patterns)
    
    def _is_follow_up(self, query: str, conversation_history: List[Dict]) -> bool:
        """Check if query is a follow-up question"""
        if not conversation_history:
            return False
        
        # Check for pronouns that indicate reference to previous context
        pronouns = ['it', 'they', 'them', 'this', 'that', 'these', 'those', 'the document', 'the file']
        has_pronoun = any(pronoun in query.lower() for pronoun in pronouns)
        
        # Check for continuation words
        continuation_words = ['also', 'additionally', 'what about', 'how about', 'tell me more']
        has_continuation = any(word in query.lower() for word in continuation_words)
        
        # Short queries are often follow-ups
        is_short = len(query.split()) <= 5
        
        return has_pronoun or has_continuation or (is_short and len(conversation_history) > 0)
    
    def _might_reference_documents(self, query: str, conversation_history: List[Dict]) -> bool:
        """Check if follow-up query might reference documents from conversation"""
        if not conversation_history:
            return False
        
        # Check recent messages for document mentions
        recent_messages = conversation_history[-3:]
        for msg in recent_messages:
            content = msg.get('content', '').lower()
            if any(indicator in content for indicator in self.strong_document_indicators):
                return True
        
        return False

