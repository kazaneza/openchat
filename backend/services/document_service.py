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
    
    def chunk_text(self, text: str, max_tokens: int = 500, overlap: int = 50, page_texts: List[Dict] = None) -> List[Dict]:
        """Split text into overlapping chunks for better context preservation with page tracking"""
        try:
            encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding
            
            # Split by paragraphs first
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            chunks = []
            current_chunk = ""
            
            for paragraph in paragraphs:
                # Check if adding this paragraph would exceed the limit
                test_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph
                token_count = len(encoding.encode(test_chunk))
                
                if token_count <= max_tokens:
                    current_chunk = test_chunk
                else:
                    # Save current chunk if it has content
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    
                    # If single paragraph is too long, split it further
                    if len(encoding.encode(paragraph)) > max_tokens:
                        # Split by sentences
                        sentences = re.split(r'[.!?]+', paragraph)
                        temp_chunk = ""
                        
                        for sentence in sentences:
                            if not sentence.strip():
                                continue
                            test_sentence = temp_chunk + sentence.strip() + "."
                            if len(encoding.encode(test_sentence)) <= max_tokens:
                                temp_chunk = test_sentence
                            else:
                                if temp_chunk:
                                    chunks.append(temp_chunk.strip())
                                temp_chunk = sentence.strip() + "."
                        
                        if temp_chunk:
                            chunks.append(temp_chunk.strip())
                        current_chunk = ""
                    else:
                        current_chunk = paragraph
            
            # Add the last chunk
            if current_chunk:
                chunks.append(current_chunk.strip())

            # Create overlapping chunks for better context
            if len(chunks) > 1:
                overlapping_chunks = []
                for i, chunk in enumerate(chunks):
                    overlapping_chunks.append(chunk)

                    # Add overlap with next chunk
                    if i < len(chunks) - 1:
                        overlap_text = self._get_overlap_text(chunk, chunks[i + 1], overlap)
                        if overlap_text:
                            overlapping_chunks.append(overlap_text)

                chunks = [chunk for chunk in overlapping_chunks if chunk.strip()]
            else:
                chunks = [chunk for chunk in chunks if chunk.strip()]

            # Add page numbers to chunks
            chunks_with_metadata = []
            for chunk_text in chunks:
                page_nums = self._find_pages_for_chunk(chunk_text, text, page_texts)
                chunks_with_metadata.append({
                    "text": chunk_text,
                    "pages": page_nums,
                    "char_count": len(chunk_text),
                    "token_count": len(encoding.encode(chunk_text))
                })

            return chunks_with_metadata

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
                chunk_data = {
                    "text": chunk,
                    "document_id": doc["id"],
                    "document_name": doc["filename"],
                    "chunk_index": i,
                    "embedding": embeddings[i] if i < len(embeddings) else None
                }
                chunks_with_metadata.append(chunk_data)
        
        return chunks_with_metadata