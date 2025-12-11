"""
Script to index uploaded artifacts in Azure AI Search
This script scans blob storage and creates search index entries
"""
import asyncio
import logging
import hashlib
from datetime import datetime
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

from src.config import Config
from src.storage_client import StorageClient
from src.document_processor import DocumentProcessor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def index_artifacts():
    """Index all artifacts from blob storage into AI Search"""
    
    # Load configuration
    config = Config()
    config.validate()
    
    # Initialize clients
    storage_client = StorageClient(config.azure_storage)
    document_processor = DocumentProcessor(config)
    
    search_client = SearchClient(
        endpoint=config.azure_search.endpoint,
        index_name=config.azure_search.index_name,
        credential=AzureKeyCredential(config.azure_search.api_key)
    )
    
    logger.info("Starting artifact indexing...")
    
    # Get all artifacts from storage
    artifacts = storage_client.list_artifacts()
    logger.info(f"Found {len(artifacts)} artifacts to index")
    
    indexed_count = 0
    
    for artifact in artifacts:
        try:
            logger.info(f"Processing: {artifact.blob_name}")
            
            # Download and process artifact
            content = storage_client.download_artifact(artifact.blob_name)
            processed = document_processor.process(
                content,
                artifact.document_type,
                artifact.blob_name
            )
            
            # Create search document
            document_id = hashlib.md5(artifact.blob_name.encode()).hexdigest()
            
            search_document = {
                "id": document_id,
                "blob_name": artifact.blob_name,
                "content": processed.extracted_text[:50000],  # Limit content size
                "document_type": artifact.document_type.value,
                "keywords": processed.keywords,
                "last_modified": artifact.last_modified.isoformat()
            }
            
            # Upload to search index
            result = search_client.upload_documents(documents=[search_document])
            
            if result[0].succeeded:
                logger.info(f"✓ Indexed: {artifact.blob_name}")
                indexed_count += 1
            else:
                logger.error(f"✗ Failed to index: {artifact.blob_name}")
            
        except Exception as e:
            logger.error(f"Error processing {artifact.blob_name}: {e}")
            continue
    
    logger.info(f"\nIndexing complete! Indexed {indexed_count}/{len(artifacts)} artifacts")


if __name__ == "__main__":
    asyncio.run(index_artifacts())
