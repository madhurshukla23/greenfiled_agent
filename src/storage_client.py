"""
Azure Blob Storage client for retrieving customer artifacts
"""
import logging
from typing import List
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.exceptions import AzureError

from src.models import Artifact, DocumentType
from src.config import AzureStorageConfig

logger = logging.getLogger(__name__)


class StorageClient:
    """Client for interacting with Azure Blob Storage"""
    
    def __init__(self, config: AzureStorageConfig):
        self.config = config
        self.blob_service_client = BlobServiceClient.from_connection_string(
            config.connection_string
        )
        self.container_client = self.blob_service_client.get_container_client(
            config.container_name
        )
    
    def list_artifacts(self, prefix: str = "") -> List[Artifact]:
        """List all artifacts in the container"""
        try:
            artifacts = []
            blobs = self.container_client.list_blobs(name_starts_with=prefix)
            
            for blob in blobs:
                artifact = Artifact(
                    blob_name=blob.name,
                    document_type=self._detect_document_type(blob.name),
                    size_bytes=blob.size,
                    last_modified=blob.last_modified,
                    url=self._get_blob_url(blob.name),
                    metadata=blob.metadata or {}
                )
                artifacts.append(artifact)
            
            logger.info(f"Found {len(artifacts)} artifacts in storage")
            return artifacts
        
        except AzureError as e:
            logger.error(f"Error listing artifacts: {e}")
            raise
    
    def download_artifact(self, blob_name: str) -> bytes:
        """Download artifact content as bytes"""
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            download_stream = blob_client.download_blob()
            content = download_stream.readall()
            
            logger.info(f"Downloaded artifact: {blob_name} ({len(content)} bytes)")
            return content
        
        except AzureError as e:
            logger.error(f"Error downloading artifact {blob_name}: {e}")
            raise
    
    def upload_artifact(self, blob_name: str, content: bytes) -> None:
        """Upload artifact to blob storage"""
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            blob_client.upload_blob(content, overwrite=True)
            
            logger.info(f"Uploaded artifact: {blob_name} ({len(content)} bytes)")
        
        except AzureError as e:
            logger.error(f"Error uploading artifact {blob_name}: {e}")
            raise
    
    def _detect_document_type(self, filename: str) -> DocumentType:
        """Detect document type from filename extension"""
        extension = filename.lower().split('.')[-1]
        
        type_mapping = {
            'pdf': DocumentType.PDF,
            'docx': DocumentType.DOCX,
            'doc': DocumentType.DOCX,
            'pptx': DocumentType.PPTX,
            'ppt': DocumentType.PPTX,
            'png': DocumentType.IMAGE,
            'jpg': DocumentType.IMAGE,
            'jpeg': DocumentType.IMAGE,
            'txt': DocumentType.TEXT,
            'md': DocumentType.TEXT,
        }
        
        return type_mapping.get(extension, DocumentType.UNKNOWN)
    
    def _get_blob_url(self, blob_name: str) -> str:
        """Get the URL for a blob"""
        blob_client = self.container_client.get_blob_client(blob_name)
        return blob_client.url
