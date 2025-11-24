import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional
import PyPDF2
from io import BytesIO
import tiktoken
import re

class DocumentService:
    def __init__(self, uploads_dir: str = "data/uploads"):
        self.uploads_dir = uploads_dir
        os.makedirs(uploads_dir, exist_ok=True)
    
    def extract_text_from_pdf(self, file_content: bytes) -> tuple[str, List[Dict]]:
        """Extract text content from PDF with page information"""
        try:
            pdf_reader = PyPDF2.PdfReader(BytesIO(file_content))
            text = ""
            page_texts = []

            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                text += page_text + "\n"
                page_texts.append({
                    "page_number": page_num + 1,
                    "text": page_text,
                    "char_start": len(text) - len(page_text) - 1,
                    "char_end": len(text) - 1
                })

            return text, page_texts
        except Exception as e:
            raise Exception(f"Failed to process PDF: {str(e)}")
    
    def chunk_text(self, text: str, max_tokens: int = 1000, overlap: int = 200, page_texts: List[Dict] = None) -> List[Dict]:
        """Split text into overlapping chunks using modern chunking service"""
        try:
            from .chunking_service import ChunkingService
            
            # Use modern chunking service
            chunking_service = ChunkingService(
                chunk_size=max_tokens,
                chunk_overlap=overlap
            )
            
            chunks = chunking_service.chunk_text(text, page_texts)
            return chunks

        except Exception as e:
            print(f"Error in chunking: {e}")
            # Fallback: simple character-based chunking
            chunk_size = max_tokens * 3
            simple_chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
            return [{"text": chunk, "pages": [], "char_count": len(chunk), "token_count": 0} for chunk in simple_chunks]

    def _find_pages_for_chunk(self, chunk_text: str, full_text: str, page_texts: List[Dict]) -> List[int]:
        """Find which pages a chunk spans"""
        if not page_texts:
            return []

        # Find chunk position in full text
        chunk_start = full_text.find(chunk_text)
        if chunk_start == -1:
            return []

        chunk_end = chunk_start + len(chunk_text)

        # Find overlapping pages
        pages = []
        for page_info in page_texts:
            page_start = page_info['char_start']
            page_end = page_info['char_end']

            # Check if chunk overlaps with this page
            if not (chunk_end < page_start or chunk_start > page_end):
                pages.append(page_info['page_number'])

        return pages if pages else [1]
    
    def _get_overlap_text(self, chunk1: str, chunk2: str, overlap_tokens: int) -> str:
        """Create overlap between two chunks"""
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            
            # Get last sentences from chunk1
            sentences1 = re.split(r'[.!?]+', chunk1)
            sentences2 = re.split(r'[.!?]+', chunk2)
            
            overlap_text = ""
            token_count = 0
            
            # Add sentences from end of chunk1
            for sentence in reversed(sentences1):
                if sentence.strip():
                    test_text = sentence.strip() + ". " + overlap_text
                    test_tokens = len(encoding.encode(test_text))
                    if test_tokens <= overlap_tokens // 2:
                        overlap_text = test_text
                        token_count = test_tokens
                    else:
                        break
            
            # Add sentences from beginning of chunk2
            for sentence in sentences2:
                if sentence.strip():
                    test_text = overlap_text + sentence.strip() + "."
                    test_tokens = len(encoding.encode(test_text))
                    if test_tokens <= overlap_tokens:
                        overlap_text = test_text
                        token_count = test_tokens
                    else:
                        break
            
            return overlap_text.strip()
        except:
            return ""
    
    def save_document(self, file_content: bytes, filename: str, text_content: str, chunks: List[Dict], page_texts: List[Dict] = None) -> Dict:
        """Save document to file system and return document metadata"""
        file_id = str(uuid.uuid4())
        file_path = os.path.join(self.uploads_dir, f"{file_id}.pdf")

        try:
            with open(file_path, "wb") as f:
                f.write(file_content)
        except Exception as e:
            raise Exception(f"Failed to save file: {str(e)}")

        document = {
            "id": file_id,
            "filename": filename,
            "file_path": file_path,
            "text_content": text_content,
            "chunks": chunks,
            "chunk_embeddings": [],
            "page_texts": page_texts or [],
            "total_pages": len(page_texts) if page_texts else 0,
            "uploaded_at": datetime.now().isoformat(),
            "size": len(file_content)
        }

        return document
    
    def delete_document_file(self, file_path: str) -> bool:
        """Delete document file from file system"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            print(f"Warning: Could not delete file {file_path}: {str(e)}")
            return False
    
    def prepare_chunks_with_metadata(self, documents: List[Dict], filename_filter: str = None) -> List[Dict]:
        """Prepare chunks with metadata for similarity search"""
        chunks_with_metadata = []
        
        for doc in documents:
            if filename_filter and filename_filter.lower() not in doc['filename'].lower():
                continue
                
            chunks = doc.get("chunks", [])
            embeddings = doc.get("chunk_embeddings", [])
            
            for i, chunk in enumerate(chunks):
                chunk_text = chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
                chunk_data = {
                    "text": chunk_text,
                    "document_id": doc["id"],
                    "document_name": doc["filename"],
                    "chunk_index": i,
                    "embedding": embeddings[i] if i < len(embeddings) else None
                }
                chunks_with_metadata.append(chunk_data)
        
        return chunks_with_metadata
