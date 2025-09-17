import json
import os
from typing import List, Dict
from .openai_service import OpenAIService

class EmbeddingService:
    def __init__(self, openai_service: OpenAIService):
        self.openai_service = openai_service
        self.embeddings_cache_dir = "data/embeddings"
        os.makedirs(self.embeddings_cache_dir, exist_ok=True)
    
    def generate_embeddings_for_document(self, document: Dict) -> Dict:
        """Generate embeddings for all chunks in a document"""
        if not self.openai_service.is_available():
            print("OpenAI service not available, skipping embeddings")
            return document
        
        chunks = document.get("chunks", [])
        if not chunks:
            return document
        
        try:
            # Check if embeddings already exist
            cache_file = os.path.join(self.embeddings_cache_dir, f"{document['id']}.json")
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    cached_embeddings = json.load(f)
                    if len(cached_embeddings) == len(chunks):
                        document["chunk_embeddings"] = cached_embeddings
                        print(f"Loaded cached embeddings for {document['filename']}")
                        return document
            
            print(f"Generating embeddings for {document['filename']} ({len(chunks)} chunks)")
            
            # Generate embeddings in batches to avoid rate limits
            batch_size = 10
            all_embeddings = []
            
            for i in range(0, len(chunks), batch_size):
                batch_chunks = chunks[i:i + batch_size]
                batch_embeddings = self.openai_service.get_embeddings(batch_chunks)
                all_embeddings.extend(batch_embeddings)
                print(f"Generated embeddings for batch {i//batch_size + 1}/{(len(chunks) + batch_size - 1)//batch_size}")
            
            if len(all_embeddings) == len(chunks):
                document["chunk_embeddings"] = all_embeddings
                
                # Cache the embeddings
                with open(cache_file, 'w') as f:
                    json.dump(all_embeddings, f)
                
                print(f"Successfully generated and cached embeddings for {document['filename']}")
            else:
                print(f"Warning: Embedding count mismatch for {document['filename']}")
        
        except Exception as e:
            print(f"Error generating embeddings for {document['filename']}: {e}")
        
        return document
    
    def update_document_embeddings(self, documents: List[Dict]) -> List[Dict]:
        """Update embeddings for all documents that don't have them"""
        updated_documents = []
        
        for doc in documents:
            if not doc.get("chunk_embeddings") or len(doc.get("chunk_embeddings", [])) != len(doc.get("chunks", [])):
                print(f"Updating embeddings for {doc['filename']}")
                updated_doc = self.generate_embeddings_for_document(doc)
                updated_documents.append(updated_doc)
            else:
                updated_documents.append(doc)
        
        return updated_documents
    
    def clear_embeddings_cache(self, document_id: str = None):
        """Clear embeddings cache for a specific document or all documents"""
        try:
            if document_id:
                cache_file = os.path.join(self.embeddings_cache_dir, f"{document_id}.json")
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                    print(f"Cleared embeddings cache for document {document_id}")
            else:
                # Clear all cache files
                for filename in os.listdir(self.embeddings_cache_dir):
                    if filename.endswith('.json'):
                        os.remove(os.path.join(self.embeddings_cache_dir, filename))
                print("Cleared all embeddings cache")
        except Exception as e:
            print(f"Error clearing embeddings cache: {e}")