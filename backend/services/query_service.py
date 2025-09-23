from typing import List, Dict, Optional, Tuple
from .openai_service import OpenAIService
from .document_service import DocumentService
from .embedding_service import EmbeddingService
from .vector_service import VectorService
from .prompt_service import PromptService
import traceback

class ConversationContext:
    def __init__(self):
        self.conversations = {}  # org_id -> list of messages
        self.max_context_length = 10  # Keep last 10 exchanges
    
    def add_message(self, org_id: str, user_message: str, ai_response: str):
        if org_id not in self.conversations:
            self.conversations[org_id] = []
        
        self.conversations[org_id].append({
            'user': user_message,
            'assistant': ai_response,
            'timestamp': traceback.time.time() if hasattr(traceback, 'time') else 0
        })
        
        # Keep only recent messages
        if len(self.conversations[org_id]) > self.max_context_length:
            self.conversations[org_id] = self.conversations[org_id][-self.max_context_length:]
    
    def get_context(self, org_id: str) -> str:
        if org_id not in self.conversations or not self.conversations[org_id]:
            return ""
        
        context_parts = []
        for exchange in self.conversations[org_id][-5:]:  # Last 5 exchanges
            context_parts.append(f"User previously asked: {exchange['user']}")
            context_parts.append(f"You responded: {exchange['assistant']}")
        
        return "\n".join(context_parts)

class QueryService:
    def __init__(self, openai_service: OpenAIService, document_service: DocumentService, embedding_service: EmbeddingService, vector_service: VectorService, prompt_service: PromptService):
        self.openai_service = openai_service
        self.document_service = document_service
        self.embedding_service = embedding_service
        self.vector_service = vector_service
        self.prompt_service = prompt_service
        self.conversation_context = ConversationContext()
    
    def process_query(self, message: str, organization: Dict, user_context: Dict = None) -> str:
        """Process user query with RAG approach - GPT handles language naturally"""
        try:
            # Process query using RAG - GPT will handle language matching naturally
            query_type = self.openai_service.detect_query_type(message)
            print(f"Query type detected: {query_type}")
            
            # Get documents
            documents = organization.get("documents", [])
            
            # Process the query
            if not documents or query_type == "general":
                # Handle general queries or no documents
                response = self._handle_general_query(message, organization, query_type, user_context)
            else:
                # Handle document-specific queries with RAG
                response = self._handle_document_query(message, organization, documents, user_context)
            
            # Store conversation context
            org_id = organization.get("id")
            if org_id:
                self.conversation_context.add_message(org_id, message, response)
            
            return response
        
        except Exception as e:
            print(f"Error processing query: {e}")
            traceback.print_exc()
            return "Sorry, there was an error processing your question. Please try again."
    
    def _handle_general_query(self, message: str, organization: Dict, query_type: str, user_context: Dict = None) -> str:
        """Handle general queries without document context"""
        base_prompt = organization.get("prompt") or self.prompt_service.get_default_prompt("general_assistant")
        
        # Create contextual prompt
        system_prompt = self.prompt_service.create_contextual_prompt(
            base_prompt=base_prompt,
            organization_name=organization["name"],
            document_count=len(organization.get("documents", [])),
            context_type="general"
        )
        
        # Add conversation context
        conversation_context = self.conversation_context.get_context(organization.get("id", ""))
        if conversation_context:
            system_prompt += f"\n\nPrevious conversation context:\n{conversation_context}"
        
        return self.openai_service.generate_response(
            system_prompt=system_prompt,
            user_message=message,
            context="",
            is_document_query=False
        )
    
    def _handle_document_query(self, message: str, organization: Dict, documents: List[Dict], user_context: Dict = None) -> str:
        """Handle document-specific queries using RAG"""
        try:
            # Ensure documents have embeddings
            organization_id = organization["id"]
            documents = self.embedding_service.update_document_embeddings(documents, organization_id)
            
            # Get query embedding
            query_embedding = self.openai_service.get_single_embedding(message)
            if not query_embedding:
                return self._fallback_keyword_search(message, organization, documents, organization_id)
            
            # Search for similar chunks using ChromaDB
            similar_chunks = self.embedding_service.search_similar_chunks(
                query_embedding=query_embedding,
                organization_id=organization_id,
                top_k=5
            )
            
            if not similar_chunks:
                print("No similar chunks found in ChromaDB, falling back to keyword search")
                return self._fallback_keyword_search(message, organization, documents, organization_id)
            
            # Prepare context from similar chunks
            context = self._prepare_context_from_chunks(similar_chunks)
            
            # Generate response
            base_prompt = organization.get("prompt") or self.prompt_service.get_default_prompt("document_assistant")
            system_prompt = self.prompt_service.create_contextual_prompt(
                base_prompt=base_prompt,
                organization_name=organization["name"],
                document_count=len(documents),
                context_type="document"
            )
            
            # Add conversation context
            conversation_context = self.conversation_context.get_context(organization.get("id", ""))
            if conversation_context:
                system_prompt += f"\n\nPrevious conversation context:\n{conversation_context}"
            
            # Add conversation context
            conversation_context = self.conversation_context.get_context(organization_id)
            if conversation_context:
                system_prompt += f"\n\nPrevious conversation context:\n{conversation_context}"
            
            return self.openai_service.generate_response(
                system_prompt=system_prompt,
                user_message=message,
                context=context,
                is_document_query=True
            )
        
        except Exception as e:
            print(f"Error in document query processing: {e}")
            return self._fallback_keyword_search(message, organization, documents, organization.get("id"))
    
    def _fallback_keyword_search(self, message: str, organization: Dict, documents: List[Dict], organization_id: str = None) -> str:
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
            base_prompt=base_prompt,
            organization_name=organization["name"],
            document_count=len(documents),
            context_type="document"
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