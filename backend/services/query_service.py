from typing import List, Dict, Optional, Tuple
from .openai_service import OpenAIService
from .document_service import DocumentService
from .embedding_service import EmbeddingService
from .vector_service import VectorService
from .prompt_service import PromptService
from .language_service import LanguageService
from .translation_service import TranslationService

class QueryService:
    def __init__(self, openai_service: OpenAIService, document_service: DocumentService, embedding_service: EmbeddingService, vector_service: VectorService, prompt_service: PromptService, translation_service: TranslationService):
        self.openai_service = openai_service
        self.document_service = document_service
        self.embedding_service = embedding_service
        self.vector_service = vector_service
        self.prompt_service = prompt_service
        self.language_service = LanguageService()
        self.translation_service = translation_service
    
    def process_query(self, message: str, organization: Dict, user_context: Dict = None) -> str:
        """Process user query with RAG approach"""
        try:
            # Step 1: Detect user's language and translate to English
            detected_language, confidence = self.language_service.detect_language(message)
            print(f"Detected language: {detected_language} (confidence: {confidence:.2f})")
            
            # Handle greetings with localized responses
            if self.language_service.is_greeting(message, detected_language):
                return self.language_service.handle_greeting(
                    message, 
                    detected_language, 
                    organization.get("name")
                )
            
            # Handle low confidence language detection
            if confidence < 0.5:
                options = self.language_service.get_language_options_message()
                return options.get(detected_language, options['en'])
            
            # Step 2: Translate query to English for processing
            english_query, final_lang, final_confidence = self.translation_service.detect_and_translate_to_english(message)
            
            # Use the more confident language detection
            if final_confidence > confidence:
                detected_language = final_lang
                confidence = final_confidence
            
            # Step 3: Process query in English using RAG
            query_type = self.openai_service.detect_query_type(english_query)
            print(f"Query type detected: {query_type}")
            
            # Get documents
            documents = organization.get("documents", [])
            
            # Process the query in English
            if not documents or query_type == "general":
                # Handle general queries or no documents
                english_response = self._handle_general_query(english_query, organization, query_type)
            else:
                # Handle document-specific queries with RAG
                english_response = self._handle_document_query(english_query, organization, documents)
            
            # Step 4: Translate response back to user's language
            if self.translation_service.is_translation_needed(detected_language, confidence):
                final_response = self.translation_service.translate_response_to_user_language(
                    english_response, detected_language
                )
            else:
                final_response = english_response
            
            return final_response
        
        except Exception as e:
            print(f"Error processing query: {e}")
            traceback.print_exc()
            # Return localized error message
            return self.language_service.translate_error_message(
                "Sorry, there was an error processing your question. Please try again.",
                detected_language if 'detected_language' in locals() else 'en'
            )
    
    def _handle_general_query(self, english_message: str, organization: Dict, query_type: str) -> str:
        """Handle general queries without document context"""
        base_prompt = organization.get("prompt") or self.prompt_service.get_default_prompt("general_assistant")
        
        # Create English-only prompt for processing
        system_prompt = f"""{base_prompt}

Organization: {organization["name"]}
Available Documents: {len(organization.get("documents", []))}
Context Type: general

You are a helpful AI assistant. You can answer both document-related questions (when context is provided) and general questions. Be helpful, polite, and informative.

{"No documents are available in this organization yet." if not organization.get("documents") else "This is a general query not related to specific documents."}
"""
        
        return self.openai_service.generate_response(
            system_prompt=system_prompt,
            user_message=english_message,
            context="",
            is_document_query=False
        )
    
    def _handle_document_query(self, english_message: str, organization: Dict, documents: List[Dict]) -> str:
        """Handle document-specific queries using RAG (in English)"""
        try:
            # Ensure documents have embeddings
            organization_id = organization["id"]
            documents = self.embedding_service.update_document_embeddings(documents, organization_id)
            
            # Get query embedding (for English query)
            query_embedding = self.openai_service.get_single_embedding(english_message)
            if not query_embedding:
                return self._fallback_keyword_search(english_message, organization, documents, organization_id)
            
            # Search for similar chunks using ChromaDB
            similar_chunks = self.embedding_service.search_similar_chunks(
                query_embedding=query_embedding,
                organization_id=organization_id,
                top_k=5
            )
            
            if not similar_chunks:
                print("No similar chunks found in ChromaDB, falling back to keyword search")
                return self._fallback_keyword_search(english_message, organization, documents, organization_id)
            
            # Prepare context from similar chunks
            context = self._prepare_context_from_chunks(similar_chunks)
            
            # Generate response in English
            base_prompt = organization.get("prompt") or self.prompt_service.get_default_prompt("document_assistant")
            system_prompt = f"""{base_prompt}

Organization: {organization["name"]}
Available Documents: {len(documents)}
Context Type: document

Based on the following document excerpts, please answer the user's question. If the answer cannot be found in the provided documents, please say so clearly and offer to help with general questions.

Document Context:
{context}

Instructions:
- Answer based on the provided context when possible
- If the context doesn't contain relevant information, acknowledge this
- Be helpful and polite in your responses
- You can also answer general questions outside of the document context
"""
            
            return self.openai_service.generate_response(
                system_prompt=system_prompt,
                user_message=english_message,
                context=context,
                is_document_query=True
            )
        
        except Exception as e:
            print(f"Error in document query processing: {e}")
            return self._fallback_keyword_search(english_message, organization, documents, organization.get("id"))
    
    def _fallback_keyword_search(self, english_message: str, organization: Dict, documents: List[Dict], organization_id: str = None) -> str:
        """Fallback to keyword-based search when embeddings fail"""
        print("Using fallback keyword search")
        
        # Simple keyword matching
        query_words = set(english_message.lower().split())
        relevant_chunks = []
        
        for doc in documents:
            chunks = doc.get("chunks", [])
            for i, chunk in enumerate(chunks):
                chunk_words = set(chunk.lower().split())
                score = len(query_words.intersection(chunk_words))
                
                if score > 0:
                    relevant_chunks.append({
                        "text": chunk,
                        "document_name": doc["filename"],
                        "score": score
                    })
        
        # Sort by score and take top chunks
        relevant_chunks.sort(key=lambda x: x["score"], reverse=True)
        top_chunks = relevant_chunks[:3]
        
        if not top_chunks:
            # No relevant content found
            context = "No relevant information found in the uploaded documents."
        else:
            context = "\n\n---\n\n".join([
                f"[From {chunk['document_name']}]\n{chunk['text']}"
                for chunk in top_chunks
            ])
        
        base_prompt = organization.get("prompt") or self.prompt_service.get_default_prompt("document_assistant")
        system_prompt = f"""{base_prompt}

Organization: {organization["name"]}
Available Documents: {len(documents)}
Context Type: document

Based on the following document excerpts, please answer the user's question. If the answer cannot be found in the provided documents, please say so clearly and offer to help with general questions.

Document Context:
{context}

Instructions:
- Answer based on the provided context when possible
- If the context doesn't contain relevant information, acknowledge this
- Be helpful and polite in your responses
- You can also answer general questions outside of the document context
"""
        
        return self.openai_service.generate_response(
            system_prompt=system_prompt,
            user_message=english_message,
            context=context,
            is_document_query=True
        )
            base_prompt, 
            organization["name"], 
            len(organization.get("documents", [])),
            "general",
            user_language,
            language_confidence
        )
        
        if query_type == "general":
            context = "This is a general query not related to specific documents."
        else:
            context = "No documents are available in this organization yet."
        
        return self.openai_service.generate_response(
            system_prompt=system_prompt,
            user_message=message,
            context=context,
            is_document_query=False
        )
    
    def _handle_document_query(self, message: str, organization: Dict, documents: List[Dict], user_language: str = "en", language_confidence: float = 0.8) -> str:
        """Handle document-specific queries using RAG"""
        try:
            # Ensure documents have embeddings
            organization_id = organization["id"]
            documents = self.embedding_service.update_document_embeddings(documents, organization_id)
            
            # Get query embedding
            query_embedding = self.openai_service.get_single_embedding(message)
            if not query_embedding:
                return self._fallback_keyword_search(message, organization, documents, organization_id, user_language, language_confidence)
            
            # Search for similar chunks using ChromaDB
            similar_chunks = self.embedding_service.search_similar_chunks(
                query_embedding=query_embedding,
                organization_id=organization_id,
                top_k=5
            )
            
            if not similar_chunks:
                print("No similar chunks found in ChromaDB, falling back to keyword search")
                return self._fallback_keyword_search(message, organization, documents, organization_id, user_language, language_confidence)
            
            # Prepare context from similar chunks
            context = self._prepare_context_from_chunks(similar_chunks)
            
            # Generate response
            base_prompt = organization.get("prompt") or self.prompt_service.get_default_prompt("document_assistant")
            system_prompt = self.prompt_service.create_contextual_prompt(
                base_prompt,
                organization["name"],
                len(documents),
                "document",
                user_language,
                language_confidence
            )
            
            return self.openai_service.generate_response(
                system_prompt=system_prompt,
                user_message=message,
                context=context,
                is_document_query=True
            )
        
        except Exception as e:
            print(f"Error in document query processing: {e}")
            return self._fallback_keyword_search(message, organization, documents, organization.get("id"), user_language, language_confidence)
    
    def _fallback_keyword_search(self, message: str, organization: Dict, documents: List[Dict], organization_id: str = None, user_language: str = "en", language_confidence: float = 0.8) -> str:
        """Fallback to keyword-based search when embeddings fail"""
        print("Using fallback keyword search")
        
        # Simple keyword matching
        query_words = set(message.lower().split())
        relevant_chunks = []
        
        for doc in documents:
            chunks = doc.get("chunks", [])
            for i, chunk in enumerate(chunks):
                chunk_words = set(chunk.lower().split())
                score = len(query_words.intersection(chunk_words))
                
                if score > 0:
                    relevant_chunks.append({
                        "text": chunk,
                        "document_name": doc["filename"],
                        "score": score
                    })
        
        # Sort by score and take top chunks
        relevant_chunks.sort(key=lambda x: x["score"], reverse=True)
        top_chunks = relevant_chunks[:3]
        
        if not top_chunks:
            # No relevant content found
            context = "No relevant information found in the uploaded documents."
        else:
            context = "\n\n---\n\n".join([
                f"[From {chunk['document_name']}]\n{chunk['text']}"
                for chunk in top_chunks
            ])
        
        base_prompt = organization.get("prompt") or self.prompt_service.get_default_prompt("document_assistant")
        system_prompt = self.prompt_service.create_contextual_prompt(
            base_prompt,
            organization["name"],
            len(documents),
            "document",
            user_language,
            language_confidence
        )
        
        return self.openai_service.generate_response(
            system_prompt=system_prompt,
            user_message=message,
            context=context,
            is_document_query=True
        )
    
    def _prepare_context_from_chunks(self, similar_chunks: List[Dict]) -> str:
        """Prepare context string from similar chunks"""
        context_parts = []
        
        for chunk in similar_chunks:
            similarity_score = chunk.get('similarity', 0)
            document_name = chunk.get('document_name', 'Unknown Document')
            chunk_index = chunk.get('chunk_index', 0)
            text = chunk.get('text', '')
            
            context_part = f"[From {document_name} (chunk {chunk_index + 1}) - Relevance: {similarity_score:.2f}]\n{text}"
            context_parts.append(context_part)
        
        return "\n\n---\n\n".join(context_parts)
    
    def get_query_suggestions(self, organization: Dict) -> List[str]:
        """Generate query suggestions based on available documents"""
        documents = organization.get("documents", [])
        
        if not documents:
            return [
                "Hello! How can I help you today?",
                "What can you do?",
                "Tell me about this organization"
            ]
        
        # Generate suggestions based on document content
        suggestions = [
            "What information is available in the uploaded documents?",
            "Can you summarize the main topics covered?",
            "Search for specific information in the documents",
            f"What does the document '{documents[0]['filename']}' contain?",
        ]
        
        if len(documents) > 1:
            suggestions.append(f"Compare information between {documents[0]['filename']} and {documents[1]['filename']}")
        
        return suggestions