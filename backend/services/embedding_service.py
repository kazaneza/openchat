import json
import os
from typing import List, Dict
from .openai_service import OpenAIService
from .vector_service import VectorService

class EmbeddingService:
    def __init__(self, openai_service: OpenAIService, vector_service: VectorService):
        self.openai_service = openai_service
        self.vector_service = vector_service
        
        # Keep file-based cache as backup
        self.embeddings_cache_dir = "data/embeddings"
        os.makedirs(self.embeddings_cache_dir, exist_ok=True)
    
    def generate_embeddings_for_document(self, document: Dict, organization_id: str) -> Dict:
        """Generate embeddings for all chunks in a document and store in ChromaDB"""
        if not self.openai_service.is_available():
            print("OpenAI service not available, skipping embeddings")
            return document
        
        chunks = document.get("chunks", [])
        if not chunks:
            print(f"No chunks found for document {document['filename']}")
            return document
        
        try:
            document_id = document["id"]
            document_name = document["filename"]
            
            print(f"Generating embeddings for {document_name} ({len(chunks)} chunks)")
            
            # Generate embeddings in batches to avoid rate limits
            batch_size = 10
            all_embeddings = []
            
            for i in range(0, len(chunks), batch_size):
                batch_chunks = chunks[i:i + batch_size]
                batch_embeddings = self.openai_service.get_embeddings(batch_chunks)
                
                if not batch_embeddings:
                    print(f"Failed to generate embeddings for batch {i//batch_size + 1}")
                    continue
                    
                all_embeddings.extend(batch_embeddings)
                print(f"Generated embeddings for batch {i//batch_size + 1}/{(len(chunks) + batch_size - 1)//batch_size}")
            
            if len(all_embeddings) != len(chunks):
                print(f"Warning: Embedding count mismatch for {document_name}")
                return document
            
            # Store embeddings in ChromaDB
            success = self.vector_service.add_document_chunks(
                document_id=document_id,
                document_name=document_name,
                chunks=chunks,
                embeddings=all_embeddings,
                organization_id=organization_id
            )
            
            if success:
                # Also cache embeddings in file system as backup
                cache_file = os.path.join(self.embeddings_cache_dir, f"{document_id}.json")
                with open(cache_file, 'w') as f:
                    json.dump(all_embeddings, f)
                
                # Store embeddings in document for backward compatibility
                document["chunk_embeddings"] = all_embeddings
                document["embeddings_stored"] = True
                document["vector_db_stored"] = True
                
                print(f"Successfully generated and stored embeddings for {document_name}")
            else:
                print(f"Failed to store embeddings in ChromaDB for {document_name}")
        
        except Exception as e:
            print(f"Error generating embeddings for {document['filename']}: {e}")
        
        return document
    
    def update_document_embeddings(self, documents: List[Dict], organization_id: str) -> List[Dict]:
        """Update embeddings for all documents that don't have them"""
        updated_documents = []
        
        for doc in documents:
            needs_embeddings = (
                not doc.get("embeddings_stored") or 
                not doc.get("vector_db_stored") or
                not doc.get("chunk_embeddings") or 
                len(doc.get("chunk_embeddings", [])) != len(doc.get("chunks", []))
            )
            
            if needs_embeddings:
                print(f"Updating embeddings for {doc['filename']}")
                updated_doc = self.generate_embeddings_for_document(doc, organization_id)
                updated_documents.append(updated_doc)
            else:
                updated_documents.append(doc)
        
        return updated_documents
    
    def search_similar_chunks(self, query_embedding: List[float], organization_id: str, top_k: int = 5) -> List[Dict]:
        """Search for similar chunks using ChromaDB"""
        return self.vector_service.search_similar_chunks(
            query_embedding=query_embedding,
            organization_id=organization_id,
            top_k=top_k
        )
    
    def delete_document_embeddings(self, document_id: str):
        """Delete embeddings for a specific document"""
        # Delete from ChromaDB
        self.vector_service.delete_document_chunks(document_id)
        
        # Delete from file cache
        cache_file = os.path.join(self.embeddings_cache_dir, f"{document_id}.json")
        if os.path.exists(cache_file):
            os.remove(cache_file)
            print(f"Deleted embedding cache file for document {document_id}")
    
    def delete_organization_embeddings(self, organization_id: str):
        """Delete all embeddings for an organization"""
        self.vector_service.delete_organization_chunks(organization_id)
    
    def get_embedding_stats(self) -> Dict:
        """Get statistics about stored embeddings"""
        return self.vector_service.get_collection_stats()
    
    def clear_embeddings_cache(self, document_id: str = None):
        """Clear embeddings cache for a specific document or all documents"""
        try:
            if document_id:
                # Delete from ChromaDB
                self.vector_service.delete_document_chunks(document_id)
                
                # Delete from file cache
                cache_file = os.path.join(self.embeddings_cache_dir, f"{document_id}.json")
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                    print(f"Cleared embeddings cache for document {document_id}")
            else:
                # Clear all cache files
                for filename in os.listdir(self.embeddings_cache_dir):
                    if filename.endswith('.json'):
                        os.remove(os.path.join(self.embeddings_cache_dir, filename))
                
                # Reset ChromaDB collection
                self.vector_service.reset_collection()
                print("Cleared all embeddings cache")
        except Exception as e:
            print(f"Error clearing embeddings cache: {e}")