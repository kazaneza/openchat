from typing import Dict, Optional

class ResponseLengthService:
    def __init__(self):
        self.query_type_tokens = {
            'yes_no': 50,
            'simple_fact': 100,
            'definition': 150,
            'how_to': 300,
            'explanation': 250,
            'comparison': 350,
            'troubleshooting': 400,
            'comprehensive': 500
        }

    def determine_appropriate_length(self, query: str, query_analysis: Dict) -> int:
        """
        Determine appropriate response length based on query type
        Returns max_tokens for response generation
        """
        query_lower = query.lower()

        # Yes/no questions
        if self._is_yes_no_question(query_lower):
            return self.query_type_tokens['yes_no']

        # Simple fact questions
        if self._is_simple_fact_question(query_lower):
            return self.query_type_tokens['simple_fact']

        # Definition questions
        if self._is_definition_question(query_lower):
            return self.query_type_tokens['definition']

        # How-to questions
        if self._is_how_to_question(query_lower):
            return self.query_type_tokens['how_to']

        # Comparison questions
        if self._is_comparison_question(query_lower):
            return self.query_type_tokens['comparison']

        # Troubleshooting questions
        if self._is_troubleshooting_question(query_lower):
            return self.query_type_tokens['troubleshooting']

        # Use query analysis if available
        primary_intent = query_analysis.get('intent', {}).get('primary_intent', '')

        if primary_intent in ['specific_fact_inquiry', 'clarification']:
            return self.query_type_tokens['simple_fact']
        elif primary_intent in ['how_to_inquiry', 'procedural_inquiry']:
            return self.query_type_tokens['how_to']
        elif primary_intent in ['general_inquiry', 'exploratory']:
            return self.query_type_tokens['explanation']

        # Default to moderate length
        return self.query_type_tokens['explanation']

    def _is_yes_no_question(self, query: str) -> bool:
        """Check if query is a yes/no question"""
        yes_no_starters = [
            'is ', 'are ', 'am ', 'was ', 'were ', 'do ', 'does ', 'did ',
            'can ', 'could ', 'will ', 'would ', 'should ', 'has ', 'have ',
            'may ', 'might '
        ]
        return any(query.startswith(starter) for starter in yes_no_starters)

    def _is_simple_fact_question(self, query: str) -> bool:
        """Check if query is asking for a simple fact"""
        simple_patterns = [
            'what is the ', 'what are the ', 'when is ', 'when does ',
            'where is ', 'who is ', 'which is ', 'how much ', 'how many '
        ]
        return any(pattern in query for pattern in simple_patterns)

    def _is_definition_question(self, query: str) -> bool:
        """Check if query is asking for a definition"""
        definition_patterns = ['what does', 'define', 'meaning of', 'what is']
        return any(pattern in query for pattern in definition_patterns)

    def _is_how_to_question(self, query: str) -> bool:
        """Check if query is a how-to question"""
        how_to_patterns = ['how to', 'how do i', 'how can i', 'steps to', 'guide to']
        return any(pattern in query for pattern in how_to_patterns)

    def _is_comparison_question(self, query: str) -> bool:
        """Check if query is asking for comparison"""
        comparison_words = [
            'compare', 'difference', 'versus', 'vs', 'better than',
            'similar to', 'contrast'
        ]
        return any(word in query for word in comparison_words)

    def _is_troubleshooting_question(self, query: str) -> bool:
        """Check if query is troubleshooting-related"""
        troubleshooting_words = [
            'not working', 'broken', 'error', 'problem', 'issue', 'fix',
            'troubleshoot', 'resolve', "doesn't work", "won't work"
        ]
        return any(word in query for word in troubleshooting_words)

    def create_length_instruction(self, max_tokens: int) -> str:
        """Create instruction for response length"""
        if max_tokens <= 100:
            return "\n\nIMPORTANT: Keep your response brief and direct - maximum 2-3 sentences. Answer the specific question asked without elaboration."
        elif max_tokens <= 200:
            return "\n\nIMPORTANT: Keep your response concise - maximum 4-5 sentences. Be specific and to the point."
        elif max_tokens <= 300:
            return "\n\nIMPORTANT: Provide a focused response in 1-2 short paragraphs. Include only essential information."
        else:
            return "\n\nIMPORTANT: Provide a clear, well-structured response. Be thorough but avoid unnecessary verbosity."
