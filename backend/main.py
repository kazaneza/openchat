from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
from dotenv import load_dotenv
import uvicorn
import traceback
import os

# Import services and models
from services.openai_service import OpenAIService
from services.document_service import DocumentService
from services.embedding_service import EmbeddingService
from services.query_service import QueryService
from services.vector_service import VectorService
from services.prompt_service import PromptService
from services.language_service import LanguageService
from models.organization import OrganizationModel
from models.user import UserModel

# Load environment variables
load_dotenv()

# Initialize services
openai_service = OpenAIService()
document_service = DocumentService()
vector_service = VectorService()
prompt_service = PromptService()
language_service = LanguageService()
embedding_service = EmbeddingService(openai_service, vector_service)
query_service = QueryService(openai_service, document_service, embedding_service, vector_service, prompt_service)

# Initialize models
organization_model = OrganizationModel()
user_model = UserModel()

app = FastAPI(title="PDF Chat API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://localhost:5173"],  # Vite dev server (HTTP and HTTPS)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Admin endpoints
@app.get("/api/admin/organizations")
async def admin_get_organizations():
    """Get all organizations with users for admin"""
    organizations = organization_model.load_all()
    users = user_model.load_all()
    
    print(f"Available users: {list(users.keys())}")
    
    # Add users to each organization
    for org_id, org in organizations.items():
        org_users = [user for user in users.values() if user['organization_id'] == org_id]
        print(f"Organization {org_id} has users: {[u['id'] for u in org_users]}")
        org['users'] = org_users
    
    return {"organizations": list(organizations.values())}

@app.post("/api/admin/organizations")
async def admin_create_organization(name: str = Form(...), prompt: str = Form(...)):
    """Create a new organization (admin only)"""
    organization = organization_model.create(name, prompt)
    organization["users"] = []  # Add empty users list for admin response
    
    return {"organization": organization}

@app.delete("/api/admin/organizations/{org_id}")
async def admin_delete_organization(org_id: str):
    """Delete an organization and all its users (admin only)"""
    organization = organization_model.get_by_id(org_id)
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Delete associated files
    for doc in organization["documents"]:
        document_service.delete_document_file(doc["file_path"])
        # Delete embeddings
        embedding_service.delete_document_embeddings(doc["id"])
    
    # Delete all organization embeddings from ChromaDB
    embedding_service.delete_organization_embeddings(org_id)
    
    # Delete users belonging to this organization
    users = user_model.load_all()
    users_to_delete = [user_id for user_id, user in users.items() if user['organization_id'] == org_id]
    for user_id in users_to_delete:
        user_model.delete(user_id)
    
    # Remove organization
    organization_model.delete(org_id)
    
    return {"message": "Organization and all associated users deleted successfully"}

@app.post("/api/admin/users")
async def admin_create_user(
    email: str = Form(...), 
    password: str = Form(...), 
    organization_id: str = Form(...),
    role: str = Form(...),
    must_change_password: bool = Form(True)
):
    """Create a new user (admin only)"""
    if not organization_model.get_by_id(organization_id):
        raise HTTPException(status_code=404, detail="Organization not found")
    
    try:
        user = user_model.create(email, password, organization_id, role, must_change_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Return user without password
    user_response = user.copy()
    del user_response['password']
    
    return {"user": user_response}

@app.delete("/api/admin/users/{user_id}")
async def admin_delete_user(user_id: str):
    """Delete a user (admin only)"""
    if not user_model.delete(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User deleted successfully"}

# Authentication endpoints
@app.post("/api/auth/login")
async def authenticate_user(email: str = Form(...), password: str = Form(...)):
    """Authenticate user and return organization data"""
    user = user_model.authenticate(email, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Get user's organization
    organization = organization_model.get_by_id(user['organization_id'])
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return {
        "user": user,
        "organization": organization
    }

@app.post("/api/auth/change-password")
async def change_password(
    user_id: str = Form(...),
    current_password: str = Form(...),
    new_password: str = Form(...)
):
    """Change user password"""
    user = user_model.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify current password
    if not user_model.verify_password(current_password, user['password']):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Update password and clear must_change_password flag
    updated_user = user_model.update(user_id, {
        'password': new_password,
        'must_change_password': False
    })
    
    # Return user without password
    user_response = updated_user.copy()
    del user_response['password']
    
    return {"message": "Password changed successfully", "user": user_response}

@app.get("/api/organizations")
async def get_organizations():
    """Get all organizations"""
    organizations = organization_model.load_all()
    return {"organizations": list(organizations.values())}

@app.post("/api/organizations")
async def create_organization(name: str = Form(...), prompt: str = Form(...)):
    """Create a new organization"""
    organization = organization_model.create(name, prompt)
    
    return {"organization": organization}

@app.post("/api/organizations/{org_id}/upload")
async def upload_documents(org_id: str, files: List[UploadFile] = File(...), user_id: str = Form(...)):
    """Upload PDF documents to an organization"""
    print(f"Upload request - org_id: {org_id}, user_id: {user_id}")
    print(f"Number of files: {len(files)}")
    
    organization = organization_model.get_by_id(org_id)
    if not organization:
        print(f"Organization {org_id} not found")
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Verify user belongs to this organization
    user = user_model.get_by_id(user_id)
    print(f"User found: {user is not None}")
    if not user or user['organization_id'] != org_id:
        print(f"Access denied - user org: {user['organization_id'] if user else 'None'}, requested org: {org_id}")
        raise HTTPException(status_code=403, detail="Access denied")
    
    uploaded_docs = []
    
    for file in files:
        print(f"Processing file: {file.filename}")
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Read file content
        content = await file.read()
        print(f"File size: {len(content)} bytes")
        
        # Extract text from PDF
        try:
            text_content = document_service.extract_text_from_pdf(content)
            print(f"Extracted text length: {len(text_content)} characters")
        except Exception as e:
            print(f"PDF extraction error: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        
        # Chunk the text
        chunks = document_service.chunk_text(text_content)
        print(f"Created {len(chunks)} chunks")
        
        # Save document
        try:
            document = document_service.save_document(content, file.filename, text_content, chunks)
            print(f"Document saved: {document['id']}")
        except Exception as e:
            print(f"File save error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
        
        # Generate embeddings for the document
        document = embedding_service.generate_embeddings_for_document(document, org_id)
        
        # Add document to organization
        organization_model.add_document(org_id, document)
        uploaded_docs.append(document)
        print(f"Document added: {file.filename}")
    
    # Get updated organization
    updated_organization = organization_model.get_by_id(org_id)
    print(f"Upload complete. Total documents: {updated_organization['document_count']}")
    
    return {"uploaded_documents": uploaded_docs}

@app.post("/api/organizations/{org_id}/chat")
async def chat_with_documents(org_id: str, message: str = Form(...), user_id: str = Form(...)):
    """Chat with the documents in an organization"""
    try:
        organization = organization_model.get_by_id(org_id)
        if not organization:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        # Verify user belongs to this organization
        user = user_model.get_by_id(user_id)
        if not user or user['organization_id'] != org_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Process query using the new query service
        ai_response = query_service.process_query(message, organization, {"user_id": user_id})
        
        # Update organization stats
        organization_model.increment_chat_count(org_id)
        
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
        organization = organization_model.get_by_id(org_id)
        if not organization:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        # Process query using the new query service
        ai_response = query_service.process_query(message, organization)
        
        # Update organization stats
        organization_model.increment_chat_count(org_id)
        
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
    organization = organization_model.get_by_id(org_id)
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return {"organization": organization}

@app.delete("/api/organizations/{org_id}/documents/{doc_id}")
async def delete_document(org_id: str, doc_id: str, user_id: str = Form(...)):
    """Delete a document from an organization"""
    print(f"Delete document request - org_id: {org_id}, doc_id: {doc_id}, user_id: {user_id}")
    
    organization = organization_model.get_by_id(org_id)
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Verify user belongs to this organization
    user = user_model.get_by_id(user_id)
    if not user or user['organization_id'] != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Remove document from organization
    doc_to_delete = organization_model.remove_document(org_id, doc_id)
    if not doc_to_delete:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete the physical file
    document_service.delete_document_file(doc_to_delete["file_path"])
    
    # Delete embeddings from ChromaDB and cache
    embedding_service.delete_document_embeddings(doc_id)
    
    print(f"Document {doc_to_delete['filename']} deleted successfully")
    
    return {"message": "Document deleted successfully"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)