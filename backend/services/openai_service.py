import os
import openai
from openai import OpenAI
import tiktoken
from typing import List, Dict, Optional
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import json
import traceback

class OpenAIService:
    def __init__(self):
        self.client = None
        self.embedding_model = "text-embedding-3-small"
        self.chat_model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        self.max_tokens = int(os.getenv("MAX_TOKENS", "1000"))
        self.temperature = float(os.getenv("TEMPERATURE", "0.7"))
        
        if os.getenv("OPENAI_API_KEY"):
            try:
                self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                print("OpenAI client initialized successfully")
            except Exception as e:
                print(f"Failed to initialize OpenAI client: {e}")
                self.client = None
        else:
            print("OpenAI API key not found in environment variables")
    
    def is_available(self) -> bool:
        """Check if OpenAI service is available"""
        return self.client is not None
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for a list of texts"""
        if not self.client:
            return []
        
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            return [embedding.embedding for embedding in response.data]
        except Exception as e:
            print(f"Error getting embeddings: {e}")
            return []
    
    def get_single_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for a single text"""
        embeddings = self.get_embeddings([text])
        return embeddings[0] if embeddings else None
    
    def find_similar_chunks(self, query_embedding: List[float], chunk_embeddings: List[Dict], top_k: int = 3) -> List[Dict]:
        """Find most similar chunks using cosine similarity"""
        if not query_embedding or not chunk_embeddings:
            return []
        
        try:
            # Extract embeddings and metadata
            embeddings_matrix = []
            chunks_data = []
            
            for chunk_data in chunk_embeddings:
                if 'embedding' in chunk_data and chunk_data['embedding']:
                    embeddings_matrix.append(chunk_data['embedding'])
                    chunks_data.append(chunk_data)
            
            if not embeddings_matrix:
                return []
            
            # Calculate cosine similarity
            query_embedding_array = np.array(query_embedding).reshape(1, -1)
            embeddings_array = np.array(embeddings_matrix)
            
            similarities = cosine_similarity(query_embedding_array, embeddings_array)[0]
            
            # Get top-k most similar chunks
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            similar_chunks = []
            for idx in top_indices:
                if similarities[idx] > 0.1:  # Minimum similarity threshold
                    chunk_data = chunks_data[idx].copy()
                    chunk_data['similarity'] = float(similarities[idx])
                    similar_chunks.append(chunk_data)
            
            return similar_chunks
        except Exception as e:
            print(f"Error finding similar chunks: {e}")
            return []
    
    def generate_response(self, system_prompt: str, user_message: str, context: str = "", is_document_query: bool = True, user_language: str = "en") -> str:
        """Generate AI response using OpenAI GPT with language enforcement"""
        if not self.client:
            return "OpenAI API key is not configured. Please set your OPENAI_API_KEY in the .env file."
        
        try:
            # Add critical language enforcement to system prompt
            language_names = {
                'rw': 'Kinyarwanda',
                'fr': 'French', 
                'sw': 'Swahili',
                'en': 'English',
                'es': 'Spanish',
                'de': 'German',
                'it': 'Italian',
                'pt': 'Portuguese'
            }
            
            language_name = language_names.get(user_language, user_language)
            language_instruction = f"\n\nCRITICAL: You MUST respond in {language_name} ({user_language}). Do not use any other language."
            
            # Use the provided system prompt with language enforcement
            final_system_prompt = f"{system_prompt}{language_instruction}"
            
            if is_document_query and context:
                # Document-specific query with RAG
                context_addition = f"\n\nDocument Context:\n{context}\n\nInstructions:\n- Answer based on the provided context when possible\n- If the context doesn't contain relevant information, acknowledge this\n- Be helpful and polite in your responses"
                final_system_prompt += context_addition
            else:
                # General query
                if context:
                    final_system_prompt += f"\n\nAvailable context: {context}"
                else:
                    final_system_prompt += "\n\nNo specific document context provided."

            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": final_system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API Error: {str(e)}")
            traceback.print_exc()
            return f"Sorry, there was an error processing your request: {str(e)}"
    
    def detect_query_type(self, message: str) -> str:
        """Detect if query is document-specific or general"""
        document_keywords = [
            'document', 'file', 'pdf', 'uploaded', 'content', 'text',
            'according to', 'based on', 'in the document', 'what does it say',
            'find', 'search', 'look for', 'extract', 'summarize'
        ]
        
        general_keywords = [
            'hello', 'hi', 'help', 'how are you', 'what can you do',
            'explain', 'define', 'what is', 'how to', 'why', 'when'
        ]
        
        message_lower = message.lower()
        
        # Check for document-specific keywords
        doc_score = sum(1 for keyword in document_keywords if keyword in message_lower)
        general_score = sum(1 for keyword in general_keywords if keyword in message_lower)
        
        if doc_score > general_score:
            return "document"
        elif general_score > 0 and doc_score == 0:
            return "general"
        else:
            return "mixed"  # Could be either, try document first