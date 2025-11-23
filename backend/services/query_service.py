from typing import List, Dict, Optional, Tuple
from .openai_service import OpenAIService
from .document_service import DocumentService
from .embedding_service import EmbeddingService
from .vector_service import VectorService
from .prompt_service import PromptService
from .retrieval_service import RetrievalService
from .query_understanding_service import QueryUnderstandingService
from .conversation_context_service import ConversationContextService
from .domain_filter_service import DomainFilterService
from .response_length_service import ResponseLengthService
from .escalation_service import EscalationService
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
        self.domain_filter = DomainFilterService()
        self.response_length = ResponseLengthService()
        self.escalation_service = EscalationService()

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

            # Check domain relevance
            relevance_check = self.domain_filter.is_query_relevant(message, organization)
            print(f"Domain relevance: {relevance_check['is_relevant']}, "
                  f"Category: {relevance_check['category']}, "
                  f"Confidence: {relevance_check['confidence']:.2f}")

            # If query is clearly off-topic, return redirect response
            if not relevance_check['is_relevant'] and relevance_check['confidence'] > 0.7:
                off_topic_response = self.domain_filter.get_off_topic_response(
                    message, organization, relevance_check
                )
                return {
                    "response": off_topic_response,
                    "conversation_id": conversation_id,
                    "query_type": "off_topic",
                    "sources": [],
                    "confidence_score": 0.0,
                    "off_topic": True,
                    "relevance_check": relevance_check
                }

            # Analyze query with enhanced understanding
            documents = organization.get("documents", [])
            print(f"QueryService: Processing query with {len(documents)} documents available")
            if not documents:
                print(f"WARNING: No documents found in organization! Organization ID: {org_id}")
                print(f"Organization keys: {list(organization.keys())}")
                print(f"Document count field: {organization.get('document_count', 'not set')}")
            
            query_analysis = self.query_understanding.analyze_query(
                message,
                conversation_history=conversation_history,
                available_documents=len(documents)
            )

            # Determine appropriate response length
            appropriate_length = self.response_length.determine_appropriate_length(
                message, query_analysis
            )
            print(f"Appropriate response length: {appropriate_length} tokens")

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

            print(f"Processing query - Documents available: {len(documents)}, Primary intent: {primary_intent}")
            
            # Check if this is a simple greeting that should always use general handler
            original_query_lower = message.lower().strip()
            is_greeting = any(original_query_lower == pattern or original_query_lower.startswith(pattern + ' ') 
                            for pattern in ['hey', 'hi', 'hello', 'greetings', 'good morning', 'good afternoon', 'good evening'])
            
            # Domain-aware query routing
            # Determine if document handler should be used based on domain, intent, and documents
            use_document_handler = False if is_greeting else self._should_use_document_handler(
                query_analysis, organization, documents
            )
            
            if is_greeting:
                print("Detected greeting, using general query handler")
            
            if not documents or not use_document_handler:
                if not documents:
                    print("WARNING: No documents available, using general query handler")
                else:
                    print(f"Using general query handler (domain-aware routing decision)")
                response = self._handle_general_query(
                    query_to_process, organization, primary_intent, user_context, conversation_context, appropriate_length
                )
                confidence_score = 0.7
            else:
                # Handle document-specific queries with RAG
                print(f"Using document query handler with {len(documents)} documents (intent: {primary_intent})")
                # Pass both original and enhanced query - use enhanced for embedding search
                response, sources, confidence_score = self._handle_document_query(
                    query_to_process, organization, documents, user_context, conversation_context, query_analysis, appropriate_length, original_query=message
                )

            # Check if escalation is needed
            escalation_check = self.escalation_service.should_escalate(
                query=message,
                confidence_score=confidence_score,
                sources=sources,
                query_analysis=query_analysis
            )

            print(f"Escalation check: should_escalate={escalation_check['should_escalate']}, "
                  f"urgency={escalation_check['urgency']}")

            # If escalation is needed, modify response
            if escalation_check['should_escalate']:
                escalation_response = self.escalation_service.create_escalation_response(
                    escalation_check, organization
                )

                # Append escalation message to the original response
                if confidence_score > 0.3:
                    response = f"{response}\n\n{escalation_response}"
                else:
                    response = escalation_response

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
                        "is_follow_up": query_analysis['follow_up']['is_follow_up'],
                        "escalated": escalation_check['should_escalate'],
                        "escalation_reasons": escalation_check.get('escalation_reasons', [])
                    }
                )

            return {
                "response": response,
                "conversation_id": conversation_id,
                "query_type": primary_intent,
                "sources": sources,
                "confidence_score": confidence_score,
                "query_analysis": query_analysis,
                "escalation": escalation_check if escalation_check['should_escalate'] else None
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

    def _handle_general_query(self, message: str, organization: Dict, query_type: str, user_context: Dict = None, conversation_context: str = "", max_tokens: int = 250) -> str:
        """Handle general queries without document context"""
        try:
            base_prompt = organization.get("prompt") or self.prompt_service.get_default_prompt("customer_support")

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

            # Add length instruction
            length_instruction = self.response_length.create_length_instruction(max_tokens)
            system_prompt += length_instruction

            # Add domain info if available
            org_domain = organization.get('domain', '')
            org_industry = organization.get('industry', '')
            if org_domain or org_industry:
                domain_info = f"\n\nOrganization domain/industry: {org_domain or org_industry}"
                domain_info += "\nREMINDER: Only answer questions related to this domain. Politely redirect off-topic questions."
                system_prompt += domain_info

            response = self.openai_service.generate_response(
                system_prompt=system_prompt,
                user_message=message,
                context="",
                is_document_query=False,
                max_tokens=max_tokens
            )
            
            # Ensure we always return a response
            if not response or response.strip() == "":
                return f"Hello! How can I assist you with {organization.get('name', 'your organization')} today?"
            
            return response
        except Exception as e:
            print(f"Error in general query handler: {e}")
            import traceback
            traceback.print_exc()
            # Fallback response
            return f"Hello! How can I assist you with {organization.get('name', 'your organization')} today?"

    def _handle_document_query(self, message: str, organization: Dict, documents: List[Dict], user_context: Dict = None, conversation_context: str = "", query_analysis: Dict = None, max_tokens: int = 400, original_query: str = None) -> Tuple[str, List[Dict], float]:
        """Handle document-specific queries using enhanced RAG - returns (response, sources, confidence)"""
        try:
            # Use provided query analysis or analyze query complexity
            if not query_analysis:
                query_analysis = {'intent': {'primary_intent': 'general_inquiry'}}

            # Check for document/policy listing queries (count, list, enumerate)
            message_lower = message.lower()
            count_keywords = ['how many', 'count', 'number of', 'total number', 'how much']
            list_keywords = ['list', 'show', 'enumerate', 'all of them', 'all of', 'what are', 'what are the']
            is_count_query = any(keyword in message_lower for keyword in count_keywords)
            is_list_query = any(keyword in message_lower for keyword in list_keywords)
            
            # Check for policy-related terms (including variations)
            policy_terms = ['document', 'policy', 'policies', 'file', 'files', 'it policy', 'it policies', 'them']
            has_policy_term = any(term in message_lower for term in policy_terms)
            
            # Handle count queries
            if is_count_query and has_policy_term:
                doc_count = len(documents)
                # Filter documents that match the query (e.g., "IT policies")
                if 'policy' in message_lower or 'policies' in message_lower:
                    # Count policy documents
                    policy_docs = [d for d in documents if 'policy' in d.get('filename', '').lower()]
                    count = len(policy_docs)
                    doc_list = [d.get('filename', 'Unknown') for d in policy_docs[:10]]  # First 10 for context
                    
                    if count > 0:
                        response = f"There are {count} IT policy document(s) available."
                        if count <= 10:
                            response += f" They are: {', '.join(doc_list)}"
                        else:
                            response += f" Some examples: {', '.join(doc_list[:5])}, and {count - 5} more."
                        
                        sources = [{"document_id": d.get("id"), "document_name": d.get("filename")} for d in policy_docs[:5]]
                        return response, sources, 0.9
                    else:
                        response = f"There are {doc_count} total documents available, but no specific policy documents were found matching your query."
                        return response, [], 0.7
                else:
                    # General document count
                    response = f"There are {doc_count} document(s) available in the knowledge base."
                    sources = [{"document_id": d.get("id"), "document_name": d.get("filename")} for d in documents[:5]]
                    return response, sources, 0.9
            
            # Handle list/enumeration queries about documents/policies
            if is_list_query and (has_policy_term or 'them' in message_lower or 'all' in message_lower):
                # Check conversation context to understand what "them" refers to
                previous_context_mentions_policies = False
                if conversation_context:
                    context_lower = conversation_context.lower()
                    previous_context_mentions_policies = any(term in context_lower for term in ['policy', 'policies', 'it policy'])
                
                # Determine if we should list policies or all documents
                should_list_policies = (
                    'policy' in message_lower or 
                    'policies' in message_lower or 
                    'it policy' in message_lower or
                    (('them' in message_lower or 'all' in message_lower) and previous_context_mentions_policies)
                )
                
                # Check if it's asking for all policies/documents
                if 'all' in message_lower or 'them' in message_lower or 'list' in message_lower:
                    if should_list_policies:
                        # Filter policy documents
                        policy_docs = [d for d in documents if 'policy' in d.get('filename', '').lower()]
                        if policy_docs:
                            # Create a numbered list of all policy documents
                            doc_list = []
                            for i, doc in enumerate(policy_docs, 1):
                                doc_name = doc.get('filename', 'Unknown Document')
                                doc_list.append(f"{i}. {doc_name}")
                            
                            response = f"Here are all {len(policy_docs)} IT policy documents:\n\n" + "\n".join(doc_list)
                            sources = [{"document_id": d.get("id"), "document_name": d.get("filename"), "similarity": 1.0} for d in policy_docs]
                            return response, sources, 0.95
                    else:
                        # List all documents
                        doc_list = []
                        for i, doc in enumerate(documents, 1):
                            doc_name = doc.get('filename', 'Unknown Document')
                            doc_list.append(f"{i}. {doc_name}")
                        
                        response = f"Here are all {len(documents)} documents in the knowledge base:\n\n" + "\n".join(doc_list)
                        sources = [{"document_id": d.get("id"), "document_name": d.get("filename"), "similarity": 1.0} for d in documents]
                        return response, sources, 0.95

            complexity_analysis = self.retrieval_service.analyze_query_complexity(message)
            print(f"Complexity analysis: {complexity_analysis}")

            # Calculate adaptive retrieval parameters
            retrieval_params = self.retrieval_service.calculate_adaptive_parameters(complexity_analysis)
            print(f"Adaptive parameters: top_k={retrieval_params['top_k']}, threshold={retrieval_params['similarity_threshold']}")

            # Ensure documents have embeddings
            organization_id = organization["id"]
            documents = self.embedding_service.update_document_embeddings(documents, organization_id)

            # Get query embedding - clean up the query first
            # Use original query if available, otherwise use the enhanced query
            import re
            
            # Clean up malformed queries (remove duplicate words, clean up context markers)
            query_for_embedding = original_query if original_query else message
            
            # If the enhanced query has a resolved context prefix, extract the actual query part
            # Format: "[Referring to: IT policies] how many are they?"
            if "[Referring to:" in query_for_embedding:
                # Extract the entity and the query
                match = re.search(r'\[Referring to: ([^\]]+)\]\s*(.+)', query_for_embedding)
                if match:
                    entity = match.group(1).strip()
                    query_part = match.group(2).strip()
                    # Clean up query part - remove duplicate words
                    query_words = query_part.split()
                    # Remove consecutive duplicates
                    cleaned_words = []
                    prev_word = None
                    for word in query_words:
                        if word.lower() != prev_word:
                            cleaned_words.append(word)
                            prev_word = word.lower()
                    query_part = ' '.join(cleaned_words)
                    # Use the entity + cleaned query for better semantic search
                    query_for_embedding = f"{entity} {query_part}".strip()
                    print(f"Extracted and cleaned query for embedding: {query_for_embedding[:100]}...")
            
            # Additional cleanup: remove common stop words that might cause issues
            # Remove "today" if it appears multiple times or at the end
            query_for_embedding = re.sub(r'\btoday\b\s+\btoday\b', 'today', query_for_embedding, flags=re.IGNORECASE)
            query_for_embedding = re.sub(r'\s+\btoday\s*$', '', query_for_embedding, flags=re.IGNORECASE)
            
            # Remove duplicate consecutive words
            words = query_for_embedding.split()
            cleaned_words = []
            prev_word = None
            for word in words:
                if word.lower() != prev_word:
                    cleaned_words.append(word)
                    prev_word = word.lower()
            query_for_embedding = ' '.join(cleaned_words).strip()
            
            query_embedding = self.openai_service.get_single_embedding(query_for_embedding)
            if not query_embedding:
                response = self._fallback_keyword_search(message, organization, documents, organization_id)
                return response, [], 0.3

            # Search for similar chunks using ChromaDB with adaptive top_k
            print(f"Searching ChromaDB for organization_id: {organization_id}, top_k: {retrieval_params['top_k']}")
            print(f"Query for embedding: {query_for_embedding[:100]}...")
            semantic_results = self.embedding_service.search_similar_chunks(
                query_embedding=query_embedding,
                organization_id=organization_id,
                top_k=retrieval_params['top_k']
            )
            print(f"ChromaDB search returned {len(semantic_results)} results")
            if semantic_results:
                print(f"Sample result: document_id={semantic_results[0].get('document_id', 'unknown')}, similarity={semantic_results[0].get('similarity', 0):.3f}")
            else:
                print("WARNING: No results from ChromaDB search!")
                print(f"Checking if documents have chunks...")
                for doc in documents[:3]:
                    chunks = doc.get("chunks", [])
                    print(f"  Document {doc.get('filename', 'unknown')}: {len(chunks)} chunks")

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
            print(f"Total chunks prepared: {len(all_chunks)} from {len(documents)} documents")

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
            
            # Log context for debugging
            if context and context.strip():
                print(f"Context prepared: {len(context)} characters, {len(final_results)} chunks")
                print(f"Sample context (first 200 chars): {context[:200]}...")
            else:
                print("WARNING: No context prepared from chunks! Context will be empty string.")
                context = ""  # Ensure it's empty string, not None

            # Generate response
            base_prompt = organization.get("prompt") or self.prompt_service.get_default_prompt("document_assistant")
            system_prompt = self.prompt_service.create_contextual_prompt(
                base_prompt=base_prompt,
                organization_name=organization["name"],
                document_count=len(documents),
                context_type="document"
            )

            # Add explicit RAG instruction at the top
            rag_instruction = f"""
=== RAG INSTRUCTIONS ===
You have access to {len(final_results)} relevant information passages retrieved from {len(documents)} documents.
Your response MUST be based EXCLUSIVELY on the information provided in the "Available Information" section below.
If the answer is not in the provided information, you MUST say you don't have that information.
DO NOT use general knowledge or make assumptions.
"""
            system_prompt = rag_instruction + system_prompt

            # Add structured conversation context
            if conversation_context:
                system_prompt += f"\n\n=== Conversation Context ===\n{conversation_context}"

            # Add retrieval quality info
            retrieval_info = f"\n\n=== Retrieval Metadata ===\nFound {len(final_results)} relevant passages (avg relevance: {confidence_score:.2f})\nQuery complexity: {complexity_analysis['complexity_level']}\nIntent: {query_analysis['intent']['primary_intent']}\nIs follow-up: {query_analysis.get('follow_up', {}).get('is_follow_up', False)}"
            system_prompt += retrieval_info

            # Add reference resolution guidance if needed
            if query_analysis.get('follow_up', {}).get('is_follow_up'):
                system_prompt += "\n\nNote: This is a follow-up question. Use the conversation context to understand references like 'it', 'that', 'the document', etc."

            # Add length instruction
            length_instruction = self.response_length.create_length_instruction(max_tokens)
            system_prompt += length_instruction

            # Add domain info if available
            org_domain = organization.get('domain', '')
            org_industry = organization.get('industry', '')
            if org_domain or org_industry:
                domain_info = f"\n\nOrganization domain/industry: {org_domain or org_industry}"
                domain_info += "\nREMINDER: Focus on information relevant to this domain."
                system_prompt += domain_info

            response = self.openai_service.generate_response(
                system_prompt=system_prompt,
                user_message=message,
                context=context,
                is_document_query=True,
                max_tokens=max_tokens
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

                # Handle similarity - ensure it's a valid number
                similarity = chunk.get('similarity', 0)
                if similarity is None or (isinstance(similarity, float) and (similarity != similarity)):  # Check for NaN
                    similarity = 1.0  # Default to 1.0 for direct document queries
                similarity = round(float(similarity), 2)
                
                sources.append({
                    "document_id": doc_id,
                    "document_name": chunk.get('document_name', 'Unknown Document'),
                    "pages": pages,
                    "page_display": page_display,
                    "similarity": similarity,
                    "chunk_preview": chunk.get('text', '')[:200] + "..." if len(chunk.get('text', '')) > 200 else chunk.get('text', '')
                })

        return sources

    def _should_use_document_handler(self, query_analysis: Dict, organization: Dict, documents: List[Dict]) -> bool:
        """Domain-aware decision on whether to use document handler"""
        if not documents:
            return False
        
        primary_intent = query_analysis.get('intent', {}).get('primary_intent', 'general_inquiry')
        original_query = query_analysis.get('original_query', '').lower().strip()
        domain = organization.get('domain', '').lower()
        industry = organization.get('industry', '').lower()
        
        # Never use document handler for simple greetings
        greeting_patterns = ['hey', 'hi', 'hello', 'greetings', 'good morning', 'good afternoon', 'good evening']
        if any(original_query == pattern or original_query.startswith(pattern + ' ') for pattern in greeting_patterns):
            return False
        
        # Domain-specific routing rules
        if domain in ['customer_support', 'helpdesk', 'support']:
            # Customer support: Use documents only for factual queries
            return primary_intent in ['factual_lookup', 'specific_value', 'procedural']
        
        elif domain in ['technical', 'documentation', 'knowledge_base', 'it_policies']:
            # Technical/knowledge base: Use documents for substantive queries, not greetings
            # Only skip for pure greetings or opinion requests
            if primary_intent == 'opinion_recommendation':
                return False
            # For general_inquiry, check if it's actually a substantive question
            if primary_intent == 'general_inquiry':
                # If it's just a greeting or very short, use general handler
                if len(original_query.split()) <= 2:
                    return False
            return True
        
        elif domain in ['legal', 'compliance', 'policies']:
            # Legal/compliance: Use documents for specific lookups
            return primary_intent in ['factual_lookup', 'specific_value', 'list_enumeration']
        
        # Default: Use documents for most queries when available
        # But skip for greetings and very short queries
        if len(original_query.split()) <= 2:
            return False
        return primary_intent != 'opinion_recommendation'

    def _fallback_keyword_search(self, message: str, organization: Dict, documents: List[Dict], organization_id: str = None) -> str:
        """Fallback to keyword-based search when embeddings fail"""
        print("Using fallback keyword search")

        # Check for count and list queries first
        message_lower = message.lower()
        count_keywords = ['how many', 'count', 'number of', 'total number']
        list_keywords = ['list', 'show', 'enumerate', 'all of them', 'all of', 'what are', 'what are the']
        is_count_query = any(keyword in message_lower for keyword in count_keywords)
        is_list_query = any(keyword in message_lower for keyword in list_keywords)
        
        # Check for policy-related terms (including variations)
        policy_terms = ['document', 'policy', 'policies', 'file', 'files', 'it policy', 'it policies', 'them']
        has_policy_term = any(term in message_lower for term in policy_terms)
        
        # Handle list queries - return directly without LLM processing
        if is_list_query and (has_policy_term or 'them' in message_lower or 'all' in message_lower):
            if 'policy' in message_lower or 'policies' in message_lower or 'it policy' in message_lower or 'them' in message_lower:
                policy_docs = [d for d in documents if 'policy' in d.get('filename', '').lower()]
                if policy_docs:
                    doc_list = []
                    for i, doc in enumerate(policy_docs, 1):
                        doc_name = doc.get('filename', 'Unknown Document')
                        doc_list.append(f"{i}. {doc_name}")
                    return f"Here are all {len(policy_docs)} IT policy documents:\n\n" + "\n".join(doc_list)
                else:
                    return f"There are {len(documents)} total documents available, but no specific policy documents were found."
            else:
                doc_list = []
                for i, doc in enumerate(documents, 1):
                    doc_name = doc.get('filename', 'Unknown Document')
                    doc_list.append(f"{i}. {doc_name}")
                return f"Here are all {len(documents)} documents in the knowledge base:\n\n" + "\n".join(doc_list)
        elif is_count_query and has_policy_term:
            # Handle count query directly
            if 'policy' in message_lower or 'policies' in message_lower or 'it policy' in message_lower:
                policy_docs = [d for d in documents if 'policy' in d.get('filename', '').lower()]
                count = len(policy_docs)
                if count > 0:
                    doc_list = [d.get('filename', 'Unknown') for d in policy_docs[:10]]
                    context = f"There are {count} IT policy documents available. Document names: {', '.join(doc_list[:5])}"
                    if count > 5:
                        context += f" and {count - 5} more."
                else:
                    context = f"There are {len(documents)} total documents available, but no specific policy documents were found."
            else:
                context = f"There are {len(documents)} documents available in the knowledge base."
        else:
            # Simple keyword matching
            # Remove stop words for better matching
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'how', 'many', 'what', 'when', 'where', 'why'}
            query_words = set(message_lower.split()) - stop_words
            
            # If query is too short after removing stop words, use all words
            if len(query_words) == 0:
                query_words = set(message_lower.split())
            
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
                    # Calculate score: exact matches + partial matches
                    exact_matches = len(query_words.intersection(chunk_words))
                    # Also check for partial word matches
                    partial_matches = sum(1 for qw in query_words if any(qw in cw or cw in qw for cw in chunk_words))
                    score = exact_matches * 2 + partial_matches

                    if score > 0:
                        relevant_chunks.append({
                            "text": chunk_text,
                            "document_name": doc["filename"],
                            "score": score
                        })

            # Sort by score and take top chunks
            relevant_chunks.sort(key=lambda x: x["score"], reverse=True)
            top_chunks = relevant_chunks[:5]  # Get more chunks for better context

            if not top_chunks:
                # No relevant content found - provide document count as fallback
                context = f"No specific information found matching your query. However, there are {len(documents)} documents available in the knowledge base."
            else:
                context = "\n\n---\n\n".join([
                    f"[From {chunk['document_name']}]\n{chunk['text'][:500]}"  # Limit chunk length
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
