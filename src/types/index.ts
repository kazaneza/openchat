export interface Document {
  id: string;
  filename: string;
  file_path: string;
  text_content: string;
  uploaded_at: string;
  size: number;
}

export interface Organization {
  id: string;
  name: string;
  prompt: string;
  documents: Document[];
  created_at: string;
  document_count: number;
  users: User[];
}

export interface User {
  id: string;
  email: string;
  password: string;
  organization_id: string;
  role: 'admin' | 'user';
  created_at: string;
}

export interface AdminUser {
  id: string;
  email: string;
  password: string;
  role: 'super_admin';
  created_at: string;
}

export interface ChatMessage {
  id: string;
  message: string;
  response: string;
  timestamp: string;
}