from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import json
import os
import uuid
from datetime import datetime
from typing import List, Optional
import PyPDF2
from io import BytesIO
import uvicorn
import tiktoken
import re
import traceback

# Try to import OpenAI, handle if not available
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("OpenAI package not available. Install with: pip install openai")

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = None
if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        print("OpenAI client initialized successfully")
    except Exception as e:
        print(f"Failed to initialize OpenAI client: {e}")
        client = None
else:
    print("OpenAI API key not found in environment variables")

app = FastAPI(title="PDF Chat API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://localhost:5173"],  # Vite dev server (HTTP and HTTPS)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data storage paths
ORGANIZATIONS_FILE = "data/organizations.json"
UPLOADS_DIR = "data/uploads"

# Ensure directories exist
os.makedirs("data", exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

def load_organizations():
    """Load organizations from JSON file"""
    if os.path.exists(ORGANIZATIONS_FILE):
        with open(ORGANIZATIONS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_organizations(organizations):
    """Save organizations to JSON file"""
    with open(ORGANIZATIONS_FILE, 'w') as f:
        json.dump(organizations, f, indent=2)

def chunk_text(text: str, max_tokens: int = 1000) -> List[str]:
    """Split text into chunks that fit within token limits"""
    try:
        encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding
        
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
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
                        test_sentence = temp_chunk + sentence + "."
                        if len(encoding.encode(test_sentence)) <= max_tokens:
                            temp_chunk = test_sentence
                        else:
                            if temp_chunk:
                                chunks.append(temp_chunk.strip())
                            temp_chunk = sentence + "."
                    
                    if temp_chunk:
                        chunks.append(temp_chunk.strip())
                    current_chunk = ""
                else:
                    current_chunk = paragraph
        
        # Add the last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return [chunk for chunk in chunks if chunk.strip()]
    
    except Exception as e:
        # Fallback: simple character-based chunking
        chunk_size = max_tokens * 3  # Rough estimate: 1 token ≈ 3-4 characters
        return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

def find_relevant_chunks(chunks: List[str], query: str, max_chunks: int = 3) -> List[str]:
    """Find the most relevant chunks for a query using simple keyword matching"""
    query_words = set(query.lower().split())
    
    chunk_scores = []
    for i, chunk in enumerate(chunks):
        chunk_words = set(chunk.lower().split())
        # Simple scoring based on word overlap
        score = len(query_words.intersection(chunk_words))
        chunk_scores.append((score, i, chunk))
    
    # Sort by score and return top chunks
    chunk_scores.sort(key=lambda x: x[0], reverse=True)
    return [chunk for score, i, chunk in chunk_scores[:max_chunks] if score > 0]

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text content from PDF"""
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(file_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process PDF: {str(e)}")

def generate_ai_response(system_prompt: str, user_message: str, document_context: str) -> str:
    """Generate AI response using OpenAI GPT"""
    try:
        if not client:
            return "OpenAI API key is not configured. Please set your OPENAI_API_KEY in the .env file."
        
        # Prepare the context with document information
        context_prompt = f"""
{system_prompt}

Based on the following document excerpts, please answer the user's question. If the answer cannot be found in the provided documents, please say so clearly.

Document Context:
{document_context}
"""

        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            messages=[
                {"role": "system", "content": context_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=int(os.getenv("MAX_TOKENS", "1000")),
            temperature=float(os.getenv("TEMPERATURE", "0.7"))
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI API Error: {str(e)}")
        traceback.print_exc()
        return f"Sorry, there was an error processing your request: {str(e)}"

@app.get("/api/organizations")
async def get_organizations():
    """Get all organizations"""
    organizations = load_organizations()
    return {"organizations": list(organizations.values())}

@app.post("/api/organizations")
async def create_organization(name: str = Form(...), prompt: str = Form(...)):
    """Create a new organization"""
    organizations = load_organizations()
    
    org_id = str(uuid.uuid4())
    organization = {
        "id": org_id,
        "name": name,
        "prompt": prompt,
        "documents": [],
        "created_at": datetime.now().isoformat(),
        "document_count": 0
    }
    
    organizations[org_id] = organization
    save_organizations(organizations)
    
    return {"organization": organization}

@app.post("/api/organizations/{org_id}/upload")
async def upload_documents(org_id: str, files: List[UploadFile] = File(...)):
    """Upload PDF documents to an organization"""
    organizations = load_organizations()
    
    if org_id not in organizations:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    uploaded_docs = []
    
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Read file content
        content = await file.read()
        
        # Extract text from PDF
        text_content = extract_text_from_pdf(content)
        
        # Save file
        file_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOADS_DIR, f"{file_id}.pdf")
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Create document record
        document = {
            "id": file_id,
            "filename": file.filename,
            "file_path": file_path,
            "text_content": text_content,
            "chunks": chunk_text(text_content),  # Pre-chunk the document
            "uploaded_at": datetime.now().isoformat(),
            "size": len(content)
        }
        
        organizations[org_id]["documents"].append(document)
        uploaded_docs.append(document)
    
    organizations[org_id]["document_count"] = len(organizations[org_id]["documents"])
    save_organizations(organizations)
    
    return {"uploaded_documents": uploaded_docs}

@app.post("/api/organizations/{org_id}/chat")
async def chat_with_documents(org_id: str, message: str = Form(...)):
    """Chat with the documents in an organization"""
    try:
        organizations = load_organizations()
        
        if org_id not in organizations:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        organization = organizations[org_id]
        
        if not organization["documents"]:
            raise HTTPException(status_code=400, detail="No documents uploaded for this organization")
        
        # Collect all chunks from all documents
        all_chunks = []
        for doc in organization["documents"]:
            doc_chunks = doc.get("chunks", [])
            if not doc_chunks:  # Fallback for old documents without chunks
                doc_chunks = chunk_text(doc["text_content"])
            
            # Add document context to each chunk
            for chunk in doc_chunks:
                all_chunks.append(f"[From {doc['filename']}]\n{chunk}")
        
        # Find relevant chunks for the user's question
        relevant_chunks = find_relevant_chunks(all_chunks, message)
        
        if not relevant_chunks:
            # If no relevant chunks found, use first few chunks as fallback
            relevant_chunks = all_chunks[:3]
        
        # Combine relevant chunks
        combined_context = "\n\n---\n\n".join(relevant_chunks)
        
        # Generate AI response using OpenAI
        system_prompt = organization["prompt"]
        
        # Generate AI-powered response
        ai_response = generate_ai_response(system_prompt, message, combined_context)
        
        return {
            "response": ai_response,
            "document_count": len(organization["documents"]),
            "organization_name": organization["name"]
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in chat_with_documents: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/chat/{org_id}")
async def public_chat_endpoint(org_id: str, message: str = Form(...)):
    """Public chat endpoint for external use"""
    try:
        organizations = load_organizations()
        
        if org_id not in organizations:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        organization = organizations[org_id]
        
        if not organization["documents"]:
            # If no documents, provide a basic response
            system_prompt = organization["prompt"]
            ai_response = generate_ai_response(system_prompt, message, "No documents have been uploaded to this organization yet.")
            
            return {
                "response": ai_response,
                "organization": organization["name"],
                "endpoint": f"/chat/{org_id}"
            }
        
        # Collect all chunks from all documents
        all_chunks = []
        for doc in organization["documents"]:
            try:
                doc_chunks = doc.get("chunks", [])
                if not doc_chunks and "text_content" in doc:  # Fallback for old documents without chunks
                    doc_chunks = chunk_text(doc["text_content"])
                
                # Add document context to each chunk
                for chunk in doc_chunks:
                    if chunk.strip():  # Only add non-empty chunks
                        all_chunks.append(f"[From {doc['filename']}]\n{chunk}")
            except Exception as e:
                print(f"Error processing document {doc.get('filename', 'unknown')}: {str(e)}")
                continue
        
        # If no valid chunks found, use a fallback message
        if not all_chunks:
            system_prompt = organization["prompt"]
            ai_response = generate_ai_response(system_prompt, message, "The documents in this organization could not be processed properly.")
            
            return {
                "response": ai_response,
                "organization": organization["name"],
                "endpoint": f"/chat/{org_id}"
            }
        
        # Find relevant chunks for the user's question
        relevant_chunks = find_relevant_chunks(all_chunks, message)
        
        if not relevant_chunks:
            # If no relevant chunks found, use first few chunks as fallback
            relevant_chunks = all_chunks[:3]
        
        # Combine relevant chunks
        combined_context = "\n\n---\n\n".join(relevant_chunks)
        
        # Generate AI response using OpenAI
        system_prompt = organization["prompt"]
        
        # Generate AI-powered response
        ai_response = generate_ai_response(system_prompt, message, combined_context)
        
        return {
            "response": ai_response,
            "organization": organization["name"],
            "endpoint": f"/chat/{org_id}"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in public_chat_endpoint: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/organizations/{org_id}")
async def get_organization(org_id: str):
    """Get a specific organization"""
    organizations = load_organizations()
    
    if org_id not in organizations:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return {"organization": organizations[org_id]}

@app.delete("/api/organizations/{org_id}")
async def delete_organization(org_id: str):
    """Delete an organization and its documents"""
    organizations = load_organizations()
    
    if org_id not in organizations:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Delete associated files
    organization = organizations[org_id]
    for doc in organization["documents"]:
        if os.path.exists(doc["file_path"]):
            os.remove(doc["file_path"])
    
    # Remove organization
    del organizations[org_id]
    save_organizations(organizations)
    
    return {"message": "Organization deleted successfully"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)