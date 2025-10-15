import os
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict
import threading
import time

class ConversationService:
    """Manages persistent conversation history with file-based storage and 1-day retention"""

    def __init__(self, storage_dir: str = "data/conversations", retention_days: int = 1):
        self.storage_dir = storage_dir
        self.retention_days = retention_days
        os.makedirs(storage_dir, exist_ok=True)

        # Index file for faster lookups
        self.index_file = os.path.join(storage_dir, "_index.json")

        # In-memory cache for faster access
        self._cache = {}
        self._index = {
            "by_user": {},  # user_id -> [conversation_ids]
            "by_org": {},   # org_id -> [conversation_ids]
            "by_date": {},  # date -> [conversation_ids]
            "metadata": {}  # conversation_id -> {user_id, org_id, updated_at, title}
        }
        self._cache_lock = threading.Lock()

        # Load existing conversations and build index
        self._load_all_conversations()
        self._load_or_build_index()

        # Start cleanup thread
        self._start_cleanup_thread()

    def _load_all_conversations(self):
        """Load all conversations from disk into memory cache"""
        try:
            for filename in os.listdir(self.storage_dir):
                if filename.endswith('.json') and filename != '_index.json':
                    conversation_id = filename.replace('.json', '')
                    filepath = os.path.join(self.storage_dir, filename)
                    with open(filepath, 'r') as f:
                        self._cache[conversation_id] = json.load(f)
            print(f"Loaded {len(self._cache)} conversations from disk")
        except Exception as e:
            print(f"Error loading conversations: {e}")

    def _load_or_build_index(self):
        """Load index from file or build it from conversations"""
        try:
            if os.path.exists(self.index_file):
                with open(self.index_file, 'r') as f:
                    self._index = json.load(f)
                print(f"Loaded index with {len(self._index['metadata'])} entries")
            else:
                self._rebuild_index()
        except Exception as e:
            print(f"Error loading index, rebuilding: {e}")
            self._rebuild_index()

    def _rebuild_index(self):
        """Rebuild index from all conversations"""
        self._index = {
            "by_user": {},
            "by_org": {},
            "by_date": {},
            "metadata": {}
        }

        for conv_id, conv in self._cache.items():
            self._add_to_index(conv)

        self._save_index()
        print(f"Rebuilt index with {len(self._index['metadata'])} entries")

    def _add_to_index(self, conversation: Dict):
        """Add conversation to index"""
        conv_id = conversation['id']
        user_id = conversation['user_id']
        org_id = conversation['organization_id']
        updated_at = conversation['updated_at']
        date_key = updated_at.split('T')[0]  # YYYY-MM-DD

        # Index by user
        if user_id not in self._index['by_user']:
            self._index['by_user'][user_id] = []
        if conv_id not in self._index['by_user'][user_id]:
            self._index['by_user'][user_id].append(conv_id)

        # Index by organization
        if org_id not in self._index['by_org']:
            self._index['by_org'][org_id] = []
        if conv_id not in self._index['by_org'][org_id]:
            self._index['by_org'][org_id].append(conv_id)

        # Index by date
        if date_key not in self._index['by_date']:
            self._index['by_date'][date_key] = []
        if conv_id not in self._index['by_date'][date_key]:
            self._index['by_date'][date_key].append(conv_id)

        # Store metadata
        self._index['metadata'][conv_id] = {
            'user_id': user_id,
            'organization_id': org_id,
            'updated_at': updated_at,
            'title': conversation.get('title', 'New Conversation'),
            'message_count': conversation.get('message_count', 0),
            'is_active': conversation.get('is_active', True)
        }

    def _remove_from_index(self, conv_id: str):
        """Remove conversation from index"""
        if conv_id not in self._index['metadata']:
            return

        metadata = self._index['metadata'][conv_id]
        user_id = metadata['user_id']
        org_id = metadata['organization_id']
        date_key = metadata['updated_at'].split('T')[0]

        # Remove from user index
        if user_id in self._index['by_user'] and conv_id in self._index['by_user'][user_id]:
            self._index['by_user'][user_id].remove(conv_id)

        # Remove from org index
        if org_id in self._index['by_org'] and conv_id in self._index['by_org'][org_id]:
            self._index['by_org'][org_id].remove(conv_id)

        # Remove from date index
        if date_key in self._index['by_date'] and conv_id in self._index['by_date'][date_key]:
            self._index['by_date'][date_key].remove(conv_id)

        # Remove metadata
        del self._index['metadata'][conv_id]

    def _save_index(self):
        """Save index to file"""
        try:
            with open(self.index_file, 'w') as f:
                json.dump(self._index, f, indent=2)
        except Exception as e:
            print(f"Error saving index: {e}")

    def _save_conversation(self, conversation: Dict):
        """Save conversation to disk and update index"""
        try:
            conversation_id = conversation['id']
            filepath = os.path.join(self.storage_dir, f"{conversation_id}.json")

            with self._cache_lock:
                with open(filepath, 'w') as f:
                    json.dump(conversation, f, indent=2)
                self._cache[conversation_id] = conversation
                self._add_to_index(conversation)
                self._save_index()
        except Exception as e:
            print(f"Error saving conversation {conversation.get('id')}: {e}")

    def create_conversation(self, organization_id: str, user_id: str, title: str = "New Conversation") -> Dict:
        """Create a new conversation"""
        conversation = {
            "id": str(uuid.uuid4()),
            "organization_id": organization_id,
            "user_id": user_id,
            "title": title,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": [],
            "message_count": 0,
            "is_active": True,
            "metadata": {
                "total_tokens": 0,
                "sources_used": []
            }
        }

        self._save_conversation(conversation)
        print(f"Created conversation {conversation['id']} for user {user_id}")
        return conversation

    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Get a conversation by ID"""
        with self._cache_lock:
            return self._cache.get(conversation_id)

    def get_user_conversations(self, organization_id: str, user_id: str, limit: int = 50) -> List[Dict]:
        """Get all conversations for a user in an organization using index"""
        user_conv_ids = self._index['by_user'].get(user_id, [])

        conversations = []
        for conv_id in user_conv_ids:
            metadata = self._index['metadata'].get(conv_id)
            if metadata and metadata['organization_id'] == organization_id:
                conv = self.get_conversation(conv_id)
                if conv:
                    conversations.append(conv)

        # Sort by updated_at descending
        conversations.sort(key=lambda x: x['updated_at'], reverse=True)
        return conversations[:limit]

    def get_active_conversation(self, organization_id: str, user_id: str) -> Optional[Dict]:
        """Get the most recent active conversation for a user"""
        conversations = self.get_user_conversations(organization_id, user_id)

        for conv in conversations:
            if conv.get('is_active', True):
                return conv

        return None

    def add_message(self, conversation_id: str, role: str, content: str, metadata: Dict = None) -> Dict:
        """Add a message to a conversation"""
        conversation = self.get_conversation(conversation_id)

        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        if role not in ['user', 'assistant']:
            raise ValueError(f"Invalid role: {role}. Must be 'user' or 'assistant'")

        # Estimate token count (rough approximation)
        token_count = len(content.split()) * 1.3

        message = {
            "id": str(uuid.uuid4()),
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
            "token_count": int(token_count)
        }

        # Add message to conversation
        conversation['messages'].append(message)
        conversation['message_count'] = len(conversation['messages'])
        conversation['updated_at'] = datetime.now().isoformat()
        conversation['metadata']['total_tokens'] += int(token_count)

        # Update sources if provided in metadata
        if metadata and 'sources' in metadata:
            existing_sources = set(conversation['metadata'].get('sources_used', []))
            new_sources = set(metadata['sources'])
            conversation['metadata']['sources_used'] = list(existing_sources | new_sources)

        # Auto-generate title from first user message if still "New Conversation"
        if conversation['title'] == "New Conversation" and role == 'user' and conversation['message_count'] == 1:
            conversation['title'] = self._generate_title(content)

        self._save_conversation(conversation)
        return message

    def _generate_title(self, first_message: str, max_length: int = 50) -> str:
        """Generate a conversation title from the first message"""
        title = first_message.strip()

        # Truncate if too long
        if len(title) > max_length:
            title = title[:max_length-3] + "..."

        # Remove newlines
        title = title.replace('\n', ' ').replace('\r', '')

        return title or "New Conversation"

    def get_conversation_context(self, conversation_id: str, max_messages: int = 10) -> List[Dict]:
        """Get recent messages from a conversation for context"""
        conversation = self.get_conversation(conversation_id)

        if not conversation:
            return []

        messages = conversation.get('messages', [])

        # Return last N messages
        return messages[-max_messages:] if len(messages) > max_messages else messages

    def format_context_for_llm(self, conversation_id: str, max_messages: int = 10) -> str:
        """Format conversation context for LLM prompt"""
        messages = self.get_conversation_context(conversation_id, max_messages)

        if not messages:
            return ""

        context_parts = ["Previous conversation:"]
        for msg in messages:
            role = "User" if msg['role'] == 'user' else "Assistant"
            content = msg['content']
            context_parts.append(f"{role}: {content}")

        return "\n".join(context_parts)

    def update_conversation(self, conversation_id: str, updates: Dict) -> Optional[Dict]:
        """Update conversation metadata"""
        conversation = self.get_conversation(conversation_id)

        if not conversation:
            return None

        # Update allowed fields
        allowed_fields = ['title', 'is_active', 'metadata']
        for field in allowed_fields:
            if field in updates:
                conversation[field] = updates[field]

        conversation['updated_at'] = datetime.now().isoformat()
        self._save_conversation(conversation)

        return conversation

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        try:
            filepath = os.path.join(self.storage_dir, f"{conversation_id}.json")

            with self._cache_lock:
                if conversation_id in self._cache:
                    del self._cache[conversation_id]

                self._remove_from_index(conversation_id)
                self._save_index()

                if os.path.exists(filepath):
                    os.remove(filepath)

            print(f"Deleted conversation {conversation_id}")
            return True
        except Exception as e:
            print(f"Error deleting conversation {conversation_id}: {e}")
            return False

    def delete_user_conversations(self, organization_id: str, user_id: str) -> int:
        """Delete all conversations for a user"""
        conversations = self.get_user_conversations(organization_id, user_id)
        deleted_count = 0

        for conv in conversations:
            if self.delete_conversation(conv['id']):
                deleted_count += 1

        return deleted_count

    def delete_organization_conversations(self, organization_id: str) -> int:
        """Delete all conversations for an organization"""
        org_conv_ids = self._index['by_org'].get(organization_id, []).copy()
        deleted_count = 0

        for conv_id in org_conv_ids:
            if self.delete_conversation(conv_id):
                deleted_count += 1

        return deleted_count

    def cleanup_old_conversations(self, days: int = None) -> int:
        """Delete conversations older than specified days (defaults to retention_days)"""
        if days is None:
            days = self.retention_days

        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = 0

        # Use date index for efficient cleanup
        dates_to_check = []
        current_date = cutoff_date.date()

        # Check all dates before cutoff
        for date_key in list(self._index['by_date'].keys()):
            try:
                date_obj = datetime.strptime(date_key, '%Y-%m-%d').date()
                if date_obj < current_date:
                    dates_to_check.append(date_key)
            except:
                continue

        # Delete conversations from old dates
        for date_key in dates_to_check:
            conv_ids = self._index['by_date'].get(date_key, []).copy()
            for conv_id in conv_ids:
                metadata = self._index['metadata'].get(conv_id)
                if metadata:
                    updated_at = datetime.fromisoformat(metadata['updated_at'])
                    if updated_at < cutoff_date:
                        if self.delete_conversation(conv_id):
                            deleted_count += 1

        if deleted_count > 0:
            print(f"Cleaned up {deleted_count} conversations older than {days} day(s)")

        return deleted_count

    def _start_cleanup_thread(self):
        """Start background thread for automatic cleanup"""
        def cleanup_worker():
            while True:
                try:
                    # Run cleanup every hour
                    time.sleep(3600)
                    self.cleanup_old_conversations()
                except Exception as e:
                    print(f"Error in cleanup thread: {e}")

        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
        print(f"Started automatic cleanup thread (retention: {self.retention_days} day(s))")

    def get_statistics(self, organization_id: str = None, user_id: str = None) -> Dict:
        """Get conversation statistics using index"""
        if user_id:
            conv_ids = self._index['by_user'].get(user_id, [])
        elif organization_id:
            conv_ids = self._index['by_org'].get(organization_id, [])
        else:
            conv_ids = list(self._index['metadata'].keys())

        conversations = [self.get_conversation(cid) for cid in conv_ids]
        conversations = [c for c in conversations if c]

        total_messages = sum(c['message_count'] for c in conversations)
        total_tokens = sum(c['metadata'].get('total_tokens', 0) for c in conversations)
        active_conversations = sum(1 for c in conversations if c.get('is_active', True))

        return {
            "total_conversations": len(conversations),
            "active_conversations": active_conversations,
            "total_messages": total_messages,
            "total_tokens": total_tokens,
            "average_messages_per_conversation": total_messages / len(conversations) if conversations else 0,
            "retention_days": self.retention_days
        }
