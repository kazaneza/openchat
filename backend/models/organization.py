import json
import os
from typing import Dict, List, Optional
from datetime import datetime

class OrganizationModel:
    def __init__(self, data_file: str = "data/organizations.json"):
        self.data_file = data_file
        os.makedirs(os.path.dirname(data_file), exist_ok=True)
    
    def load_all(self) -> Dict:
        """Load all organizations from JSON file"""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_all(self, organizations: Dict):
        """Save all organizations to JSON file"""
        with open(self.data_file, 'w') as f:
            json.dump(organizations, f, indent=2)
    
    def get_by_id(self, org_id: str) -> Optional[Dict]:
        """Get organization by ID"""
        organizations = self.load_all()
        return organizations.get(org_id)
    
    def create(self, name: str, prompt: str, domain: str = "", industry: str = "", contact_info: Dict = None) -> Dict:
        """Create a new organization"""
        import uuid

        organizations = self.load_all()
        org_id = str(uuid.uuid4())

        organization = {
            "id": org_id,
            "name": name,
            "prompt": prompt or "You are a helpful AI assistant with comprehensive knowledge about this organization. Provide accurate, helpful responses while maintaining a professional and friendly tone. Always respond in the same language as the user's question. Remember previous conversation context to provide better assistance.",
            "domain": domain,
            "industry": industry,
            "contact_info": contact_info or {},
            "documents": [],
            "created_at": datetime.now().isoformat(),
            "document_count": 0,
            "chat_count": 0,
            "last_activity": None
        }

        organizations[org_id] = organization
        self.save_all(organizations)

        return organization
    
    def update(self, org_id: str, updates: Dict) -> Optional[Dict]:
        """Update organization"""
        organizations = self.load_all()
        
        if org_id not in organizations:
            return None
        
        organizations[org_id].update(updates)
        self.save_all(organizations)
        
        return organizations[org_id]
    
    def delete(self, org_id: str) -> bool:
        """Delete organization"""
        organizations = self.load_all()
        
        if org_id not in organizations:
            return False
        
        del organizations[org_id]
        self.save_all(organizations)
        
        return True
    
    def add_document(self, org_id: str, document: Dict) -> Optional[Dict]:
        """Add document to organization"""
        organizations = self.load_all()
        
        if org_id not in organizations:
            return None
        
        organizations[org_id]["documents"].append(document)
        organizations[org_id]["document_count"] = len(organizations[org_id]["documents"])
        
        self.save_all(organizations)
        
        return organizations[org_id]
    
    def remove_document(self, org_id: str, doc_id: str) -> Optional[Dict]:
        """Remove document from organization"""
        organizations = self.load_all()
        
        if org_id not in organizations:
            return None
        
        organization = organizations[org_id]
        documents = organization["documents"]
        
        # Find and remove document
        for i, doc in enumerate(documents):
            if doc["id"] == doc_id:
                removed_doc = documents.pop(i)
                organization["document_count"] = len(documents)
                self.save_all(organizations)
                return removed_doc
        
        return None
    
    def increment_chat_count(self, org_id: str):
        """Increment chat count and update last activity"""
        organizations = self.load_all()
        
        if org_id in organizations:
            organizations[org_id]["chat_count"] = organizations[org_id].get("chat_count", 0) + 1
            organizations[org_id]["last_activity"] = datetime.now().isoformat()
            self.save_all(organizations)