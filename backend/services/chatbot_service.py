"""
Modern Chatbot Service
Handles intelligent query routing, retrieval, and response generation
"""
from typing import List, Dict, Optional, Tuple
import re
import random
from .openai_service import OpenAIService
from .embedding_service import EmbeddingService
from .vector_service import VectorService
from .query_classifier import QueryClassifier
from .retrieval_service import RetrievalService
from .prompt_service import PromptService
from models.conversation import ConversationModel
import traceback

class ChatbotService:
    def __init__(
        self,
        openai_service: OpenAIService,
        embedding_service: EmbeddingService,
        vector_service: VectorService,
        prompt_service: PromptService
    ):
        self.openai_service = openai_service
        self.embedding_service = embedding_service
        self.vector_service = vector_service
        self.query_classifier = QueryClassifier()
        self.retrieval_service = RetrievalService()
        self.prompt_service = prompt_service
        self.conversation_model = ConversationModel()
    
    def process_query(
        self,
        message: str,
        organization: Dict,
        user_context: Dict = None,
        conversation_id: str = None
    ) -> Dict:
        """
        Main entry point for processing user queries
        Intelligently routes between general and document-specific queries
        """
        try:
            org_id = organization.get("id")
            user_id = user_context.get("user_id") if user_context else None
            documents = organization.get("documents", [])
            
            # Get conversation history
            conversation_history = []
            if conversation_id:
                messages = self.conversation_model.get_messages(conversation_id, limit=10)
                conversation_history = messages
            
            # Classify query
            classification = self.query_classifier.classify(
                query=message,
                has_documents=len(documents) > 0,
                conversation_history=conversation_history
            )
            
            # Create or get conversation
            if not conversation_id and user_id:
                conversation = self.conversation_model.create_conversation(
                    organization_id=org_id,
                    user_id=user_id,
                    title=message[:50] + "..." if len(message) > 50 else message
                )
                conversation_id = conversation["id"]
            elif conversation_id:
                conversation = self.conversation_model.get_conversation(conversation_id)
            
            # Add user message to conversation
            if conversation_id:
                self.conversation_model.add_message(
                    conversation_id=conversation_id,
                    role="user",
                    content=message,
                    metadata={"classification": classification}
                )
            
            # Route to appropriate handler
            if classification['type'] == 'general' or not documents:
                response = self._handle_general_query(
                    message=message,
                    organization=organization,
                    conversation_history=conversation_history
                )
                sources = []
                confidence = 0.8
            else:
                # Document-specific query
                response, sources, confidence = self._handle_document_query(
                    message=message,
                    organization=organization,
                    documents=documents,
                    conversation_history=conversation_history
                )
            
            # Generate follow-up question to help users go deeper
            follow_up_question = self._generate_follow_up_question(
                response=response,
                query_type=classification['type'],
                has_sources=len(sources) > 0,
                message=message
            )
            
            # Append follow-up question to response
            if follow_up_question:
                response = f"{response}\n\n{follow_up_question}"
            
            # Add assistant response to conversation
            if conversation_id:
                self.conversation_model.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=response,
                    metadata={
                        "query_type": classification['type'],
                        "sources": sources,
                        "confidence": confidence
                    }
                )
            
            return {
                "response": response,
                "conversation_id": conversation_id,
                "query_type": classification['type'],
                "sources": sources,
                "confidence_score": confidence,
                "classification": classification
            }
        
        except Exception as e:
            print(f"Error processing query: {e}")
            traceback.print_exc()
            return {
                "response": "I apologize, but I encountered an error processing your question. Please try again.",
                "conversation_id": conversation_id if 'conversation_id' in locals() else None,
                "query_type": "error",
                "sources": [],
                "confidence_score": 0.0
            }
    
    def _handle_general_query(
        self,
        message: str,
        organization: Dict,
        conversation_history: List[Dict]
    ) -> str:
        """Handle general queries (greetings, general questions)"""
        try:
            # Get organization prompt or default
            base_prompt = organization.get("prompt") or self.prompt_service.get_default_prompt("customer_support")
            
            # Build system prompt
            system_prompt = self.prompt_service.create_contextual_prompt(
                base_prompt=base_prompt,
                organization_name=organization["name"],
                document_count=len(organization.get("documents", [])),
                context_type="general"
            )
            
            # Add conversation context if available
            if conversation_history:
                context_parts = []
                for msg in conversation_history[-3:]:  # Last 3 messages
                    role = msg.get('role', '')
                    content = msg.get('content', '')
                    if role == 'user':
                        context_parts.append(f"User: {content}")
                    elif role == 'assistant':
                        context_parts.append(f"Assistant: {content[:200]}...")  # Truncate long responses
                
                if context_parts:
                    system_prompt += f"\n\nPrevious conversation:\n" + "\n".join(context_parts)
            
            # Generate response
            response = self.openai_service.generate_response(
                system_prompt=system_prompt,
                user_message=message,
                context="",
                is_document_query=False,
                max_tokens=500
            )
            
            return response if response else f"Hello! How can I help you with {organization.get('name', 'your organization')} today?"
        
        except Exception as e:
            print(f"Error in general query handler: {e}")
            return f"Hello! How can I help you with {organization.get('name', 'your organization')} today?"
    
    def _handle_document_query(
        self,
        message: str,
        organization: Dict,
        documents: List[Dict],
        conversation_history: List[Dict]
    ) -> Tuple[str, List[Dict], float]:
        """Handle document-specific queries with RAG"""
        try:
            # Check for metadata queries (how many, list all) - answer directly from index
            metadata_response = self._handle_metadata_query(message, documents, conversation_history)
            if metadata_response:
                return metadata_response
            
            org_id = organization.get("id")
            
            # Generate query embedding
            query_embedding = self.embedding_service.generate_single_embedding(message)
            if not query_embedding:
                # Fallback to keyword search
                return self._fallback_response(message, organization, documents), [], 0.3
            
            # Search vector database
            semantic_results = self.vector_service.search_similar_chunks(
                organization_id=org_id,
                query_embedding=query_embedding,
                top_k=10,
                min_similarity=0.3
            )
            
            # Prepare all chunks for hybrid search
            all_chunks = []
            for doc in documents:
                chunks = doc.get("chunks", [])
                for i, chunk in enumerate(chunks):
                    chunk_text = chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
                    all_chunks.append({
                        'chunk_id': f"{doc.get('id', '')}_{i}",
                        'text': chunk_text,
                        'document_id': doc.get('id', ''),
                        'document_name': doc.get('filename', ''),
                        'chunk_index': i,
                        'pages': chunk.get('pages', []) if isinstance(chunk, dict) else []
                    })
            
            # Perform hybrid search
            hybrid_results = self.retrieval_service.hybrid_search(
                semantic_results=semantic_results,
                query=message,
                all_chunks=all_chunks
            )
            
            # Rerank results
            reranked_results = self.retrieval_service.rerank_results(hybrid_results, message)
            
            # Filter by threshold
            filtered_results = self.retrieval_service.filter_by_threshold(reranked_results, threshold=0.3)
            
            # Diversify results
            final_results = self.retrieval_service.diversify_results(filtered_results, max_per_document=3)
            
            if not final_results:
                return self._fallback_response(message, organization, documents), [], 0.3
            
            # Extract sources
            sources = self._extract_sources(final_results)
            
            # Calculate confidence
            confidence = self._calculate_confidence(final_results)
            
            # Prepare context from results
            context = self._prepare_context(final_results)
            
            # Generate response
            base_prompt = organization.get("prompt") or self.prompt_service.get_default_prompt("document_assistant")
            system_prompt = self.prompt_service.create_contextual_prompt(
                base_prompt=base_prompt,
                organization_name=organization["name"],
                document_count=len(documents),
                context_type="document"
            )
            
            # Add conversation context
            if conversation_history:
                context_parts = []
                for msg in conversation_history[-2:]:  # Last 2 messages
                    role = msg.get('role', '')
                    content = msg.get('content', '')
                    if role == 'user':
                        context_parts.append(f"User previously asked: {content}")
                    elif role == 'assistant':
                        context_parts.append(f"Assistant replied: {content[:150]}...")
                
                if context_parts:
                    system_prompt += f"\n\nPrevious conversation:\n" + "\n".join(context_parts)
            
            response = self.openai_service.generate_response(
                system_prompt=system_prompt,
                user_message=message,
                context=context,
                is_document_query=True,
                max_tokens=800
            )
            
            return response, sources, confidence
        
        except Exception as e:
            print(f"Error in document query handler: {e}")
            traceback.print_exc()
            return self._fallback_response(message, organization, documents), [], 0.3
    
    def _extract_sources(self, results: List[Dict]) -> List[Dict]:
        """Extract source citations from results"""
        sources = []
        seen_docs = set()
        
        for result in results:
            doc_id = result.get('document_id', '')
            if doc_id and doc_id not in seen_docs:
                seen_docs.add(doc_id)
                pages = result.get('pages', [])
                
                sources.append({
                    "document_id": doc_id,
                    "document_name": result.get('document_name', 'Unknown Document'),
                    "pages": pages,
                    "page_display": f"page {pages[0]}" if len(pages) == 1 else f"pages {pages[0]}-{pages[-1]}" if pages else "",
                    "similarity": round(result.get('final_score', result.get('similarity', 0.0)), 2)
                })
        
        return sources
    
    def _calculate_confidence(self, results: List[Dict]) -> float:
        """Calculate confidence score from results"""
        if not results:
            return 0.0
        
        # Weight by position and score
        total_score = 0.0
        for i, result in enumerate(results[:5]):
            score = result.get('final_score', result.get('similarity', 0.0))
            weight = 1.0 / (i + 1)  # Higher weight for top results
            total_score += score * weight
        
        # Normalize
        max_possible = sum(1.0 / (i + 1) for i in range(min(len(results), 5)))
        confidence = total_score / max_possible if max_possible > 0 else 0.0
        
        return min(confidence, 1.0)
    
    def _prepare_context(self, results: List[Dict]) -> str:
        """Prepare context string from results"""
        context_parts = []
        
        for result in results[:5]:  # Top 5 results
            text = result.get('text', '')
            doc_name = result.get('document_name', 'Unknown Document')
            pages = result.get('pages', [])
            score = result.get('final_score', result.get('similarity', 0.0))
            
            page_info = ""
            if pages:
                if len(pages) == 1:
                    page_info = f", Page {pages[0]}"
                else:
                    page_info = f", Pages {pages[0]}-{pages[-1]}"
            
            context_parts.append(
                f"[Source: {doc_name}{page_info} - Relevance: {score:.2f}]\n{text}"
            )
        
        return "\n\n---\n\n".join(context_parts)
    
    def _handle_metadata_query(
        self,
        message: str,
        documents: List[Dict],
        conversation_history: List[Dict]
    ) -> Optional[Tuple[str, List[Dict], float]]:
        """
        Handle metadata queries like "how many documents" or "list all documents"
        Answers directly from the document index without vector search
        """
        message_lower = message.lower().strip()
        
        # Patterns for count queries
        count_patterns = [
            r'how many\s+(?:document|file|policy|policies|pdf)',
            r'count\s+(?:the|all|all the)?\s*(?:document|file|policy|policies)',
            r'number of\s+(?:document|file|policy|policies)',
            r'total\s+(?:number|count)\s+of\s+(?:document|file|policy|policies)'
        ]
        
        # Patterns for list queries
        list_patterns = [
            r'list\s+(?:all|all the|the)?\s*(?:document|file|policy|policies)',
            r'show\s+(?:me\s+)?(?:all|all the|the)?\s*(?:document|file|policy|policies)',
            r'enumerate\s+(?:all|all the|the)?\s*(?:document|file|policy|policies)',
            r'what\s+(?:are|is)\s+(?:all|all the|the)?\s*(?:document|file|policy|policies)',
            r'name\s+(?:all|all the|the)?\s*(?:document|file|policy|policies)'
        ]
        
        # Check for count query
        is_count_query = any(re.search(pattern, message_lower) for pattern in count_patterns)
        is_list_query = any(re.search(pattern, message_lower) for pattern in list_patterns)
        
        # Check if query references policies specifically
        is_policy_query = 'policy' in message_lower or 'policies' in message_lower
        
        # Handle count queries
        if is_count_query:
            if is_policy_query:
                # Count policy documents
                policy_docs = [d for d in documents if 'policy' in d.get('filename', '').lower()]
                count = len(policy_docs)
                if count > 0:
                    # Always list all items when providing a count
                    doc_list = []
                    for i, doc in enumerate(policy_docs, 1):
                        doc_name = doc.get('filename', 'Unknown Document')
                        doc_list.append(f"{i}. {doc_name}")
                    
                    response = f"There are {count} IT policy document(s) available:\n\n" + "\n".join(doc_list)
                    sources = [{"document_id": d.get("id"), "document_name": d.get("filename")} for d in policy_docs]
                    return response, sources, 0.95
                else:
                    response = f"There are {len(documents)} total document(s) available, but no specific policy documents were found."
                    return response, [], 0.8
            else:
                # Count all documents - always list all when providing count
                count = len(documents)
                if count > 0:
                    doc_list = []
                    for i, doc in enumerate(documents, 1):
                        doc_name = doc.get('filename', 'Unknown Document')
                        doc_list.append(f"{i}. {doc_name}")
                    
                    response = f"There are {count} document(s) available in the knowledge base:\n\n" + "\n".join(doc_list)
                    sources = [{"document_id": d.get("id"), "document_name": d.get("filename")} for d in documents]
                    return response, sources, 0.95
                else:
                    response = "There are no documents available in the knowledge base."
                    return response, [], 0.9
        
        # Handle list queries
        if is_list_query:
            if is_policy_query:
                # List policy documents
                policy_docs = [d for d in documents if 'policy' in d.get('filename', '').lower()]
                if policy_docs:
                    doc_list = []
                    for i, doc in enumerate(policy_docs, 1):
                        doc_name = doc.get('filename', 'Unknown Document')
                        doc_list.append(f"{i}. {doc_name}")
                    
                    response = f"Here are all {len(policy_docs)} IT policy documents:\n\n" + "\n".join(doc_list)
                    sources = [{"document_id": d.get("id"), "document_name": d.get("filename"), "similarity": 1.0} for d in policy_docs]
                    return response, sources, 0.95
                else:
                    response = f"There are {len(documents)} total document(s) available, but no specific policy documents were found."
                    return response, [], 0.8
            else:
                # List all documents
                if documents:
                    doc_list = []
                    for i, doc in enumerate(documents, 1):
                        doc_name = doc.get('filename', 'Unknown Document')
                        doc_list.append(f"{i}. {doc_name}")
                    
                    response = f"Here are all {len(documents)} documents in the knowledge base:\n\n" + "\n".join(doc_list)
                    sources = [{"document_id": d.get("id"), "document_name": d.get("filename"), "similarity": 1.0} for d in documents]
                    return response, sources, 0.95
                else:
                    response = "There are no documents available in the knowledge base."
                    return response, [], 0.9
        
        # Check for follow-up references to "them" or "they" after a list/count query
        if conversation_history:
            recent_assistant = None
            for msg in reversed(conversation_history[-3:]):
                if msg.get('role') == 'assistant':
                    recent_assistant = msg.get('content', '').lower()
                    break
            
            if recent_assistant and ('policy' in recent_assistant or 'document' in recent_assistant):
                # Check if current query references "them", "they", "all of them", etc.
                reference_patterns = [
                    r'\b(?:list|show|enumerate|what are|name)\s+(?:all|all of)?\s*(?:them|they)',
                    r'how many\s+(?:are\s+)?(?:they|them)',
                    r'count\s+(?:them|they)'
                ]
                
                if any(re.search(pattern, message_lower) for pattern in reference_patterns):
                    # Determine if referring to policies or all documents
                    if 'policy' in recent_assistant:
                        policy_docs = [d for d in documents if 'policy' in d.get('filename', '').lower()]
                        if policy_docs:
                            doc_list = []
                            for i, doc in enumerate(policy_docs, 1):
                                doc_name = doc.get('filename', 'Unknown Document')
                                doc_list.append(f"{i}. {doc_name}")
                            response = f"Here are all {len(policy_docs)} IT policy documents:\n\n" + "\n".join(doc_list)
                            sources = [{"document_id": d.get("id"), "document_name": d.get("filename"), "similarity": 1.0} for d in policy_docs]
                            return response, sources, 0.95
                    else:
                        # List all documents
                        if documents:
                            doc_list = []
                            for i, doc in enumerate(documents, 1):
                                doc_name = doc.get('filename', 'Unknown Document')
                                doc_list.append(f"{i}. {doc_name}")
                            response = f"Here are all {len(documents)} documents:\n\n" + "\n".join(doc_list)
                            sources = [{"document_id": d.get("id"), "document_name": d.get("filename"), "similarity": 1.0} for d in documents]
                            return response, sources, 0.95
        
        return None
    
    def _is_metadata_query(self, message: str) -> bool:
        """Check if query is a metadata query (count/list) that already provides complete info"""
        message_lower = message.lower()
        metadata_patterns = [
            r'how many\s+(?:document|file|policy|policies)',
            r'count\s+(?:the|all|all the)?\s*(?:document|file|policy|policies)',
            r'list\s+(?:all|all the|the)?\s*(?:document|file|policy|policies)',
            r'show\s+(?:me\s+)?(?:all|all the|the)?\s*(?:document|file|policy|policies)',
            r'enumerate\s+(?:all|all the|the)?\s*(?:document|file|policy|policies)'
        ]
        return any(re.search(pattern, message_lower) for pattern in metadata_patterns)
    
    def _generate_follow_up_question(
        self,
        response: str,
        query_type: str,
        has_sources: bool,
        message: str
    ) -> str:
        """
        Generate a natural follow-up question to help users go deeper
        """
        message_lower = message.lower()
        response_lower = response.lower()
        
        # Determine context from the response
        is_count_response = 'there are' in response_lower and ('document' in response_lower or 'policy' in response_lower)
        is_list_response = 'here are' in response_lower or 'all' in response_lower and 'document' in response_lower
        is_detailed_response = len(response.split()) > 50
        is_short_response = len(response.split()) < 20
        
        # Generate contextually appropriate follow-ups
        follow_ups = []
        
        if is_count_response or is_list_response:
            # For count/list queries, offer to explain or get details
            follow_ups.extend([
                "Would you like me to explain what any of these documents contain?",
                "Would you like more details about any specific document?",
                "Would you like a summary of what these documents cover?"
            ])
        elif is_detailed_response:
            # For detailed responses, offer summary or breakdown
            follow_ups.extend([
                "Would you like a summary of this information?",
                "Would you like me to break this down into simpler terms?",
                "Would you like more details on any specific aspect?"
            ])
        elif is_short_response:
            # For short responses, offer more detail
            follow_ups.extend([
                "Would you like more details about this?",
                "Would you like me to explain this further?",
                "Would you like additional information on this topic?"
            ])
        else:
            # General follow-ups
            follow_ups.extend([
                "Would you like more details about this?",
                "Would you like me to explain any part of this further?",
                "Is there anything specific you'd like me to clarify?"
            ])
        
        # Add context-specific follow-ups based on query type
        if query_type == 'document' and has_sources:
            follow_ups.extend([
                "Would you like me to search for more information on this topic?",
                "Would you like details from other related documents?"
            ])
        elif query_type == 'general':
            follow_ups.extend([
                "Is there anything else I can help you with?",
                "Would you like to know more about our services?"
            ])
        
        # Select a random but appropriate follow-up
        selected = random.choice(follow_ups)
        
        return selected
    
    def _fallback_response(self, message: str, organization: Dict, documents: List[Dict]) -> str:
        """Fallback response when retrieval fails"""
        if not documents:
            return f"I don't have access to any documents for {organization.get('name', 'this organization')}. How can I help you?"
        
        return f"I couldn't find specific information about that in the available documents. There are {len(documents)} document(s) available. Could you rephrase your question or ask about something else?"

