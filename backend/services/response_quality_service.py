from typing import List, Dict, Optional, Tuple
import re
from datetime import datetime

class ResponseQualityService:
    def __init__(self):
        self.confidence_thresholds = {
            'high': 0.80,
            'medium': 0.60,
            'low': 0.40
        }

    def validate_response(
        self,
        response: str,
        sources: List[Dict],
        query: str,
        query_intent: str
    ) -> Dict:
        """Validate response quality and accuracy"""

        validation = {
            'is_valid': True,
            'issues': [],
            'warnings': [],
            'quality_score': 1.0
        }

        # Check for empty or too short response
        if not response or len(response.strip()) < 10:
            validation['is_valid'] = False
            validation['issues'].append('Response too short or empty')
            validation['quality_score'] *= 0.1
            return validation

        # Check for hallucination indicators
        hallucination_check = self._check_hallucinations(response, sources)
        if hallucination_check['has_hallucinations']:
            validation['warnings'].extend(hallucination_check['warnings'])
            validation['quality_score'] *= 0.8

        # Check source grounding
        grounding_check = self._check_source_grounding(response, sources)
        validation['grounding_score'] = grounding_check['score']
        validation['quality_score'] *= grounding_check['score']

        if grounding_check['score'] < 0.3:
            validation['warnings'].append('Response may not be well-grounded in sources')

        # Check for contradictions
        contradiction_check = self._check_contradictions(response, sources)
        if contradiction_check['has_contradictions']:
            validation['warnings'].extend(contradiction_check['warnings'])
            validation['quality_score'] *= 0.7

        # Check completeness
        completeness = self._check_completeness(response, query, query_intent)
        validation['completeness_score'] = completeness['score']
        validation['quality_score'] *= completeness['score']

        if completeness['score'] < 0.5:
            validation['warnings'].append('Response may be incomplete')

        # Check for uncertainty expressions
        uncertainty = self._detect_uncertainty(response)
        validation['uncertainty_level'] = uncertainty['level']
        if uncertainty['level'] == 'high':
            validation['quality_score'] *= 0.9

        return validation

    def _check_hallucinations(self, response: str, sources: List[Dict]) -> Dict:
        """Check for potential hallucinations"""
        warnings = []
        has_hallucinations = False

        # Check for specific values not in sources
        numbers = re.findall(r'\b\d+(?:\.\d+)?(?:\s*(?:GB|MB|KB|%|dollars?|\$|€))\b', response, re.IGNORECASE)

        if numbers:
            source_text = ' '.join([s.get('chunk_preview', '') for s in sources])
            for number in numbers:
                if number not in source_text:
                    warnings.append(f'Numeric value "{number}" not found in sources')
                    has_hallucinations = True

        # Check for hedge phrases that might indicate uncertainty
        hedge_phrases = [
            'i think', 'i believe', 'it seems', 'it appears',
            'probably', 'possibly', 'might be', 'could be',
            'it\'s likely', 'perhaps'
        ]

        response_lower = response.lower()
        for phrase in hedge_phrases:
            if phrase in response_lower:
                warnings.append(f'Contains uncertain language: "{phrase}"')

        return {
            'has_hallucinations': has_hallucinations,
            'warnings': warnings
        }

    def _check_source_grounding(self, response: str, sources: List[Dict]) -> Dict:
        """Check how well response is grounded in sources"""
        if not sources:
            return {'score': 0.0, 'matches': []}

        # Extract key phrases from response
        response_words = set(response.lower().split())

        # Calculate overlap with sources
        total_overlap = 0
        matches = []

        for source in sources:
            source_text = source.get('chunk_preview', '').lower()
            source_words = set(source_text.split())

            overlap = len(response_words.intersection(source_words))
            overlap_ratio = overlap / len(response_words) if response_words else 0

            if overlap_ratio > 0.1:
                matches.append({
                    'document': source.get('document_name', ''),
                    'overlap_ratio': overlap_ratio
                })

            total_overlap += overlap

        # Calculate grounding score
        max_possible = len(response_words) * len(sources)
        grounding_score = min(total_overlap / len(response_words), 1.0) if response_words else 0

        return {
            'score': grounding_score,
            'matches': matches
        }

    def _check_contradictions(self, response: str, sources: List[Dict]) -> Dict:
        """Check for contradictions with source material"""
        warnings = []
        has_contradictions = False

        # Look for negations in response
        negation_patterns = [
            r'\bnot\b', r'\bno\b', r'\bnever\b', r'\bdoesn\'t\b',
            r'\bdon\'t\b', r'\bisn\'t\b', r'\baren\'t\b', r'\bwasn\'t\b'
        ]

        response_lower = response.lower()
        has_negations = any(re.search(pattern, response_lower) for pattern in negation_patterns)

        if has_negations and sources:
            # Check if source material supports the negation
            source_text = ' '.join([s.get('chunk_preview', '') for s in sources]).lower()

            # If response has negations but source doesn't, flag potential contradiction
            source_has_negations = any(re.search(pattern, source_text) for pattern in negation_patterns)

            if not source_has_negations:
                warnings.append('Response contains negations not clearly supported by sources')
                has_contradictions = True

        return {
            'has_contradictions': has_contradictions,
            'warnings': warnings
        }

    def _check_completeness(self, response: str, query: str, query_intent: str) -> Dict:
        """Check if response adequately addresses the query"""
        score = 1.0

        # Intent-specific completeness checks
        if query_intent == 'comparison':
            # Should mention both entities
            if 'compare' in query.lower() or 'versus' in query.lower():
                entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
                if len(entities) >= 2:
                    mentions = sum(1 for entity in entities[:2] if entity in response)
                    score = mentions / 2.0

        elif query_intent == 'list_enumeration':
            # Should have multiple items
            list_indicators = len(re.findall(r'\b\d+[\.\)]\s', response))
            bullet_points = len(re.findall(r'\n\s*[-*•]\s', response))

            if list_indicators + bullet_points < 2:
                score *= 0.7

        elif query_intent == 'procedural':
            # Should have steps
            steps = len(re.findall(r'\b(?:step|first|second|third|then|next|finally)\b', response.lower()))
            if steps < 2:
                score *= 0.8

        # Check response length appropriateness
        query_words = len(query.split())
        response_words = len(response.split())

        # Very short queries might expect longer responses
        if query_words < 10 and response_words < 30:
            score *= 0.9

        return {'score': score}

    def _detect_uncertainty(self, response: str) -> Dict:
        """Detect uncertainty level in response"""
        uncertainty_indicators = {
            'high': ['not sure', 'uncertain', 'unclear', 'cannot determine', 'insufficient information'],
            'medium': ['may', 'might', 'could', 'possibly', 'perhaps', 'it seems'],
            'low': ['likely', 'probably', 'appears to']
        }

        response_lower = response.lower()

        for level, indicators in uncertainty_indicators.items():
            for indicator in indicators:
                if indicator in response_lower:
                    return {'level': level, 'indicator': indicator}

        return {'level': 'none', 'indicator': None}

    def fact_check_response(
        self,
        response: str,
        sources: List[Dict],
        query: str
    ) -> Dict:
        """Fact-check response against source documents"""

        fact_check = {
            'verified_claims': [],
            'unverified_claims': [],
            'confidence': 1.0,
            'issues': []
        }

        # Extract claims (sentences with factual content)
        claims = self._extract_claims(response)

        # Check each claim against sources
        source_text_combined = ' '.join([s.get('chunk_preview', '') for s in sources])

        for claim in claims:
            verification = self._verify_claim(claim, source_text_combined, sources)

            if verification['verified']:
                fact_check['verified_claims'].append({
                    'claim': claim,
                    'source': verification['source'],
                    'confidence': verification['confidence']
                })
            else:
                fact_check['unverified_claims'].append({
                    'claim': claim,
                    'reason': verification['reason']
                })
                fact_check['confidence'] *= 0.9

        # Calculate overall confidence
        if claims:
            verified_ratio = len(fact_check['verified_claims']) / len(claims)
            fact_check['confidence'] *= verified_ratio

        return fact_check

    def _extract_claims(self, response: str) -> List[str]:
        """Extract factual claims from response"""
        # Split into sentences
        sentences = re.split(r'[.!?]+', response)

        claims = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue

            # Filter out questions and non-factual statements
            if '?' in sentence:
                continue

            # Look for factual indicators (numbers, specific terms, etc.)
            has_numbers = bool(re.search(r'\d+', sentence))
            has_specific_terms = bool(re.search(r'\b(?:is|are|has|have|contains|includes)\b', sentence.lower()))

            if has_numbers or has_specific_terms:
                claims.append(sentence)

        return claims[:5]  # Limit to top 5 claims

    def _verify_claim(self, claim: str, source_text: str, sources: List[Dict]) -> Dict:
        """Verify a single claim against sources"""
        claim_lower = claim.lower()
        source_lower = source_text.lower()

        # Check for key phrases in claim
        claim_words = set(claim_lower.split())
        source_words = set(source_lower.split())

        # Calculate overlap
        overlap = len(claim_words.intersection(source_words))
        overlap_ratio = overlap / len(claim_words) if claim_words else 0

        # Find which source best supports the claim
        best_source = None
        best_overlap = 0

        for source in sources:
            source_chunk = source.get('chunk_preview', '').lower()
            source_chunk_words = set(source_chunk.split())
            chunk_overlap = len(claim_words.intersection(source_chunk_words))

            if chunk_overlap > best_overlap:
                best_overlap = chunk_overlap
                best_source = source.get('document_name', 'Unknown')

        # Determine if verified
        if overlap_ratio > 0.3:
            return {
                'verified': True,
                'source': best_source,
                'confidence': min(overlap_ratio, 1.0),
                'reason': 'Supported by source material'
            }
        else:
            return {
                'verified': False,
                'source': None,
                'confidence': 0.0,
                'reason': 'Insufficient support in sources'
            }

    def calculate_confidence_indicators(
        self,
        retrieval_confidence: float,
        validation_result: Dict,
        fact_check_result: Dict,
        source_count: int
    ) -> Dict:
        """Calculate comprehensive confidence indicators"""

        # Component scores
        retrieval_score = retrieval_confidence
        validation_score = validation_result.get('quality_score', 0.5)
        fact_check_score = fact_check_result.get('confidence', 0.5)
        source_score = min(source_count / 5.0, 1.0)  # Ideal 5+ sources

        # Weighted average
        overall_confidence = (
            retrieval_score * 0.35 +
            validation_score * 0.25 +
            fact_check_score * 0.30 +
            source_score * 0.10
        )

        # Determine level
        if overall_confidence >= self.confidence_thresholds['high']:
            level = 'high'
            color = 'green'
            description = 'High confidence - Well-supported by sources'
        elif overall_confidence >= self.confidence_thresholds['medium']:
            level = 'medium'
            color = 'yellow'
            description = 'Medium confidence - Moderately supported'
        elif overall_confidence >= self.confidence_thresholds['low']:
            level = 'low'
            color = 'orange'
            description = 'Low confidence - Limited source support'
        else:
            level = 'very_low'
            color = 'red'
            description = 'Very low confidence - Insufficient evidence'

        return {
            'overall_confidence': overall_confidence,
            'level': level,
            'color': color,
            'description': description,
            'components': {
                'retrieval': retrieval_score,
                'validation': validation_score,
                'fact_check': fact_check_score,
                'sources': source_score
            },
            'breakdown': {
                'retrieval': f'{retrieval_score:.0%}',
                'validation': f'{validation_score:.0%}',
                'fact_check': f'{fact_check_score:.0%}',
                'sources': f'{source_count} sources'
            }
        }

    def generate_follow_up_questions(
        self,
        query: str,
        response: str,
        sources: List[Dict],
        query_intent: str,
        entities: Dict
    ) -> List[str]:
        """Generate relevant follow-up questions"""

        follow_ups = []

        # Intent-based follow-ups
        if query_intent == 'factual_lookup':
            follow_ups.extend(self._generate_factual_follow_ups(query, response, entities))
        elif query_intent == 'comparison':
            follow_ups.extend(self._generate_comparison_follow_ups(query, response, entities))
        elif query_intent == 'procedural':
            follow_ups.extend(self._generate_procedural_follow_ups(query, response))
        elif query_intent == 'analytical':
            follow_ups.extend(self._generate_analytical_follow_ups(query, response))

        # Source-based follow-ups
        if sources:
            follow_ups.extend(self._generate_source_follow_ups(sources))

        # Entity-based follow-ups
        if entities:
            follow_ups.extend(self._generate_entity_follow_ups(entities))

        # Remove duplicates and limit
        follow_ups = list(dict.fromkeys(follow_ups))[:5]

        return follow_ups

    def _generate_factual_follow_ups(self, query: str, response: str, entities: Dict) -> List[str]:
        """Generate follow-ups for factual queries"""
        follow_ups = []

        # Extract main subject
        main_entity = entities.get('topics', [''])[0] if entities.get('topics') else None

        if main_entity:
            follow_ups.append(f"Tell me more about {main_entity}")
            follow_ups.append(f"What are the key features of {main_entity}?")
            follow_ups.append(f"How does {main_entity} compare to alternatives?")

        return follow_ups

    def _generate_comparison_follow_ups(self, query: str, response: str, entities: Dict) -> List[str]:
        """Generate follow-ups for comparison queries"""
        follow_ups = []

        topics = entities.get('topics', [])
        if len(topics) >= 2:
            follow_ups.append(f"What are the pros and cons of each?")
            follow_ups.append(f"Which one is better for my specific needs?")
            follow_ups.append(f"Are there other alternatives to consider?")

        return follow_ups

    def _generate_procedural_follow_ups(self, query: str, response: str) -> List[str]:
        """Generate follow-ups for procedural queries"""
        return [
            "What are the common challenges with this process?",
            "Are there any prerequisites I should know about?",
            "Can you provide more details on any specific step?"
        ]

    def _generate_analytical_follow_ups(self, query: str, response: str) -> List[str]:
        """Generate follow-ups for analytical queries"""
        return [
            "What are the implications of this?",
            "Are there any related considerations?",
            "What supporting evidence exists for this?"
        ]

    def _generate_source_follow_ups(self, sources: List[Dict]) -> List[str]:
        """Generate follow-ups based on available sources"""
        follow_ups = []

        documents = list(set([s.get('document_name', '') for s in sources if s.get('document_name')]))

        if documents:
            if len(documents) > 1:
                follow_ups.append(f"What else does {documents[0]} discuss?")
            follow_ups.append("Are there other relevant documents I should review?")

        return follow_ups

    def _generate_entity_follow_ups(self, entities: Dict) -> List[str]:
        """Generate follow-ups based on extracted entities"""
        follow_ups = []

        if entities.get('documents'):
            doc = entities['documents'][0]
            follow_ups.append(f"What other information is in {doc}?")

        if entities.get('values'):
            follow_ups.append("Can you explain these numbers in more context?")

        return follow_ups
