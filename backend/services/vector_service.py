"""
Modern Vector Database Service using ChromaDB
Provides organization-isolated vector storage and retrieval
"""
import os
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import uuid

class VectorService:
    def __init__(self, persist_directory: str = "data/chroma_db"):
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Dictionary to cache collection references
        self._collections = {}
    
    def get_collection(self, organization_id: str):
        """Get or create a collection for an organization"""
        if organization_id not in self._collections:
            collection_name = f"org_{organization_id}"
            try:
                collection = self.client.get_or_create_collection(
                    name=collection_name,
                    metadata={"organization_id": organization_id}
                )
                self._collections[organization_id] = collection
            except Exception as e:
                print(f"Error getting collection for org {organization_id}: {e}")
                # Create with a unique name if there's a conflict
                collection_name = f"org_{organization_id}_{uuid.uuid4().hex[:8]}"
                collection = self.client.get_or_create_collection(
                    name=collection_name,
                    metadata={"organization_id": organization_id}
                )
                self._collections[organization_id] = collection
        
        return self._collections[organization_id]
    
    def add_document_chunks(
        self,
        organization_id: str,
        document_id: str,
        chunks: List[Dict],
        embeddings: List[List[float]]
    ) -> bool:
        """Add document chunks to vector database"""
        try:
            collection = self.get_collection(organization_id)
            
            # Prepare data for ChromaDB
            ids = []
            documents = []
            metadatas = []
            embedding_list = []
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{document_id}_chunk_{i}"
                chunk_text = chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
                pages = chunk.get("pages", []) if isinstance(chunk, dict) else []
                
                ids.append(chunk_id)
                documents.append(chunk_text)
                metadatas.append({
                    "document_id": document_id,
                    "document_name": chunk.get("document_name", ""),
                    "chunk_index": i,
                    "pages": ",".join(map(str, pages)) if pages else ""
                })
                embedding_list.append(embeddings[i] if i < len(embeddings) else [])
            
            # Add to collection
            if embedding_list:
                collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                    embeddings=embedding_list
                )
            
            return True
        except Exception as e:
            print(f"Error adding document chunks to vector DB: {e}")
            return False
    
    def search_similar_chunks(
        self,
        organization_id: str,
        query_embedding: List[float],
        top_k: int = 5,
        min_similarity: float = 0.3
    ) -> List[Dict]:
        """Search for similar chunks using vector similarity"""
        try:
            collection = self.get_collection(organization_id)
            
            # Query the collection
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            
            # Format results
            similar_chunks = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    chunk_id = results['ids'][0][i]
                    distance = results['distances'][0][i] if 'distances' in results else 0.0
                    # Convert distance to similarity (ChromaDB uses distance, lower is better)
                    # For cosine distance: similarity = 1 - distance
                    similarity = max(0.0, 1.0 - distance) if distance > 0 else 1.0
                    
                    if similarity >= min_similarity:
                        metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                        document_text = results['documents'][0][i] if results['documents'] else ""
                        
                        # Parse pages from metadata
                        pages_str = metadata.get("pages", "")
                        pages = [int(p) for p in pages_str.split(",") if p.isdigit()] if pages_str else []
                        
                        similar_chunks.append({
                            "chunk_id": chunk_id,
                            "text": document_text,
                            "document_id": metadata.get("document_id", ""),
                            "document_name": metadata.get("document_name", ""),
                            "chunk_index": metadata.get("chunk_index", 0),
                            "pages": pages,
                            "similarity": similarity
                        })
            
            return similar_chunks
        except Exception as e:
            print(f"Error searching similar chunks: {e}")
            return []
    
    def delete_document_chunks(self, organization_id: str, document_id: str) -> bool:
        """Delete all chunks for a document"""
        try:
            collection = self.get_collection(organization_id)
            
            # Get all chunks for this document
            results = collection.get(
                where={"document_id": document_id}
            )
            
            if results['ids']:
                collection.delete(ids=results['ids'])
            
            return True
        except Exception as e:
            print(f"Error deleting document chunks: {e}")
            return False
    
    def delete_organization_data(self, organization_id: str) -> bool:
        """Delete all data for an organization"""
        try:
            collection = self.get_collection(organization_id)
            collection_name = collection.name
            
            # Delete the entire collection
            self.client.delete_collection(name=collection_name)
            
            # Remove from cache
            if organization_id in self._collections:
                del self._collections[organization_id]
            
            return True
        except Exception as e:
            print(f"Error deleting organization data: {e}")
            return False

