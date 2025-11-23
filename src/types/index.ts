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
  chat_count?: number;
  last_activity?: string;
}

export interface User {
  id: string;
  email: string;
  password: string;
  organization_id: string;
  role: 'admin' | 'user';
  must_change_password?: boolean;
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

export interface ConversationMessage {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  metadata?: {
    query_type?: string;
    sources?: Array<{
      document_name: string;
      page_display: string;
      similarity: number;
      chunk_preview: string;
    }>;
    confidence_score?: number;
    needs_clarification?: boolean;
    [key: string]: any;
  };
}

export interface Conversation {
  id: string;
  organization_id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  is_active?: boolean;
}