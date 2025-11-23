"""
Modern Retrieval Service with Hybrid Search
Combines semantic search with keyword matching and reranking
"""
from typing import List, Dict, Optional
import re
from collections import Counter

class RetrievalService:
    def __init__(self):
        self.min_similarity_threshold = 0.3
        self.max_results = 10
    
    def hybrid_search(
        self,
        semantic_results: List[Dict],
        query: str,
        all_chunks: List[Dict],
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> List[Dict]:
        """
        Perform hybrid search combining semantic and keyword matching
        """
        if not semantic_results:
            # Fallback to keyword search only
            return self._keyword_search(query, all_chunks)
        
        # Extract query keywords (remove stop words)
        query_keywords = self._extract_keywords(query)
        
        # Score each semantic result with keyword boost
        scored_results = []
        for result in semantic_results:
            chunk_text = result.get('text', '').lower()
            
            # Semantic score (from vector search)
            semantic_score = result.get('similarity', 0.0)
            
            # Keyword score
            keyword_score = self._calculate_keyword_score(query_keywords, chunk_text)
            
            # Combined score
            combined_score = (semantic_score * semantic_weight) + (keyword_score * keyword_weight)
            
            result['combined_score'] = combined_score
            result['keyword_score'] = keyword_score
            scored_results.append(result)
        
        # Also check chunks not in semantic results for keyword matches
        semantic_chunk_ids = {r.get('chunk_id', '') for r in semantic_results}
        
        for chunk in all_chunks:
            chunk_id = chunk.get('chunk_id', '') or f"{chunk.get('document_id', '')}_{chunk.get('chunk_index', 0)}"
            if chunk_id not in semantic_chunk_ids:
                chunk_text = (chunk.get('text', '') if isinstance(chunk.get('text'), str) else str(chunk.get('text', ''))).lower()
                keyword_score = self._calculate_keyword_score(query_keywords, chunk_text)
                
                # Only include if keyword score is high enough
                if keyword_score > 0.3:
                    chunk_dict = {
                        'chunk_id': chunk_id,
                        'text': chunk.get('text', ''),
                        'document_id': chunk.get('document_id', ''),
                        'document_name': chunk.get('document_name', ''),
                        'chunk_index': chunk.get('chunk_index', 0),
                        'pages': chunk.get('pages', []),
                        'similarity': 0.0,  # No semantic match
                        'keyword_score': keyword_score,
                        'combined_score': keyword_score * keyword_weight
                    }
                    scored_results.append(chunk_dict)
        
        # Sort by combined score
        scored_results.sort(key=lambda x: x.get('combined_score', 0), reverse=True)
        
        return scored_results[:self.max_results]
    
    def rerank_results(self, results: List[Dict], query: str) -> List[Dict]:
        """
        Rerank results based on query relevance and quality
        """
        if not results:
            return []
        
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        for result in results:
            chunk_text = result.get('text', '').lower()
            
            # Boost score if query words appear in chunk
            word_matches = len(query_words.intersection(set(chunk_text.split())))
            word_match_boost = min(word_matches / max(len(query_words), 1), 0.2)
            
            # Boost score if chunk is longer (more context)
            length_boost = min(len(chunk_text) / 1000, 0.1)
            
            # Apply boosts
            current_score = result.get('combined_score', result.get('similarity', 0.0))
            result['final_score'] = current_score + word_match_boost + length_boost
        
        # Sort by final score
        results.sort(key=lambda x: x.get('final_score', 0), reverse=True)
        
        return results
    
    def filter_by_threshold(self, results: List[Dict], threshold: float = None) -> List[Dict]:
        """Filter results by similarity threshold"""
        if threshold is None:
            threshold = self.min_similarity_threshold
        
        filtered = []
        for result in results:
            score = result.get('final_score', result.get('combined_score', result.get('similarity', 0.0)))
            if score >= threshold:
                filtered.append(result)
        
        return filtered
    
    def diversify_results(self, results: List[Dict], max_per_document: int = 3) -> List[Dict]:
        """Diversify results to avoid over-representation from single document"""
        if not results:
            return []
        
        diversified = []
        doc_counts = Counter()
        
        for result in results:
            doc_id = result.get('document_id', '')
            if doc_counts[doc_id] < max_per_document:
                diversified.append(result)
                doc_counts[doc_id] += 1
        
        return diversified
    
    def _keyword_search(self, query: str, all_chunks: List[Dict]) -> List[Dict]:
        """Fallback keyword search when semantic search fails"""
        query_keywords = self._extract_keywords(query)
        
        scored_chunks = []
        for chunk in all_chunks:
            chunk_text = (chunk.get('text', '') if isinstance(chunk.get('text'), str) else str(chunk.get('text', ''))).lower()
            keyword_score = self._calculate_keyword_score(query_keywords, chunk_text)
            
            if keyword_score > 0.2:
                chunk_dict = {
                    'chunk_id': chunk.get('chunk_id', ''),
                    'text': chunk.get('text', ''),
                    'document_id': chunk.get('document_id', ''),
                    'document_name': chunk.get('document_name', ''),
                    'chunk_index': chunk.get('chunk_index', 0),
                    'pages': chunk.get('pages', []),
                    'similarity': 0.0,
                    'keyword_score': keyword_score,
                    'combined_score': keyword_score,
                    'final_score': keyword_score
                }
                scored_chunks.append(chunk_dict)
        
        scored_chunks.sort(key=lambda x: x.get('final_score', 0), reverse=True)
        return scored_chunks[:self.max_results]
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract meaningful keywords from query"""
        # Remove stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'should', 'could', 'may', 'might', 'can', 'this', 'that',
            'these', 'those', 'what', 'which', 'who', 'where', 'when', 'why',
            'how', 'about', 'into', 'through', 'during', 'including', 'against'
        }
        
        # Extract words
        words = re.findall(r'\b\w+\b', query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return keywords
    
    def _calculate_keyword_score(self, keywords: List[str], text: str) -> float:
        """Calculate keyword match score"""
        if not keywords:
            return 0.0
        
        text_words = set(re.findall(r'\b\w+\b', text.lower()))
        matches = sum(1 for keyword in keywords if keyword in text_words)
        
        # Normalize score
        return min(matches / len(keywords), 1.0)

