from typing import Dict, List, Optional

class EscalationService:
    def __init__(self):
        self.escalation_triggers = {
            'low_confidence': 0.4,
            'no_relevant_info': True,
            'complex_request': True,
            'complaint_detected': True,
            'refund_request': True,
            'legal_issue': True
        }

    def should_escalate(
        self,
        query: str,
        confidence_score: float,
        sources: List[Dict],
        query_analysis: Dict
    ) -> Dict:
        """
        Determine if query should be escalated to human agent
        Returns: {
            'should_escalate': bool,
            'escalation_reason': str,
            'urgency': str (low, medium, high),
            'suggested_department': str
        }
        """
        query_lower = query.lower()
        escalation_reasons = []
        urgency = 'low'
        department = 'general_support'

        # Check confidence score
        if confidence_score < self.escalation_triggers['low_confidence']:
            escalation_reasons.append('Low confidence in automated response')
            urgency = 'medium'

        # Check if no relevant information found
        if not sources or len(sources) == 0:
            if self._requires_specific_info(query_lower):
                escalation_reasons.append('No relevant information available')
                urgency = 'medium'

        # Check for complaint indicators
        if self._is_complaint(query_lower):
            escalation_reasons.append('Customer complaint detected')
            urgency = 'high'
            department = 'customer_relations'

        # Check for refund/billing issues
        if self._is_billing_issue(query_lower):
            escalation_reasons.append('Billing or refund request')
            urgency = 'high'
            department = 'billing'

        # Check for legal issues
        if self._is_legal_issue(query_lower):
            escalation_reasons.append('Legal or compliance matter')
            urgency = 'high'
            department = 'legal'

        # Check for security/account issues
        if self._is_security_issue(query_lower):
            escalation_reasons.append('Security or account access issue')
            urgency = 'high'
            department = 'security'

        # Check for complex technical issues
        if self._is_complex_technical(query_lower):
            escalation_reasons.append('Complex technical issue')
            urgency = 'medium'
            department = 'technical_support'

        # Check for multiple failed attempts (from query analysis)
        if query_analysis.get('follow_up', {}).get('is_follow_up'):
            previous_context = query_analysis.get('follow_up', {}).get('context_summary', '')
            if 'unclear' in previous_context.lower() or 'not help' in previous_context.lower():
                escalation_reasons.append('Multiple unsuccessful assistance attempts')
                urgency = 'high'

        should_escalate = len(escalation_reasons) > 0

        return {
            'should_escalate': should_escalate,
            'escalation_reasons': escalation_reasons,
            'urgency': urgency,
            'suggested_department': department,
            'escalation_message': self._generate_escalation_message(escalation_reasons, department)
        }

    def _requires_specific_info(self, query: str) -> bool:
        """Check if query requires specific information"""
        specific_indicators = [
            'my account', 'my order', 'my payment', 'my subscription',
            'invoice', 'transaction', 'reference number', 'order number'
        ]
        return any(indicator in query for indicator in specific_indicators)

    def _is_complaint(self, query: str) -> bool:
        """Detect if query is a complaint"""
        complaint_words = [
            'complaint', 'complain', 'unhappy', 'disappointed', 'frustrated',
            'angry', 'terrible', 'horrible', 'worst', 'unacceptable',
            'not satisfied', 'poor service', 'bad experience', 'manager',
            'supervisor', 'escalate'
        ]
        return any(word in query for word in complaint_words)

    def _is_billing_issue(self, query: str) -> bool:
        """Detect billing/refund issues"""
        billing_words = [
            'refund', 'charge', 'charged', 'billing', 'payment', 'invoice',
            'overcharged', 'incorrect charge', 'cancel subscription',
            'money back', 'unauthorized'
        ]
        return any(word in query for word in billing_words)

    def _is_legal_issue(self, query: str) -> bool:
        """Detect legal/compliance issues"""
        legal_words = [
            'legal', 'lawyer', 'attorney', 'sue', 'lawsuit', 'court',
            'gdpr', 'privacy violation', 'data breach', 'comply', 'regulation'
        ]
        return any(word in query for word in legal_words)

    def _is_security_issue(self, query: str) -> bool:
        """Detect security/account access issues"""
        security_words = [
            'hacked', 'hack', 'unauthorized access', 'locked out',
            'cannot login', "can't access", 'password reset', 'security',
            'suspicious activity', 'fraud', 'stolen'
        ]
        return any(word in query for word in security_words)

    def _is_complex_technical(self, query: str) -> bool:
        """Detect complex technical issues"""
        technical_indicators = [
            'integration', 'api', 'configuration', 'setup', 'not working',
            'error code', 'system down', 'technical problem'
        ]
        return any(indicator in query for indicator in technical_indicators)

    def _generate_escalation_message(self, reasons: List[str], department: str) -> str:
        """Generate message to show when escalating"""
        if not reasons:
            return ""

        department_names = {
            'customer_relations': 'Customer Relations',
            'billing': 'Billing Department',
            'legal': 'Legal Department',
            'security': 'Security Team',
            'technical_support': 'Technical Support',
            'general_support': 'Customer Support'
        }

        dept_name = department_names.get(department, 'Customer Support')

        base_message = f"I understand this is important. Let me connect you with {dept_name} for specialized assistance."

        return base_message

    def create_escalation_response(self, escalation_check: Dict, organization: Dict) -> str:
        """Create appropriate response for escalated queries"""
        org_name = organization.get('name', 'our team')
        urgency = escalation_check.get('urgency', 'medium')
        escalation_message = escalation_check.get('escalation_message', '')

        if urgency == 'high':
            response = f"{escalation_message}\n\nThis matter requires immediate attention from a specialist who can provide you with the detailed assistance you need."
        else:
            response = f"{escalation_message}\n\nA specialist from our team will be better equipped to help you with this specific request."

        # Add contact information if available
        contact_info = organization.get('contact_info', {})
        if contact_info:
            if contact_info.get('email'):
                response += f"\n\nYou can reach us at: {contact_info['email']}"
            if contact_info.get('phone'):
                response += f"\nPhone: {contact_info['phone']}"

        return response
