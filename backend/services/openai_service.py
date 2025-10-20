import os
import openai
from openai import OpenAI
import tiktoken
from typing import List, Dict, Optional, Generator
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import json
import traceback

class OpenAIService:
    def __init__(self):
        self.client = None
        self.embedding_model = "text-embedding-3-small"
        self.chat_model = os.getenv("OPENAI_MODEL", "gpt-4o")
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
    
    def generate_response(self, system_prompt: str, user_message: str, context: str = "", is_document_query: bool = True, user_language: str = "en", max_tokens: int = None) -> str:
        """Generate AI response using OpenAI GPT with natural language matching"""
        if not self.client:
            return "I'm currently unable to process your request. Please try again later or contact support if the issue persists."

        try:
            # Use provided max_tokens or default
            tokens_to_use = max_tokens if max_tokens is not None else self.max_tokens

            # Simple instruction to match user's language naturally
            language_instruction = "\n\nIMPORTANT: Always respond in the same language as the user's message. Match their language naturally. Never mention documents, knowledge bases, or technical implementation details to users."

            # Use the provided system prompt with language enforcement
            final_system_prompt = f"{system_prompt}{language_instruction}"

            if is_document_query and context:
                # Document-specific query with RAG
                context_addition = f"\n\nAvailable Information:\n{context}\n\nInstructions:\n- Use the provided information to give comprehensive answers\n- If the information doesn't fully address the question, provide what you can and offer to help in other ways\n- Be helpful and polite in your responses\n- Never mention that information comes from documents or databases"
                final_system_prompt += context_addition
            else:
                # General query
                if context:
                    final_system_prompt += f"\n\nAdditional context: {context}"
                else:
                    final_system_prompt += "\n\nProvide helpful responses based on your knowledge."

            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": final_system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=tokens_to_use,
                temperature=self.temperature
            )

            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API Error: {str(e)}")
            traceback.print_exc()
            return "I apologize, but I'm having trouble processing your request right now. Please try again in a moment, or rephrase your question."

    def generate_response_stream(
        self,
        system_prompt: str,
        user_message: str,
        context: str = "",
        is_document_query: bool = True,
        user_language: str = "en"
    ) -> Generator[str, None, None]:
        """Generate streaming AI response using OpenAI GPT"""
        if not self.client:
            yield "I'm currently unable to process your request. Please try again later."
            return

        try:
            # Build final prompt same as non-streaming
            language_instruction = "\n\nIMPORTANT: Always respond in the same language as the user's message. Match their language naturally."
            final_system_prompt = f"{system_prompt}{language_instruction}"

            if is_document_query and context:
                context_addition = f"\n\nAvailable Information:\n{context}\n\nInstructions:\n- Use the provided information to give comprehensive answers\n- Be helpful and polite in your responses"
                final_system_prompt += context_addition
            elif context:
                final_system_prompt += f"\n\nAdditional context: {context}"

            # Create streaming completion
            stream = self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": final_system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=True
            )

            # Yield chunks as they arrive
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            print(f"OpenAI Streaming API Error: {str(e)}")
            traceback.print_exc()
            yield "I apologize, but I'm having trouble processing your request right now."

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