"""
RAG Engine with Token Tracking
Retrieval-Augmented Generation over uploaded PDFs
Implements hybrid chunking and document processing
Supports both RAG mode (with documents) and General Q&A mode (without documents)
"""

import io
import uuid
from datetime import datetime
import PyPDF2
import logging

from llm_client import LLMClient

logger = logging.getLogger(__name__)

class RAGEngine:
    """Main RAG Engine with hybrid chunking and token tracking"""

    def __init__(self, storage_manager, search_manager, llm: LLMClient):
        self.storage_manager = storage_manager
        self.search_manager = search_manager
        self.llm = llm
        self.top_k = 3  # Number of documents to retrieve
    
    async def process_and_index_document(self, filename: str, content: bytes) -> None:
        """
        Process PDF document with hybrid chunking and index in search service
        """
        try:
            logger.info(f"Processing document: {filename}")
            
            # Extract text from PDF
            text = await self._extract_pdf_text(content)
            logger.info(f"Extracted {len(text)} characters from PDF")
            
            # Hybrid chunking: fixed size + semantic
            chunks = await self._hybrid_chunk_text(text)
            logger.info(f"Created {len(chunks)} chunks")
            
            # Create searchable documents
            documents = []
            for idx, chunk in enumerate(chunks):
                doc = {
                    "id": str(uuid.uuid4()),
                    "content": chunk,
                    "source_document": filename,
                    "chunk_index": idx,
                    "created_at": datetime.utcnow().isoformat()
                }
                documents.append(doc)
            
            # Index documents
            await self.search_manager.index_documents(documents)
            logger.info(f"Indexed {len(documents)} chunks for {filename}")
            
        except Exception as e:
            logger.error(f"Document processing error: {str(e)}")
            raise
    
    async def _extract_pdf_text(self, content: bytes) -> str:
        """Extract text from PDF"""
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
            text = ""
            
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
        except Exception as e:
            logger.error(f"PDF extraction error: {str(e)}")
            raise
    
    async def _hybrid_chunk_text(self, text: str, fixed_size: int = 1000, overlap: int = 200) -> list:
        """
        Hybrid chunking strategy:
        1. Split by sentences first (semantic awareness)
        2. Group sentences into fixed-size chunks
        3. Add overlap for context
        """
        try:
            # Split by sentences (simple approach - split by '. ' and '\n\n')
            sentences = []
            current = ""
            
            for char in text:
                current += char
                if current.endswith(". ") or current.endswith(".\n"):
                    sentences.append(current.strip())
                    current = ""
            
            if current.strip():
                sentences.append(current.strip())
            
            logger.info(f"Split into {len(sentences)} sentences")
            
            # Group sentences into chunks
            chunks = []
            current_chunk = ""
            
            for sentence in sentences:
                if len(current_chunk) + len(sentence) < fixed_size:
                    current_chunk += " " + sentence
                else:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence
            
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            
            # Add overlap between chunks for better context
            overlapped_chunks = []
            for i, chunk in enumerate(chunks):
                if i > 0 and overlap > 0:
                    # Add end of previous chunk
                    prev_end = chunks[i-1][-overlap:] if len(chunks[i-1]) > overlap else chunks[i-1]
                    overlapped_chunks.append(prev_end + " " + chunk)
                else:
                    overlapped_chunks.append(chunk)
            
            return overlapped_chunks
        except Exception as e:
            logger.error(f"Chunking error: {str(e)}")
            raise
    
    async def get_response(self, query: str) -> tuple:
        """
        Get RAG-enhanced response with token tracking
        Returns: (response_text, source_documents, token_usage)
        
        Modes:
        1. RAG Mode: If documents found, use them for context
        2. General Q&A Mode: If no documents, answer general question
        """
        try:
            search_results = []
            if self.search_manager is not None:
                search_results = await self.search_manager.search_documents(query, top_k=self.top_k)
            
            if search_results:
                # RAG Mode: Use documents for context
                logger.info(f"Found {len(search_results)} documents - using RAG mode")
                answer, sources, token_usage = await self._generate_rag_response(query, search_results)
                return answer, sources, token_usage
            else:
                # General Q&A Mode: Answer general question without documents
                logger.info(f"No documents found - using general Q&A mode")
                answer, token_usage = await self._generate_general_response(query)
                return answer, [], token_usage
            
        except Exception as e:
            logger.error(f"Response generation error: {str(e)}")
            raise
    
    async def _generate_rag_response(self, query: str, search_results: list) -> tuple:
        """Generate response using RAG with document context and token tracking"""
        try:
            # Build context from search results
            context = "\n\n".join([
                f"[Document: {result['source_document']}, Chunk {result['chunk_index']}]\n{result['content']}"
                for result in search_results
            ])
            
            # Prepare prompt
            system_prompt = """You are a helpful assistant that answers questions based on provided documents.
Always be accurate and cite which document(s) you're referencing.
If information is not in the documents, say so clearly."""
            
            user_prompt = f"""Based on the following documents, answer this question: {query}

DOCUMENTS:
{context}

Please provide a clear, concise answer based on the documents above."""
            
            completion = await self.llm.complete(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "chat",
            )
            answer = completion.text
            token_usage = completion.usage.as_dict()

            # Extract sources
            sources = list(set([result['source_document'] for result in search_results]))

            logger.info(f"Generated RAG response using {len(sources)} sources - Tokens: {token_usage}")
            return answer, sources, token_usage
            
        except Exception as e:
            logger.error(f"RAG response generation error: {str(e)}")
            raise
    
    async def _generate_general_response(self, query: str) -> tuple:
        """Generate general response without documents (fallback mode) with token tracking"""
        try:
            # Prepare prompt for general Q&A
            system_prompt = """You are a helpful technical assistant. 
Answer questions clearly and concisely.
If you don't know something, be honest about it."""
            
            user_prompt = f"""Please answer this question: {query}"""
            
            completion = await self.llm.complete(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "chat",
            )
            answer = completion.text
            token_usage = completion.usage.as_dict()

            logger.info(f"Generated general Q&A response - Tokens: {token_usage}")
            return answer, token_usage
            
        except Exception as e:
            logger.error(f"General response generation error: {str(e)}")
            raise
