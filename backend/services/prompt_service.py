import os
from typing import Dict, Optional
from datetime import datetime
from .language_service import LanguageService

class PromptService:
    def __init__(self):
        self.language_service = LanguageService()
        self.default_prompts = {
            "document_assistant": """You are a helpful AI assistant specialized in answering questions based on document content. 

Your capabilities:
- Answer questions using information from uploaded documents
- Provide accurate, contextual responses based on document content
- Handle both document-specific and general queries
- Maintain a professional and helpful tone

Guidelines:
- When answering from documents, cite the source document name
- If information isn't in the documents, clearly state this
- For general questions outside document scope, provide helpful general responses
- Always be polite and professional
- If unsure, ask for clarification rather than guessing""",

            "general_assistant": """You are a helpful AI assistant for the OpenChat platform.

Your role:
- Assist users with both document-related and general questions
- Provide accurate, helpful information
- Maintain a friendly and professional demeanor
- Guide users on how to use the platform effectively

Capabilities:
- Answer questions about uploaded documents using RAG (Retrieval-Augmented Generation)
- Provide general knowledge and assistance
- Help with platform navigation and features
- Offer suggestions for better document organization""",

            "customer_support": """You are a customer support AI assistant.

Your mission:
- Provide excellent customer service
- Answer questions based on company documentation
- Escalate complex issues appropriately
- Maintain a helpful and empathetic tone

Guidelines:
- Always greet customers warmly
- Use document content to provide accurate information
- If you can't find the answer in documents, offer to connect them with human support
- Be patient and understanding with customer concerns
- Provide step-by-step guidance when needed""",

            "knowledge_base": """You are a knowledge base assistant designed to help users find information quickly.

Your purpose:
- Search through organizational documents efficiently
- Provide comprehensive answers with source citations
- Organize information in a clear, structured way
- Help users discover related information

Best practices:
- Structure responses with clear headings and bullet points
- Include relevant document sections and page references when available
- Suggest related topics or documents that might be helpful
- Summarize complex information in digestible formats"""
        }
    
    def get_default_prompt(self, prompt_type: str = "document_assistant") -> str:
        """Get a default system prompt by type"""
        return self.default_prompts.get(prompt_type, self.default_prompts["document_assistant"])
    
    def get_available_prompt_types(self) -> Dict[str, str]:
        """Get all available prompt types with descriptions"""
        return {
            "document_assistant": "General document Q&A assistant",
            "general_assistant": "Platform-aware general assistant", 
            "customer_support": "Customer service focused assistant",
            "knowledge_base": "Knowledge base search assistant"
        }
    
    def create_contextual_prompt(self, base_prompt: str, organization_name: str, document_count: int, context_type: str = "document", user_language: str = "en", language_confidence: float = 0.8) -> str:
        """Create a contextual system prompt with organization details"""
        
        context_info = f"""
Organization: {organization_name}
Available Documents: {document_count}
Context Type: {context_type}
Current Date: {datetime.now().strftime('%Y-%m-%d')}
User Language: {user_language} (confidence: {language_confidence:.2f})
"""
        
        if context_type == "document" and document_count > 0:
            context_addition = f"""
You have access to {document_count} document(s) from {organization_name}. Use this information to provide accurate, contextual responses. When referencing information from documents, mention the source document name.
"""
        elif document_count == 0:
            context_addition = f"""
Note: {organization_name} hasn't uploaded any documents yet. You can still help with general questions and guide them on how to upload documents for more specific assistance.
"""
        else:
            context_addition = f"""
You are assisting users from {organization_name}. Provide helpful, accurate information while maintaining a professional tone.
"""
        
        # Add multilingual support
        multilingual_prompt = self.language_service.create_multilingual_prompt(base_prompt, user_language, language_confidence)
        
        return f"{multilingual_prompt}\n\n{context_addition}\n\nContext Information:{context_info}"
    
    def validate_prompt(self, prompt: str) -> Dict[str, any]:
        """Validate a system prompt for potential issues"""
        issues = []
        suggestions = []
        
        # Check length
        if len(prompt) < 50:
            issues.append("Prompt is very short - may not provide enough guidance")
        elif len(prompt) > 2000:
            issues.append("Prompt is very long - may hit token limits")
        
        # Check for key elements
        if "helpful" not in prompt.lower():
            suggestions.append("Consider adding 'helpful' to establish a positive tone")
        
        if "document" not in prompt.lower() and "information" not in prompt.lower():
            suggestions.append("Consider mentioning document or information handling")
        
        # Check for problematic content
        problematic_words = ["never", "always refuse", "cannot", "will not"]
        for word in problematic_words:
            if word in prompt.lower():
                issues.append(f"Potentially restrictive language found: '{word}'")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "suggestions": suggestions,
            "length": len(prompt),
            "estimated_tokens": len(prompt.split()) * 1.3  # Rough estimate
        }