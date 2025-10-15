from typing import List, Dict, Optional, Tuple
from .openai_service import OpenAIService
from .document_service import DocumentService
from .embedding_service import EmbeddingService
from .vector_service import VectorService
from .prompt_service import PromptService
from .retrieval_service import RetrievalService
from .query_understanding_service import QueryUnderstandingService
from .conversation_context_service import ConversationContextService
from models.conversation import ConversationModel
import traceback

class QueryService:
    def __init__(self, openai_service: OpenAIService, document_service: DocumentService, embedding_service: EmbeddingService, vector_service: VectorService, prompt_service: PromptService):
        self.openai_service = openai_service
        self.document_service = document_service
        self.embedding_service = embedding_service
        self.vector_service = vector_service
        self.prompt_service = prompt_service
        self.conversation_model = ConversationModel()
        self.retrieval_service = RetrievalService()
        self.query_understanding = QueryUnderstandingService()
        self.context_service = ConversationContextService()

    def process_query(self, message: str, organization: Dict, user_context: Dict = None, conversation_id: str = None) -> Dict:
        """Process user query with enhanced understanding and RAG"""
        try:
            org_id = organization.get("id")
            user_id = user_context.get("user_id") if user_context else None

            # Get conversation history for context
            conversation_history = []
            if conversation_id:
                messages = self.conversation_model.get_messages(conversation_id, limit=20)
                conversation_history = messages

            # Analyze query with enhanced understanding
            documents = organization.get("documents", [])
            query_analysis = self.query_understanding.analyze_query(
                message,
                conversation_history=conversation_history,
                available_documents=len(documents)
            )

            print(f"Query Analysis: Intent={query_analysis['intent']['primary_intent']}, "
                  f"Follow-up={query_analysis['follow_up']['is_follow_up']}, "
                  f"Ambiguous={query_analysis['ambiguity']['is_ambiguous']}")

            # Build structured conversation context
            conversation_context_data = self.context_service.get_relevant_context_for_query(
                messages=conversation_history,
                current_query=message,
                query_intent=query_analysis['intent']['primary_intent']
            )

            print(f"Context: {conversation_context_data['message_count']} msgs, "
                  f"References: {conversation_context_data['references']['has_references']}, "
                  f"Needs summary: {conversation_context_data['needs_summarization']}")

            # Generate conversation summary if needed
            if conversation_context_data['needs_summarization']:
                summary = self.context_service.summarize_conversation(
                    conversation_history,
                    self.openai_service
                )
                conversation_context_data['ai_summary'] = summary
                print(f"Generated summary: {summary[:100]}...")

            # Check if clarification is needed
            if query_analysis.get('needs_clarification'):
                clarification_prompt = query_analysis.get('clarification_prompt')
                return {
                    "response": clarification_prompt,
                    "conversation_id": conversation_id,
                    "query_type": "clarification_needed",
                    "sources": [],
                    "confidence_score": 0.0,
                    "needs_clarification": True,
                    "query_analysis": query_analysis
                }

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
            else:
                conversation = None

            # Add user message to conversation
            if conversation_id:
                self.conversation_model.add_message(
                    conversation_id=conversation_id,
                    role="user",
                    content=message,
                    metadata=self.query_understanding.get_query_metadata(query_analysis)
                )

            # Enhance query with context resolution
            query_to_process = self.context_service.enhance_query_with_context(
                message,
                conversation_context_data
            )
            print(f"Enhanced query: {query_to_process[:150]}...")

            # Prepare structured conversation context for LLM
            conversation_context = self.context_service.prepare_context_for_llm(
                conversation_context_data,
                include_summary=conversation_context_data.get('needs_summarization', False)
            )

            # Process the query
            sources = []
            confidence_score = 0.0
            primary_intent = query_analysis['intent']['primary_intent']

            if not documents or primary_intent in ['general_inquiry', 'opinion_recommendation']:
                # Handle general queries or no documents
                response = self._handle_general_query(
                    query_to_process, organization, primary_intent, user_context, conversation_context
                )
                confidence_score = 0.7
            else:
                # Handle document-specific queries with RAG
                response, sources, confidence_score = self._handle_document_query(
                    query_to_process, organization, documents, user_context, conversation_context, query_analysis
                )

            # Add assistant response to conversation
            if conversation_id:
                self.conversation_model.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=response,
                    metadata={
                        "query_type": primary_intent,
                        "sources": sources,
                        "confidence_score": confidence_score,
                        "intent_info": query_analysis['intent'],
                        "is_follow_up": query_analysis['follow_up']['is_follow_up']
                    }
                )

            return {
                "response": response,
                "conversation_id": conversation_id,
                "query_type": primary_intent,
                "sources": sources,
                "confidence_score": confidence_score,
                "query_analysis": query_analysis
            }

        except Exception as e:
            print(f"Error processing query: {e}")
            traceback.print_exc()
            return {
                "response": "Sorry, there was an error processing your question. Please try again.",
                "conversation_id": conversation_id if 'conversation_id' in locals() else None,
                "query_type": "error",
                "sources": [],
                "confidence_score": 0.0
            }

    def _handle_general_query(self, message: str, organization: Dict, query_type: str, user_context: Dict = None, conversation_context: str = "") -> str:
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
        if conversation_context:
            system_prompt += f"\n\nPrevious conversation context:\n{conversation_context}"

        return self.openai_service.generate_response(
            system_prompt=system_prompt,
            user_message=message,
            context="",
            is_document_query=False
        )

    def _handle_document_query(self, message: str, organization: Dict, documents: List[Dict], user_context: Dict = None, conversation_context: str = "", query_analysis: Dict = None) -> Tuple[str, List[Dict], float]:
        """Handle document-specific queries using enhanced RAG - returns (response, sources, confidence)"""
        try:
            # Use provided query analysis or analyze query complexity
            if not query_analysis:
                query_analysis = {'intent': {'primary_intent': 'general_inquiry'}}

            complexity_analysis = self.retrieval_service.analyze_query_complexity(message)
            print(f"Complexity analysis: {complexity_analysis}")

            # Calculate adaptive retrieval parameters
            retrieval_params = self.retrieval_service.calculate_adaptive_parameters(complexity_analysis)
            print(f"Adaptive parameters: top_k={retrieval_params['top_k']}, threshold={retrieval_params['similarity_threshold']}")

            # Ensure documents have embeddings
            organization_id = organization["id"]
            documents = self.embedding_service.update_document_embeddings(documents, organization_id)

            # Get query embedding
            query_embedding = self.openai_service.get_single_embedding(message)
            if not query_embedding:
                response = self._fallback_keyword_search(message, organization, documents, organization_id)
                return response, [], 0.3

            # Search for similar chunks using ChromaDB with adaptive top_k
            semantic_results = self.embedding_service.search_similar_chunks(
                query_embedding=query_embedding,
                organization_id=organization_id,
                top_k=retrieval_params['top_k']
            )

            if not semantic_results:
                print("No similar chunks found in ChromaDB, falling back to keyword search")
                response = self._fallback_keyword_search(message, organization, documents, organization_id)
                return response, [], 0.3

            # Prepare all chunks for hybrid search
            all_chunks = []
            for doc in documents:
                chunks = doc.get("chunks", [])
                for i, chunk in enumerate(chunks):
                    if isinstance(chunk, dict):
                        chunk_text = chunk.get("text", "")
                    else:
                        chunk_text = str(chunk)

                    all_chunks.append({
                        'text': chunk_text,
                        'document_id': doc.get('id', ''),
                        'document_name': doc.get('filename', ''),
                        'chunk_index': i,
                        'chunk_id': f"{doc.get('id', '')}_{i}",
                        'pages': chunk.get('pages', []) if isinstance(chunk, dict) else []
                    })

            # Perform hybrid search
            hybrid_results = self.retrieval_service.hybrid_search(
                semantic_results=semantic_results,
                query=message,
                all_chunks=all_chunks,
                keyword_weight=retrieval_params['keyword_weight']
            )

            print(f"Hybrid search returned {len(hybrid_results)} results")

            # Re-rank results
            reranked_results = self.retrieval_service.rerank_results(hybrid_results, complexity_analysis)

            # Apply dynamic threshold filtering
            filtered_results = self.retrieval_service.filter_by_dynamic_threshold(
                reranked_results,
                retrieval_params['similarity_threshold'],
                complexity_analysis
            )

            print(f"After filtering: {len(filtered_results)} results")

            # Diversify results to avoid over-representation from single document
            final_results = self.retrieval_service.diversify_results(filtered_results)

            print(f"Final results: {len(final_results)} chunks")

            if not final_results:
                print("No results after filtering, falling back")
                response = self._fallback_keyword_search(message, organization, documents, organization_id)
                return response, [], 0.3

            # Extract sources from final results
            sources = self._extract_sources(final_results)

            # Calculate weighted confidence score
            if final_results:
                # Weight by position (earlier results are more important)
                weighted_scores = []
                for i, chunk in enumerate(final_results[:5]):
                    position_weight = 1.0 / (i + 1)
                    weighted_scores.append(chunk.get('similarity', 0) * position_weight)
                confidence_score = sum(weighted_scores) / sum(1.0 / (i + 1) for i in range(len(weighted_scores)))
            else:
                confidence_score = 0

            # Prepare context from final results
            context = self._prepare_context_from_chunks(final_results)

            # Generate response
            base_prompt = organization.get("prompt") or self.prompt_service.get_default_prompt("document_assistant")
            system_prompt = self.prompt_service.create_contextual_prompt(
                base_prompt=base_prompt,
                organization_name=organization["name"],
                document_count=len(documents),
                context_type="document"
            )

            # Add structured conversation context
            if conversation_context:
                system_prompt += f"\n\n=== Conversation Context ===\n{conversation_context}"

            # Add retrieval quality info
            retrieval_info = f"\n\n=== Retrieval Metadata ===\nFound {len(final_results)} relevant passages (avg relevance: {confidence_score:.2f})\nQuery complexity: {complexity_analysis['complexity_level']}\nIntent: {query_analysis['intent']['primary_intent']}\nIs follow-up: {query_analysis.get('follow_up', {}).get('is_follow_up', False)}"
            system_prompt += retrieval_info

            # Add reference resolution guidance if needed
            if query_analysis.get('follow_up', {}).get('is_follow_up'):
                system_prompt += "\n\nNote: This is a follow-up question. Use the conversation context to understand references like 'it', 'that', 'the document', etc."

            response = self.openai_service.generate_response(
                system_prompt=system_prompt,
                user_message=message,
                context=context,
                is_document_query=True
            )

            return response, sources, confidence_score

        except Exception as e:
            print(f"Error in document query processing: {e}")
            traceback.print_exc()
            response = self._fallback_keyword_search(message, organization, documents, organization.get("id"))
            return response, [], 0.3

    def _extract_sources(self, similar_chunks: List[Dict]) -> List[Dict]:
        """Extract source citations from similar chunks"""
        sources = []
        seen_docs = set()

        for chunk in similar_chunks:
            doc_id = chunk.get('document_id')
            if doc_id not in seen_docs:
                seen_docs.add(doc_id)

                pages = chunk.get('pages', [])
                page_display = ""
                if pages:
                    if len(pages) == 1:
                        page_display = f"page {pages[0]}"
                    else:
                        page_display = f"pages {pages[0]}-{pages[-1]}"

                sources.append({
                    "document_id": doc_id,
                    "document_name": chunk.get('document_name', 'Unknown Document'),
                    "pages": pages,
                    "page_display": page_display,
                    "similarity": round(chunk.get('similarity', 0), 2),
                    "chunk_preview": chunk.get('text', '')[:200] + "..." if len(chunk.get('text', '')) > 200 else chunk.get('text', '')
                })

        return sources

    def _fallback_keyword_search(self, message: str, organization: Dict, documents: List[Dict], organization_id: str = None) -> str:
        """Fallback to keyword-based search when embeddings fail"""
        print("Using fallback keyword search")

        # Simple keyword matching
        query_words = set(message.lower().split())
        relevant_chunks = []

        for doc in documents:
            chunks = doc.get("chunks", [])
            for i, chunk in enumerate(chunks):
                # Handle both old and new chunk formats
                if isinstance(chunk, dict):
                    chunk_text = chunk.get("text", "")
                else:
                    chunk_text = str(chunk)

                chunk_words = set(chunk_text.lower().split())
                score = len(query_words.intersection(chunk_words))

                if score > 0:
                    relevant_chunks.append({
                        "text": chunk_text,
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
        """Prepare context string from similar chunks with source information"""
        context_parts = []

        for chunk in similar_chunks:
            similarity_score = chunk.get('similarity', 0)
            document_name = chunk.get('document_name', 'Unknown Document')
            chunk_index = chunk.get('chunk_index', 0)
            pages = chunk.get('pages', [])
            text = chunk.get('text', '')

            page_info = ""
            if pages:
                if len(pages) == 1:
                    page_info = f", Page {pages[0]}"
                else:
                    page_info = f", Pages {pages[0]}-{pages[-1]}"

            context_part = f"[Source: {document_name}{page_info} - Relevance: {similarity_score:.2f}]\n{text}"
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
