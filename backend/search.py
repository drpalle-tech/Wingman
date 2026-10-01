"""
Azure AI Search Manager
Handles document indexing and semantic search
"""

import os
import asyncio
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SearchField, SearchFieldDataType,
    SimpleField, SearchableField, VectorSearch,
    HnswAlgorithmConfiguration, VectorSearchProfile
)
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import AzureError
import logging

logger = logging.getLogger(__name__)

class AzureSearchManager:
    """Manages Azure AI Search operations"""
    
    def __init__(self):
        self.endpoint = os.getenv("SEARCH_ENDPOINT")
        self.admin_key = os.getenv("SEARCH_ADMIN_KEY")
        self.index_name = os.getenv("SEARCH_INDEX_NAME", "copilot-documents")
        
        if not self.endpoint or not self.admin_key:
            raise ValueError("SEARCH_ENDPOINT or SEARCH_ADMIN_KEY not set")
        
        self.credential = AzureKeyCredential(self.admin_key)
        self.index_client = SearchIndexClient(
            endpoint=self.endpoint,
            credential=self.credential
        )
        self.search_client = SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=self.credential
        )
        
        logger.info(f"Connected to Azure AI Search: {self.endpoint}")
        self._ensure_index_exists()
    
    def _ensure_index_exists(self):
        """Create search index if it doesn't exist"""
        try:
            # Check if index exists
            existing_indexes = self.index_client.list_index_names()
            if self.index_name not in existing_indexes:
                logger.info(f"Creating search index: {self.index_name}")
                self._create_index()
            else:
                logger.info(f"Index {self.index_name} already exists")
        except AzureError as e:
            logger.error(f"Index check error: {str(e)}")
    
    def _create_index(self):
        """Create search index with fields"""
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(
                name="content",
                type=SearchFieldDataType.String,
                searchable=True
            ),
            SimpleField(
                name="source_document",
                type=SearchFieldDataType.String
            ),
            SimpleField(
                name="chunk_index",
                type=SearchFieldDataType.Int32
            ),
            SimpleField(
                name="created_at",
                type=SearchFieldDataType.String
            ),
        ]
        
        index = SearchIndex(name=self.index_name, fields=fields)
        
        try:
            self.index_client.create_index(index)
            logger.info(f"Search index {self.index_name} created successfully")
        except AzureError as e:
            logger.error(f"Index creation error: {str(e)}")
            raise
    
    async def index_documents(self, documents: list) -> None:
        """
        Index documents in search service
        documents: list of dict with 'id', 'content', 'source_document', 'chunk_index'
        """
        try:
            if not documents:
                logger.warning("No documents to index")
                return
            
            # Upload documents to index
            result = self.search_client.upload_documents(documents)
            logger.info(f"Indexed {len(documents)} documents")
            return result
        except AzureError as e:
            logger.error(f"Index upload error: {str(e)}")
            raise
    
    async def search_documents(self, query: str, top_k: int = 3) -> list:
        """
        Search for documents matching the query
        Returns top_k results with relevance scores
        """
        try:
            results = self.search_client.search(
                search_text=query,
                select=["id", "content", "source_document", "chunk_index"],
                top=top_k
            )
            
            search_results = []
            for result in results:
                search_results.append({
                    "id": result["id"],
                    "content": result["content"],
                    "source_document": result.get("source_document", "unknown"),
                    "chunk_index": result.get("chunk_index", 0),
                    "score": result["@search.score"]
                })
            
            logger.info(f"Found {len(search_results)} search results")
            return search_results
        except AzureError as e:
            logger.error(f"Search error: {str(e)}")
            raise
    
    async def delete_documents_by_source(self, source_document: str) -> None:
        """Delete all documents from a source"""
        try:
            # Query to find documents
            results = self.search_client.search(
                search_text="*",
                filter=f"source_document eq '{source_document}'"
            )
            
            # Delete each document
            doc_ids = [result["id"] for result in results]
            if doc_ids:
                delete_payload = [{"id": doc_id} for doc_id in doc_ids]
                self.search_client.delete_documents(delete_payload)
                logger.info(f"Deleted {len(doc_ids)} documents from {source_document}")
        except AzureError as e:
            logger.error(f"Delete documents error: {str(e)}")
            raise
