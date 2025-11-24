"""
Modern Intelligent Chunking Service
Uses semantic-aware chunking with proper overlap and context preservation
"""
import tiktoken
import re
from typing import List, Dict

class ChunkingService:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize chunking service
        chunk_size: Target tokens per chunk
        chunk_overlap: Overlap in tokens between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def chunk_text(self, text: str, page_texts: List[Dict] = None) -> List[Dict]:
        """
        Intelligently chunk text with semantic awareness
        Preserves context and maintains page information
        """
        if not text or not text.strip():
            return []
        
        # First, try to split by paragraphs (semantic boundaries)
        paragraphs = self._split_into_paragraphs(text)
        
        chunks = []
        current_chunk = ""
        current_tokens = 0
        
        for paragraph in paragraphs:
            para_tokens = len(self.encoding.encode(paragraph))
            
            # If paragraph fits in current chunk
            if current_tokens + para_tokens <= self.chunk_size:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
                current_tokens += para_tokens
            else:
                # Save current chunk if it has content
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # If paragraph itself is too large, split it by sentences
                if para_tokens > self.chunk_size:
                    sentence_chunks = self._split_large_paragraph(paragraph)
                    chunks.extend(sentence_chunks)
                    current_chunk = ""
                    current_tokens = 0
                else:
                    # Start new chunk with this paragraph
                    current_chunk = paragraph
                    current_tokens = para_tokens
        
        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # Add overlap between chunks for better context
        chunks_with_overlap = self._add_overlap(chunks)
        
        # Add metadata (pages, token counts, etc.)
        chunks_with_metadata = []
        for chunk_text in chunks_with_overlap:
            pages = self._find_pages_for_chunk(chunk_text, text, page_texts) if page_texts else []
            token_count = len(self.encoding.encode(chunk_text))
            
            chunks_with_metadata.append({
                "text": chunk_text,
                "pages": pages,
                "token_count": token_count,
                "char_count": len(chunk_text)
            })
        
        return chunks_with_metadata
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs, preserving structure"""
        # Split by double newlines (paragraph breaks)
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        # If no paragraph breaks, try single newlines
        if len(paragraphs) == 1:
            paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        
        return paragraphs
    
    def _split_large_paragraph(self, paragraph: str) -> List[str]:
        """Split a large paragraph into smaller chunks by sentences"""
        # Split by sentence endings
        sentences = re.split(r'([.!?]+)', paragraph)
        
        # Recombine sentences with their punctuation
        combined_sentences = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                combined_sentences.append(sentences[i] + sentences[i + 1])
            else:
                combined_sentences.append(sentences[i])
        
        chunks = []
        current_chunk = ""
        current_tokens = 0
        
        for sentence in combined_sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_tokens = len(self.encoding.encode(sentence))
            
            if current_tokens + sentence_tokens <= self.chunk_size:
                current_chunk += " " + sentence if current_chunk else sentence
                current_tokens += sentence_tokens
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
                current_tokens = sentence_tokens
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _add_overlap(self, chunks: List[str]) -> List[str]:
        """Add overlap between chunks for better context"""
        if len(chunks) <= 1:
            return chunks
        
        chunks_with_overlap = []
        
        for i, chunk in enumerate(chunks):
            chunks_with_overlap.append(chunk)
            
            # Add overlap with next chunk
            if i < len(chunks) - 1:
                overlap_text = self._create_overlap(chunk, chunks[i + 1])
                if overlap_text:
                    chunks_with_overlap.append(overlap_text)
        
        return chunks_with_overlap
    
    def _create_overlap(self, chunk1: str, chunk2: str) -> str:
        """Create overlap text between two chunks"""
        # Get last sentences from chunk1
        sentences1 = re.split(r'[.!?]+', chunk1)
        sentences2 = re.split(r'[.!?]+', chunk2)
        
        # Take last 2-3 sentences from chunk1 and first 1-2 from chunk2
        overlap_sentences = []
        overlap_tokens = 0
        
        # Add from end of chunk1
        for sentence in reversed(sentences1[-3:]):
            sentence = sentence.strip()
            if sentence:
                sentence_tokens = len(self.encoding.encode(sentence))
                if overlap_tokens + sentence_tokens <= self.chunk_overlap // 2:
                    overlap_sentences.insert(0, sentence)
                    overlap_tokens += sentence_tokens
                else:
                    break
        
        # Add from beginning of chunk2
        for sentence in sentences2[:2]:
            sentence = sentence.strip()
            if sentence:
                sentence_tokens = len(self.encoding.encode(sentence))
                if overlap_tokens + sentence_tokens <= self.chunk_overlap:
                    overlap_sentences.append(sentence)
                    overlap_tokens += sentence_tokens
                else:
                    break
        
        return " ".join(overlap_sentences) if overlap_sentences else ""
    
    def _find_pages_for_chunk(self, chunk_text: str, full_text: str, page_texts: List[Dict]) -> List[int]:
        """Find which pages a chunk spans"""
        if not page_texts:
            return []
        
        # Find chunk position in full text
        chunk_start = full_text.find(chunk_text)
        if chunk_start == -1:
            return []
        
        chunk_end = chunk_start + len(chunk_text)
        
        # Find overlapping pages
        pages = []
        for page_info in page_texts:
            page_start = page_info.get('char_start', 0)
            page_end = page_info.get('char_end', len(full_text))
            
            # Check if chunk overlaps with this page
            if not (chunk_end < page_start or chunk_start > page_end):
                pages.append(page_info.get('page_number', 1))
        
        return pages if pages else [1]

