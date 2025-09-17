import json
import os
import hashlib
from typing import Dict, List, Optional
from datetime import datetime

class UserModel:
    def __init__(self, data_file: str = "data/users.json"):
        self.data_file = data_file
        os.makedirs(os.path.dirname(data_file), exist_ok=True)
    
    def load_all(self) -> Dict:
        """Load all users from JSON file"""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_all(self, users: Dict):
        """Save all users to JSON file"""
        with open(self.data_file, 'w') as f:
            json.dump(users, f, indent=2)
    
    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return self.hash_password(password) == hashed
    
    def get_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        users = self.load_all()
        return users.get(user_id)
    
    def get_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        users = self.load_all()
        for user in users.values():
            if user['email'] == email:
                return user
        return None
    
    def create(self, email: str, password: str, organization_id: str, role: str = "user", must_change_password: bool = True) -> Dict:
        """Create a new user"""
        import uuid
        
        users = self.load_all()
        
        # Check if email already exists
        if self.get_by_email(email):
            raise ValueError("Email already exists")
        
        user_id = str(uuid.uuid4())
        user = {
            "id": user_id,
            "email": email,
            "password": self.hash_password(password),
            "organization_id": organization_id,
            "role": role,
            "must_change_password": must_change_password,
            "created_at": datetime.now().isoformat()
        }
        
        users[user_id] = user
        self.save_all(users)
        
        return user
    
    def update(self, user_id: str, updates: Dict) -> Optional[Dict]:
        """Update user"""
        users = self.load_all()
        
        if user_id not in users:
            return None
        
        # Hash password if it's being updated
        if 'password' in updates:
            updates['password'] = self.hash_password(updates['password'])
        
        users[user_id].update(updates)
        self.save_all(users)
        
        return users[user_id]
    
    def delete(self, user_id: str) -> bool:
        """Delete user"""
        users = self.load_all()
        
        if user_id not in users:
            return False
        
        del users[user_id]
        self.save_all(users)
        
        return True
    
    def authenticate(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate user"""
        user = self.get_by_email(email)
        
        if user and self.verify_password(password, user['password']):
            # Return user without password
            user_response = user.copy()
            del user_response['password']
            return user_response
        
        return None
    
    def get_users_by_organization(self, organization_id: str) -> List[Dict]:
        """Get all users for an organization"""
        users = self.load_all()
        org_users = []
        
        for user in users.values():
            if user['organization_id'] == organization_id:
                user_copy = user.copy()
                del user_copy['password']  # Don't include password
                org_users.append(user_copy)
        
        return org_users