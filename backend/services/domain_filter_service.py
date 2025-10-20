from typing import Dict, Optional, List
import re

class DomainFilterService:
    def __init__(self):
        self.off_topic_keywords = {
            'general': ['weather', 'recipe', 'cooking', 'sports', 'entertainment', 'celebrity', 'movie', 'music', 'game'],
            'personal': ['personal advice', 'dating', 'relationship', 'health diagnosis', 'medical advice'],
            'inappropriate': ['joke', 'story', 'poem', 'creative writing', 'roleplay']
        }

    def is_query_relevant(self, query: str, organization: Dict) -> Dict:
        """
        Determine if a query is relevant to the organization's domain
        Returns: {
            'is_relevant': bool,
            'confidence': float,
            'reason': str,
            'category': str
        }
        """
        org_name = organization.get('name', '').lower()
        org_domain = organization.get('domain', '').lower()
        org_industry = organization.get('industry', '').lower()
        documents = organization.get('documents', [])

        query_lower = query.lower()

        # Check if organization has domain/industry defined
        has_domain_context = bool(org_domain or org_industry)

        # If no domain is set and no documents, be more permissive
        if not has_domain_context and not documents:
            return {
                'is_relevant': True,
                'confidence': 0.5,
                'reason': 'No domain restrictions configured',
                'category': 'unrestricted'
            }

        # Check if query mentions organization by name
        if org_name and org_name in query_lower:
            return {
                'is_relevant': True,
                'confidence': 0.9,
                'reason': 'Query mentions organization name',
                'category': 'organization_specific'
            }

        # Check for obvious off-topic queries
        off_topic_score = self._calculate_off_topic_score(query_lower)
        if off_topic_score > 0.7:
            return {
                'is_relevant': False,
                'confidence': off_topic_score,
                'reason': 'Query appears unrelated to business domain',
                'category': 'off_topic'
            }

        # Check if query is about the service/product (domain-related)
        if has_domain_context:
            domain_relevance = self._check_domain_relevance(query_lower, org_domain, org_industry)
            if domain_relevance['score'] > 0.6:
                return {
                    'is_relevant': True,
                    'confidence': domain_relevance['score'],
                    'reason': f"Query relates to {domain_relevance['matched_domain']}",
                    'category': 'domain_specific'
                }

        # If we have documents, check if query might be answerable from documents
        if documents:
            document_relevance = self._check_document_relevance(query_lower, documents)
            if document_relevance > 0.5:
                return {
                    'is_relevant': True,
                    'confidence': document_relevance,
                    'reason': 'Query may be answerable from uploaded documents',
                    'category': 'document_based'
                }

        # Default: allow with low confidence if not clearly off-topic
        if off_topic_score < 0.4:
            return {
                'is_relevant': True,
                'confidence': 0.6,
                'reason': 'Query appears business-related',
                'category': 'general_business'
            }

        return {
            'is_relevant': False,
            'confidence': 0.7,
            'reason': 'Query does not appear related to organization',
            'category': 'unrelated'
        }

    def _calculate_off_topic_score(self, query: str) -> float:
        """Calculate how off-topic a query is"""
        off_topic_count = 0
        total_categories = 0

        for category, keywords in self.off_topic_keywords.items():
            total_categories += 1
            for keyword in keywords:
                if keyword in query:
                    off_topic_count += 1
                    break

        return off_topic_count / max(total_categories, 1)

    def _check_domain_relevance(self, query: str, domain: str, industry: str) -> Dict:
        """Check if query is relevant to organization's domain/industry"""
        domains = [d.strip() for d in domain.split(',') if d.strip()] if domain else []
        industries = [i.strip() for i in industry.split(',') if i.strip()] if industry else []

        all_terms = domains + industries

        if not all_terms:
            return {'score': 0.5, 'matched_domain': 'general'}

        matches = 0
        matched_term = None

        for term in all_terms:
            if term.lower() in query:
                matches += 1
                matched_term = term

        if matches > 0:
            return {'score': min(0.7 + (matches * 0.1), 1.0), 'matched_domain': matched_term or all_terms[0]}

        # Check for related terms
        for term in all_terms:
            if self._are_terms_related(query, term):
                return {'score': 0.6, 'matched_domain': term}

        return {'score': 0.4, 'matched_domain': 'general'}

    def _are_terms_related(self, query: str, domain_term: str) -> bool:
        """Simple check if query terms are related to domain"""
        domain_related_terms = {
            'banking': ['account', 'loan', 'credit', 'debit', 'transfer', 'payment', 'savings'],
            'insurance': ['policy', 'claim', 'coverage', 'premium', 'benefit'],
            'healthcare': ['appointment', 'doctor', 'patient', 'medical', 'treatment', 'diagnosis'],
            'retail': ['product', 'order', 'purchase', 'shipping', 'return', 'refund'],
            'technology': ['software', 'app', 'system', 'feature', 'bug', 'update'],
            'education': ['course', 'student', 'class', 'enrollment', 'grade', 'assignment']
        }

        domain_lower = domain_term.lower()
        for domain_key, related_terms in domain_related_terms.items():
            if domain_key in domain_lower:
                for term in related_terms:
                    if term in query:
                        return True

        return False

    def _check_document_relevance(self, query: str, documents: List[Dict]) -> float:
        """Estimate if query might be answerable from documents"""
        query_words = set(query.split())

        business_indicators = {
            'what', 'how', 'when', 'where', 'who', 'which', 'price', 'cost',
            'hours', 'location', 'service', 'product', 'policy', 'process',
            'procedure', 'requirement', 'form', 'application', 'contact'
        }

        indicator_count = len(query_words.intersection(business_indicators))

        if indicator_count > 0:
            return min(0.5 + (indicator_count * 0.1), 0.9)

        return 0.3

    def get_off_topic_response(self, query: str, organization: Dict, relevance_check: Dict) -> str:
        """Generate appropriate response for off-topic queries"""
        org_name = organization.get('name', 'our organization')
        org_domain = organization.get('domain', '')

        if relevance_check['category'] == 'off_topic':
            if org_domain:
                return f"I'm a customer support assistant for {org_name}, specializing in {org_domain}. I'm here to help with questions related to our services and products. How can I assist you with {org_domain}-related inquiries?"
            else:
                return f"I'm a customer support assistant for {org_name}. I'm here to help with questions about our organization, services, and products. Is there something specific about {org_name} I can help you with?"

        return f"I'm here to assist with questions about {org_name}. Could you please clarify how I can help you with our services?"
