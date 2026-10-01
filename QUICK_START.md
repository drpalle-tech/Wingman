# Wingman Copilot - Quick Start Guide

**RAG-Powered Document Q&A System**

## Prerequisites

- Python 3.10+ 
- Node.js 16+
- Azure Account with:
  - Azure OpenAI deployment (Llama-3.3-70B-Instruct)
  - Azure Storage Account
  - Azure AI Search service

---

## Installation

### 1. Backend Setup

```powershell
# Navigate to backend folder
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend_requirements.txt
```

### 2. Backend Configuration

```powershell
# Copy template
Copy-Item .env.template -Path .env

# Edit .env with your Azure credentials
notepad .env
```

Fill in these values from Azure:
- `AZURE_ENDPOINT`: From Azure OpenAI deployment
- `AZURE_API_KEY`: From Azure OpenAI deployment
- `AZURE_STORAGE_CONNECTION_STRING`: From Storage Account
- `SEARCH_ENDPOINT`: From Azure AI Search
- `SEARCH_ADMIN_KEY`: From Azure AI Search

### 3. Backend Start

```powershell
# From backend folder with venv activated
python main.py
```

✅ API should run at: `http://localhost:8000`

### 4. Frontend Setup

```powershell
# Open new terminal, go to frontend folder
cd frontend

# Install dependencies
npm install

# Install TypeScript and Tailwind
npm install -D typescript tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

### 5. Frontend Start

```powershell
# From frontend folder
npm run dev
```

✅ App should open at: `http://localhost:3000`

---

## Usage

### Upload Documents
1. Click **Documents** tab
2. Click **+ Upload PDF**
3. Select a PDF file
4. Wait for "Document uploaded and indexed successfully!"

### Ask Questions
1. Click **Chat** tab
2. Type your question (e.g., "What is mentioned about X?")
3. Click **Send**
4. Get RAG-enhanced answer with source documents

### Delete Documents
1. Go to **Documents** tab
2. Click **Delete** next to any document

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Check API status |
| `/chat` | POST | Send query, get RAG response |
| `/upload` | POST | Upload PDF document |
| `/documents` | GET | List all documents |
| `/documents/{name}` | DELETE | Delete document |

### Example Chat Request
```json
{
  "query": "What is the main topic?",
  "conversation_id": "session-1"
}
```

### Example Chat Response
```json
{
  "response": "Based on the documents...",
  "sources": ["document1.pdf", "document2.pdf"],
  "conversation_id": "session-1"
}
```

---

## Features

✅ **PDF Upload** - Upload and automatically index PDF documents
✅ **Smart Search** - Hybrid chunking (fixed-size + semantic)
✅ **RAG Responses** - Answers grounded in your documents
✅ **Source Citations** - See which documents answer came from
✅ **Browser History** - Chat history saved in browser session
✅ **Clean UI** - Modern React + Tailwind interface

---

## Troubleshooting

### Backend won't start
```
❌ Error: AZURE_STORAGE_CONNECTION_STRING not set
✅ Solution: Fill .env file with Azure credentials
```

### Frontend can't reach backend
```
❌ Error: Network error when accessing localhost:8000
✅ Solution: Make sure backend is running first (step 3)
```

### Upload fails
```
❌ Error: Only PDF files are supported
✅ Solution: Make sure file is .pdf (not .doc, .txt, etc)
```

### No documents found in search
```
❌ Issue: Questions get "I couldn't find any relevant information"
✅ Solution: Upload more documents or use clearer keywords
```

---

## Architecture

```
Frontend (React + Vite + Tailwind)
    ↓
    ├─→ /chat (send query)
    ├─→ /upload (upload PDF)
    └─→ /documents (list/delete)
    ↓
Backend (FastAPI + Python)
    ↓
    ├─→ RAG Engine (process query)
    ├─→ Azure Storage (store PDFs)
    ├─→ Azure AI Search (index chunks)
    └─→ Azure OpenAI (generate responses)
```

---

## Next Steps

- Add authentication
- Deploy to Azure Container Apps
- Add more document types (Word, Excel, etc)
- Implement persistent chat history
- Add admin dashboard

---

## Support

For issues:
1. Check logs in terminal
2. Verify .env credentials
3. Ensure Azure services are running
4. Check network connectivity

---

**Version: 1.0.0**
**Built with: FastAPI, React, Vite, Tailwind, Azure**
