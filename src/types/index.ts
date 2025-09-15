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
}

export interface ChatMessage {
  id: string;
  message: string;
  response: string;
  timestamp: string;
}