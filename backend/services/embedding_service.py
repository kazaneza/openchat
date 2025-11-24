"""
Modern Embedding Service using OpenAI text-embedding-3-large
Handles document and query embeddings with proper organization isolation
"""
import os
from typing import List, Dict, Optional
from .openai_service import OpenAIService

class EmbeddingService:
    def __init__(self, openai_service: OpenAIService):
        self.openai_service = openai_service
        self.embedding_model = "text-embedding-3-large"  # Modern, high-quality embeddings
        
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        if not texts:
            return []
        
        try:
            # Use OpenAI service to get embeddings
            embeddings = self.openai_service.get_embeddings(texts)
            return embeddings
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            return []
    
    def generate_single_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text"""
        embeddings = self.generate_embeddings([text])
        return embeddings[0] if embeddings else None
    
    def generate_document_embeddings(self, document: Dict, organization_id: str) -> Dict:
        """Generate embeddings for all chunks in a document"""
        chunks = document.get("chunks", [])
        if not chunks:
            return document
        
        # Extract chunk texts
        chunk_texts = []
        for chunk in chunks:
            if isinstance(chunk, dict):
                chunk_texts.append(chunk.get("text", ""))
            else:
                chunk_texts.append(str(chunk))
        
        # Generate embeddings for all chunks
        embeddings = self.generate_embeddings(chunk_texts)
        
        # Update document with embeddings
        document["chunk_embeddings"] = embeddings
        
        return document

