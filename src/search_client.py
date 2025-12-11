"""
Azure AI Search client for querying indexed artifacts
"""
import logging
from typing import List, Dict, Any, Optional
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import AzureError

from src.config import AzureSearchConfig

logger = logging.getLogger(__name__)


class SearchIndexClient:
    """Client for querying Azure AI Search"""
    
    def __init__(self, config: AzureSearchConfig):
        self.config = config
        self.search_client = SearchClient(
            endpoint=config.endpoint,
            index_name=config.index_name,
            credential=AzureKeyCredential(config.api_key)
        )
    
    def search(
        self,
        query: str,
        top: int = 10,
        filters: Optional[str] = None,
        select: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search the index for relevant documents
        
        Args:
            query: Search query string
            top: Number of results to return
            filters: OData filter expression
            select: List of fields to return
            
        Returns:
            List of search results
        """
        try:
            results = self.search_client.search(
                search_text=query,
                top=top,
                filter=filters,
                select=select,
                include_total_count=True
            )
            
            documents = []
            for result in results:
                # Convert search result to dictionary
                doc = {key: value for key, value in result.items() if not key.startswith('@')}
                # Add search score if available
                if hasattr(result, '@search.score'):
                    doc['search_score'] = result['@search.score']
                documents.append(doc)
            
            logger.info(f"Found {len(documents)} documents for query: '{query}'")
            return documents
        
        except AzureError as e:
            logger.error(f"Search error: {e}")
            raise
    
    def semantic_search(
        self,
        query: str,
        top: int = 10,
        semantic_configuration: str = "default"
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search using Azure AI Search semantic ranking
        
        Args:
            query: Search query
            top: Number of results
            semantic_configuration: Semantic configuration name
            
        Returns:
            List of semantically ranked results
        """
        try:
            results = self.search_client.search(
                search_text=query,
                top=top,
                query_type="semantic",
                semantic_configuration_name=semantic_configuration,
                include_total_count=True
            )
            
            documents = []
            for result in results:
                doc = {key: value for key, value in result.items() if not key.startswith('@')}
                # Add semantic ranking information
                if hasattr(result, '@search.reranker_score'):
                    doc['semantic_score'] = result['@search.reranker_score']
                documents.append(doc)
            
            logger.info(f"Semantic search found {len(documents)} documents")
            return documents
        
        except AzureError as e:
            logger.error(f"Semantic search error: {e}")
            # Fallback to regular search
            logger.info("Falling back to regular search")
            return self.search(query, top)
    
    def get_document(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a specific document by key"""
        try:
            result = self.search_client.get_document(key=key)
            return dict(result)
        except AzureError as e:
            logger.error(f"Error retrieving document {key}: {e}")
            return None
