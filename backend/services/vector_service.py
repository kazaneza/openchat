import chromadb
from chromadb.config import Settings
import os
import uuid
from typing import List, Dict, Optional, Any
import json
from datetime import datetime

class VectorService:
    def __init__(self, persist_directory: str = "data/chroma_db"):
        """Initialize ChromaDB client with persistent storage"""
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Create or get collection for document embeddings
        self.collection = self.client.get_or_create_collection(
            name="document_embeddings",
            metadata={"description": "Document chunks with embeddings for RAG"}
        )
        
        print(f"ChromaDB initialized with {self.collection.count()} existing embeddings")
    
    def add_document_chunks(self, document_id: str, document_name: str, chunks: List[str], embeddings: List[List[float]], organization_id: str) -> bool:
        """Add document chunks with embeddings to ChromaDB"""
        try:
            if len(chunks) != len(embeddings):
                print(f"Warning: Chunk count ({len(chunks)}) doesn't match embedding count ({len(embeddings)})")
                return False
            
            # Prepare data for ChromaDB
            ids = []
            documents = []
            metadatas = []
            embedding_vectors = []
            
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_id = f"{document_id}_chunk_{i}"
                
                ids.append(chunk_id)
                documents.append(chunk)
                metadatas.append({
                    "document_id": document_id,
                    "document_name": document_name,
                    "organization_id": organization_id,
                    "chunk_index": i,
                    "chunk_id": chunk_id,
                    "timestamp": datetime.now().isoformat(),
                    "token_count": len(chunk.split())  # Rough token estimate
                })
                embedding_vectors.append(embedding)
            
            # Add to ChromaDB
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embedding_vectors
            )
            
            print(f"Added {len(chunks)} chunks for document '{document_name}' to ChromaDB")
            return True
            
        except Exception as e:
            print(f"Error adding document chunks to ChromaDB: {e}")
            return False
    
    def search_similar_chunks(self, query_embedding: List[float], organization_id: str, top_k: int = 5, similarity_threshold: float = 0.1) -> List[Dict]:
        """Search for similar chunks using ChromaDB"""
        try:
            # Query ChromaDB for similar chunks
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where={"organization_id": organization_id},  # Filter by organization
                include=["documents", "metadatas", "distances"]
            )
            
            if not results['documents'] or not results['documents'][0]:
                return []
            
            # Process results
            similar_chunks = []
            documents = results['documents'][0]
            metadatas = results['metadatas'][0]
            distances = results['distances'][0]
            
            for doc, metadata, distance in zip(documents, metadatas, distances):
                # Convert distance to similarity score (ChromaDB uses cosine distance)
                similarity = 1 - distance
                
                if similarity >= similarity_threshold:
                    similar_chunks.append({
                        "text": doc,
                        "document_id": metadata["document_id"],
                        "document_name": metadata["document_name"],
                        "chunk_index": metadata["chunk_index"],
                        "chunk_id": metadata["chunk_id"],
                        "similarity": similarity,
                        "distance": distance,
                        "timestamp": metadata.get("timestamp"),
                        "token_count": metadata.get("token_count", 0)
                    })
            
            print(f"Found {len(similar_chunks)} similar chunks (threshold: {similarity_threshold})")
            return similar_chunks
            
        except Exception as e:
            print(f"Error searching ChromaDB: {e}")
            return []
    
    def delete_document_chunks(self, document_id: str) -> bool:
        """Delete all chunks for a specific document"""
        try:
            # Get all chunk IDs for this document
            results = self.collection.get(
                where={"document_id": document_id},
                include=["metadatas"]
            )
            
            if results['ids']:
                # Delete all chunks for this document
                self.collection.delete(
                    where={"document_id": document_id}
                )
                print(f"Deleted {len(results['ids'])} chunks for document {document_id}")
                return True
            else:
                print(f"No chunks found for document {document_id}")
                return False
                
        except Exception as e:
            print(f"Error deleting document chunks: {e}")
            return False
    
    def delete_organization_chunks(self, organization_id: str) -> bool:
        """Delete all chunks for an organization"""
        try:
            results = self.collection.get(
                where={"organization_id": organization_id},
                include=["metadatas"]
            )
            
            if results['ids']:
                self.collection.delete(
                    where={"organization_id": organization_id}
                )
                print(f"Deleted {len(results['ids'])} chunks for organization {organization_id}")
                return True
            else:
                print(f"No chunks found for organization {organization_id}")
                return False
                
        except Exception as e:
            print(f"Error deleting organization chunks: {e}")
            return False
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the vector collection"""
        try:
            total_count = self.collection.count()
            
            # Get sample of metadata to analyze
            sample_results = self.collection.get(
                limit=min(100, total_count),
                include=["metadatas"]
            )
            
            # Analyze organizations and documents
            organizations = set()
            documents = set()
            
            for metadata in sample_results.get('metadatas', []):
                organizations.add(metadata.get('organization_id', 'unknown'))
                documents.add(metadata.get('document_id', 'unknown'))
            
            return {
                "total_chunks": total_count,
                "organizations_count": len(organizations),
                "documents_count": len(documents),
                "sample_size": len(sample_results.get('metadatas', []))
            }
            
        except Exception as e:
            print(f"Error getting collection stats: {e}")
            return {"error": str(e)}
    
    def reset_collection(self) -> bool:
        """Reset the entire collection (use with caution!)"""
        try:
            self.client.delete_collection("document_embeddings")
            self.collection = self.client.get_or_create_collection(
                name="document_embeddings",
                metadata={"description": "Document chunks with embeddings for RAG"}
            )
            print("ChromaDB collection reset successfully")
            return True
        except Exception as e:
            print(f"Error resetting collection: {e}")
            return False