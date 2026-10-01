"""
Azure Storage Manager
Handles document upload and retrieval from Azure Blob Storage
"""

import os
import asyncio
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.exceptions import AzureError
import logging

logger = logging.getLogger(__name__)

class AzureStorageManager:
    """Manages Azure Blob Storage operations"""
    
    def __init__(self):
        self.connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.container_name = os.getenv("AZURE_STORAGE_CONTAINER", "documents")
        
        if not self.connection_string:
            raise ValueError("AZURE_STORAGE_CONNECTION_STRING not set")
        
        try:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                self.connection_string
            )
            self.container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            logger.info(f"Connected to Azure Storage container: {self.container_name}")
        except AzureError as e:
            logger.error(f"Azure Storage connection error: {str(e)}")
            raise
    
    async def upload_file(self, filename: str, content: bytes) -> str:
        """
        Upload file to Azure Blob Storage
        Returns: blob URL
        """
        try:
            blob_client = self.container_client.get_blob_client(filename)
            blob_client.upload_blob(content, overwrite=True)
            logger.info(f"Uploaded file: {filename}")
            return blob_client.url
        except AzureError as e:
            logger.error(f"Upload error: {str(e)}")
            raise
    
    async def download_file(self, filename: str) -> bytes:
        """Download file from Azure Blob Storage"""
        try:
            blob_client = self.container_client.get_blob_client(filename)
            download_stream = blob_client.download_blob()
            return download_stream.readall()
        except AzureError as e:
            logger.error(f"Download error: {str(e)}")
            raise
    
    async def delete_file(self, filename: str) -> None:
        """Delete file from Azure Blob Storage"""
        try:
            blob_client = self.container_client.get_blob_client(filename)
            blob_client.delete_blob()
            logger.info(f"Deleted file: {filename}")
        except AzureError as e:
            logger.error(f"Delete error: {str(e)}")
            raise
    
    async def list_documents(self) -> list:
        """List all documents in container"""
        try:
            blobs = self.container_client.list_blobs()
            documents = []
            for blob in blobs:
                documents.append({
                    "name": blob.name,
                    "size": blob.size,
                    "last_modified": blob.last_modified.isoformat()
                })
            return documents
        except AzureError as e:
            logger.error(f"List documents error: {str(e)}")
            raise
    
    async def file_exists(self, filename: str) -> bool:
        """Check if file exists"""
        try:
            blob_client = self.container_client.get_blob_client(filename)
            return blob_client.exists()
        except AzureError as e:
            logger.error(f"File exists check error: {str(e)}")
            return False
