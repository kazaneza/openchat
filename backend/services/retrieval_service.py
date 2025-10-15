from typing import List, Dict, Optional, Tuple
import re
import math

class RetrievalService:
    def __init__(self):
        self.min_chunks = 3
        self.max_chunks = 15
        self.base_similarity_threshold = 0.4

    def analyze_query_complexity(self, query: str) -> Dict:
        """Analyze query to determine complexity and retrieval needs"""
        words = query.split()
        word_count = len(words)

        # Detect question types
        question_words = ['what', 'when', 'where', 'who', 'why', 'how', 'which']
        is_question = any(query.lower().startswith(qw) for qw in question_words) or '?' in query

        # Detect comparison/analysis queries
        comparison_words = ['compare', 'difference', 'versus', 'vs', 'better', 'worse', 'contrast']
        is_comparison = any(word in query.lower() for word in comparison_words)

        # Detect multi-part queries
        has_and = ' and ' in query.lower()
        has_or = ' or ' in query.lower()
        has_multiple_questions = query.count('?') > 1
        is_multipart = has_and or has_or or has_multiple_questions

        # Detect specific vs broad queries
        has_numbers = bool(re.search(r'\d', query))
        has_quotes = '"' in query or "'" in query
        is_specific = has_numbers or has_quotes or word_count <= 5

        # Calculate complexity score
        complexity_score = 0
        if is_question:
            complexity_score += 1
        if is_comparison:
            complexity_score += 2
        if is_multipart:
            complexity_score += 2
        if word_count > 15:
            complexity_score += 1
        if not is_specific:
            complexity_score += 1

        # Determine complexity level
        if complexity_score >= 4:
            complexity_level = "high"
        elif complexity_score >= 2:
            complexity_level = "medium"
        else:
            complexity_level = "low"

        return {
            "complexity_level": complexity_level,
            "complexity_score": complexity_score,
            "word_count": word_count,
            "is_question": is_question,
            "is_comparison": is_comparison,
            "is_multipart": is_multipart,
            "is_specific": is_specific
        }

    def calculate_adaptive_parameters(self, query_analysis: Dict) -> Dict:
        """Calculate optimal retrieval parameters based on query complexity"""
        complexity_level = query_analysis["complexity_level"]

        if complexity_level == "high":
            top_k = self.max_chunks
            similarity_threshold = 0.35
            keyword_weight = 0.3
        elif complexity_level == "medium":
            top_k = 8
            similarity_threshold = 0.4
            keyword_weight = 0.25
        else:
            top_k = 5
            similarity_threshold = 0.5
            keyword_weight = 0.2

        # Adjust for specific query types
        if query_analysis["is_comparison"]:
            top_k = min(top_k + 3, self.max_chunks)

        if query_analysis["is_multipart"]:
            top_k = min(top_k + 2, self.max_chunks)

        if query_analysis["is_specific"]:
            similarity_threshold += 0.1

        return {
            "top_k": top_k,
            "similarity_threshold": similarity_threshold,
            "keyword_weight": keyword_weight
        }

    def keyword_search(self, query: str, chunks_with_metadata: List[Dict]) -> List[Dict]:
        """Perform keyword-based search with scoring"""
        query_words = set(query.lower().split())

        # Extract important words (remove common stop words)
        stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with', 'what', 'when', 'where', 'who', 'why', 'how'
        }

        important_query_words = query_words - stop_words

        scored_chunks = []
        for chunk in chunks_with_metadata:
            text = chunk.get('text', '').lower()
            chunk_words = set(text.split())

            # Calculate different match scores
            exact_matches = len(important_query_words.intersection(chunk_words))
            partial_matches = sum(1 for qw in important_query_words if any(qw in cw for cw in chunk_words))

            # Boost score for phrase matches
            phrase_matches = sum(1 for qw in query_words if qw in text)

            # Calculate keyword score (0-1)
            if len(important_query_words) > 0:
                keyword_score = (exact_matches * 2 + partial_matches + phrase_matches * 0.5) / (len(important_query_words) * 3)
            else:
                keyword_score = phrase_matches / max(len(query_words), 1)

            scored_chunks.append({
                **chunk,
                'keyword_score': min(keyword_score, 1.0)
            })

        return scored_chunks

    def hybrid_search(
        self,
        semantic_results: List[Dict],
        query: str,
        all_chunks: List[Dict],
        keyword_weight: float = 0.25
    ) -> List[Dict]:
        """Combine semantic and keyword search with weighted scoring"""

        # Get keyword scores for all chunks
        chunks_with_keyword_scores = self.keyword_search(query, all_chunks)
        keyword_score_map = {
            chunk.get('chunk_id', ''): chunk.get('keyword_score', 0)
            for chunk in chunks_with_keyword_scores
        }

        # Combine scores for semantic results
        hybrid_results = []
        for chunk in semantic_results:
            chunk_id = chunk.get('chunk_id', '')
            semantic_score = chunk.get('similarity', 0)
            keyword_score = keyword_score_map.get(chunk_id, 0)

            # Weighted hybrid score
            hybrid_score = (1 - keyword_weight) * semantic_score + keyword_weight * keyword_score

            hybrid_results.append({
                **chunk,
                'keyword_score': keyword_score,
                'semantic_score': semantic_score,
                'hybrid_score': hybrid_score,
                'similarity': hybrid_score
            })

        # Add high-scoring keyword matches that weren't in semantic results
        semantic_chunk_ids = {chunk.get('chunk_id', '') for chunk in semantic_results}

        for chunk in chunks_with_keyword_scores:
            chunk_id = chunk.get('chunk_id', '')
            if chunk_id not in semantic_chunk_ids and chunk.get('keyword_score', 0) >= 0.6:
                # High keyword match, add with adjusted hybrid score
                hybrid_score = keyword_weight * chunk.get('keyword_score', 0)
                hybrid_results.append({
                    **chunk,
                    'keyword_score': chunk.get('keyword_score', 0),
                    'semantic_score': 0,
                    'hybrid_score': hybrid_score,
                    'similarity': hybrid_score
                })

        return hybrid_results

    def rerank_results(self, results: List[Dict], query_analysis: Dict) -> List[Dict]:
        """Re-rank results based on multiple signals"""

        for result in results:
            base_score = result.get('similarity', 0)

            # Boost factors
            recency_boost = 0
            page_boost = 0
            length_boost = 0

            # Boost for page 1 content (often contains important info)
            pages = result.get('pages', [])
            if pages and 1 in pages:
                page_boost = 0.05

            # Boost for medium-length chunks (not too short, not too long)
            text = result.get('text', '')
            text_length = len(text.split())
            if 50 <= text_length <= 300:
                length_boost = 0.03

            # Penalize very short chunks
            if text_length < 20:
                length_boost = -0.1

            # For comparison queries, boost chunks with comparative language
            if query_analysis.get('is_comparison', False):
                comparative_words = ['more', 'less', 'better', 'worse', 'than', 'versus', 'compared']
                if any(word in text.lower() for word in comparative_words):
                    length_boost += 0.05

            # Calculate final score
            final_score = base_score + recency_boost + page_boost + length_boost
            result['final_score'] = min(final_score, 1.0)
            result['similarity'] = result['final_score']

        # Sort by final score
        results.sort(key=lambda x: x.get('final_score', 0), reverse=True)

        return results

    def filter_by_dynamic_threshold(
        self,
        results: List[Dict],
        base_threshold: float,
        query_analysis: Dict
    ) -> List[Dict]:
        """Filter results using dynamic threshold based on query and result quality"""

        if not results:
            return results

        # Calculate threshold based on score distribution
        scores = [r.get('similarity', 0) for r in results]
        max_score = max(scores) if scores else 0
        avg_score = sum(scores) / len(scores) if scores else 0

        # Dynamic threshold calculation
        if max_score > 0.8:
            # High confidence results, use stricter threshold
            threshold = max(base_threshold, avg_score * 0.8)
        elif max_score > 0.6:
            # Medium confidence, use base threshold
            threshold = base_threshold
        else:
            # Lower confidence, be more lenient
            threshold = min(base_threshold, max_score * 0.7)

        # Adjust for query complexity
        if query_analysis.get('complexity_level') == 'high':
            # Allow more results for complex queries
            threshold *= 0.9
        elif query_analysis.get('complexity_level') == 'low' and query_analysis.get('is_specific'):
            # Be stricter for simple, specific queries
            threshold *= 1.1

        # Filter results
        filtered_results = [r for r in results if r.get('similarity', 0) >= threshold]

        # Ensure minimum results if we have any
        if len(filtered_results) < 3 and len(results) >= 3:
            filtered_results = results[:3]

        return filtered_results

    def diversify_results(self, results: List[Dict], max_per_document: int = 3) -> List[Dict]:
        """Ensure diversity by limiting chunks from same document"""
        document_counts = {}
        diversified = []

        for result in results:
            doc_id = result.get('document_id', '')
            current_count = document_counts.get(doc_id, 0)

            if current_count < max_per_document:
                diversified.append(result)
                document_counts[doc_id] = current_count + 1

        return diversified

    def get_chunk_neighbors(
        self,
        chunk: Dict,
        all_chunks: List[Dict],
        context_window: int = 1
    ) -> List[Dict]:
        """Get neighboring chunks for better context"""
        chunk_index = chunk.get('chunk_index', -1)
        document_id = chunk.get('document_id', '')

        if chunk_index == -1:
            return []

        neighbors = []
        for other_chunk in all_chunks:
            if (other_chunk.get('document_id') == document_id and
                other_chunk.get('chunk_index', -1) != chunk_index):
                index_diff = abs(other_chunk.get('chunk_index', 0) - chunk_index)
                if index_diff <= context_window:
                    neighbors.append({
                        **other_chunk,
                        'is_neighbor': True,
                        'neighbor_distance': index_diff
                    })

        return neighbors
