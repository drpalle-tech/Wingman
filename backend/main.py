"""
Wingman backend: code review and generation for developers, plus document Q&A.
Runs locally on each developer machine.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from assist.router import router as assist_router  # noqa: E402
from cost_tracker import CostTracker  # noqa: E402
from errors import register_error_handlers  # noqa: E402
from llm_client import LLMClient  # noqa: E402
from rag import RAGEngine  # noqa: E402

VERSION = "2.0.0"
DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"


def _document_services():
    """Storage and Search are only needed for document Q&A; code features run without them."""
    configured = os.getenv("AZURE_STORAGE_CONNECTION_STRING") and os.getenv("SEARCH_ENDPOINT") and os.getenv("SEARCH_ADMIN_KEY")
    if not configured:
        logger.info("Azure Storage/Search not configured; document features are disabled")
        return None, None
    from search import AzureSearchManager
    from storage import AzureStorageManager

    return AzureStorageManager(), AzureSearchManager()


llm = LLMClient()
cost_tracker = CostTracker(llm.model, Path(os.getenv("USAGE_DB_PATH", Path(__file__).parent / "data" / "usage.db")))
storage_manager, search_manager = _document_services()
rag_engine = RAGEngine(storage_manager, search_manager, llm)

app = FastAPI(
    title="Wingman API",
    description="Code review and generation for developers, plus document Q&A",
    version=VERSION,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app)
app.state.llm = llm
app.state.cost_tracker = cost_tracker
app.include_router(assist_router)


class ChatRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    sources: list
    conversation_id: str
    cost: Optional[dict] = None


class HealthCheck(BaseModel):
    status: str
    version: str
    model: str
    documents_enabled: bool


def _require_documents() -> None:
    if storage_manager is None:
        raise HTTPException(503, "Document features are not configured. Set the Azure Storage and Search settings.")


@app.get("/health", response_model=HealthCheck)
async def health_check():
    return {
        "status": "healthy",
        "version": VERSION,
        "model": llm.model,
        "documents_enabled": storage_manager is not None,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Answers a question, grounded in uploaded documents when any match."""
    logger.info("Chat request (%d chars)", len(request.query))
    response, sources, token_usage = await rag_engine.get_response(request.query)
    cost_info = cost_tracker.track_request(token_usage["input_tokens"], token_usage["output_tokens"], task="docs")
    return {
        "response": response,
        "sources": sources,
        "conversation_id": request.conversation_id or "session-1",
        "cost": cost_info,
    }


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Uploads a PDF, then chunks and indexes it for document Q&A."""
    _require_documents()
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    logger.info("Uploading file: %s", file.filename)
    contents = await file.read()
    await storage_manager.upload_file(file.filename, contents)
    await rag_engine.process_and_index_document(file.filename, contents)
    return {
        "status": "success",
        "filename": file.filename,
        "message": "Document uploaded and indexed successfully",
    }


@app.get("/documents")
async def list_documents():
    if storage_manager is None:
        return {"documents": [], "count": 0, "enabled": False}
    documents = await storage_manager.list_documents()
    return {"documents": documents, "count": len(documents), "enabled": True}


@app.delete("/documents/{document_name}")
async def delete_document(document_name: str):
    _require_documents()
    logger.info("Deleting document: %s", document_name)
    await storage_manager.delete_file(document_name)
    return {"status": "success", "message": f"Document {document_name} deleted"}


@app.get("/usage")
async def get_usage():
    return cost_tracker.get_current_usage()


@app.get("/usage/history")
async def get_usage_history(limit: int = 10):
    requests = cost_tracker.get_request_history(limit)
    return {"requests": requests, "count": len(requests)}


@app.get("/usage/report")
async def get_usage_report():
    return cost_tracker.export_usage_report()


@app.post("/usage/reset")
async def reset_usage():
    return cost_tracker.reset_tracking()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        log_level="info",
    )
