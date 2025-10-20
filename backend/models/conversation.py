from typing import Dict, List, Optional
from services.conversation_service import ConversationService

class ConversationModel:
    """Model wrapper for ConversationService to maintain compatibility"""

    def __init__(self):
        self.service = ConversationService()

    def create_conversation(self, organization_id: str, user_id: str, title: str = "New Conversation") -> Dict:
        """Create a new conversation"""
        return self.service.create_conversation(organization_id, user_id, title)

    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Get a conversation by ID"""
        return self.service.get_conversation(conversation_id)

    def get_messages(self, conversation_id: str, limit: int = 20) -> List[Dict]:
        """Get messages from a conversation"""
        return self.service.get_conversation_context(conversation_id, max_messages=limit)

    def add_message(self, conversation_id: str, role: str, content: str, metadata: Dict = None) -> Dict:
        """Add a message to a conversation"""
        return self.service.add_message(conversation_id, role, content, metadata)

    def get_user_conversations(self, organization_id: str, user_id: str, limit: int = 50) -> List[Dict]:
        """Get all conversations for a user"""
        return self.service.get_user_conversations(organization_id, user_id, limit)

    def update_conversation(self, conversation_id: str, updates: Dict) -> Optional[Dict]:
        """Update conversation metadata"""
        return self.service.update_conversation(conversation_id, updates)

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        return self.service.delete_conversation(conversation_id)
