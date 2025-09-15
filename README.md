# PDF Chat System

An AI-powered PDF chat system built with FastAPI and React that allows you to create organizations, upload PDF documents, and chat with them using OpenAI's GPT models.

## Features

- 🏢 **Organization Management**: Create and manage multiple organizations
- 📄 **PDF Processing**: Upload and process multiple PDF documents
- 🤖 **AI-Powered Chat**: Chat with your documents using OpenAI GPT-4
- 🎨 **Beautiful UI**: Modern rose-themed interface with glass-morphism effects
- 💾 **JSON Storage**: Simple file-based storage for organizations and metadata
- 🔒 **Custom Prompts**: Configure custom system prompts for each organization

## Setup

### Prerequisites

- Python 3.8+
- Node.js 16+
- OpenAI API Key

### Backend Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the root directory:
```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4
MAX_TOKENS=1000
TEMPERATURE=0.7
MAX_CONTEXT_LENGTH=8000
```

3. Start the FastAPI server:
```bash
cd backend
python start.py
```

The API will be available at `http://localhost:8000`

### Frontend Setup

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Usage

1. **Create Organization**: Create a new organization with a custom system prompt
2. **Upload Documents**: Upload PDF documents to your organization
3. **Start Chatting**: Ask questions about your documents and get AI-powered responses

## API Endpoints

- `GET /api/organizations` - Get all organizations
- `POST /api/organizations` - Create a new organization
- `GET /api/organizations/{org_id}` - Get organization details
- `POST /api/organizations/{org_id}/upload` - Upload documents
- `POST /api/organizations/{org_id}/chat` - Chat with documents
- `DELETE /api/organizations/{org_id}` - Delete organization

## Configuration

You can customize the AI behavior by modifying the environment variables:

- `OPENAI_MODEL`: The OpenAI model to use (default: gpt-4)
- `MAX_TOKENS`: Maximum tokens for AI responses (default: 1000)
- `TEMPERATURE`: AI response creativity (0-1, default: 0.7)
- `MAX_CONTEXT_LENGTH`: Maximum document context length (default: 8000)

## Data Storage

Organizations and metadata are stored in JSON files:
- `data/organizations.json` - Organization data
- `data/uploads/` - Uploaded PDF files