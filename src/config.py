"""
Configuration settings for the Orchestrator Agent
"""
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class AzureOpenAIConfig(BaseModel):
    """Azure OpenAI configuration"""
    endpoint: str = Field(default_factory=lambda: os.getenv("AZURE_OPENAI_ENDPOINT"))
    api_key: str = Field(default_factory=lambda: os.getenv("AZURE_OPENAI_API_KEY"))
    deployment_name: str = Field(default_factory=lambda: os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"))
    api_version: str = Field(default_factory=lambda: os.getenv("AZURE_OPENAI_API_VERSION"))


class AzureStorageConfig(BaseModel):
    """Azure Storage configuration"""
    connection_string: str = Field(default_factory=lambda: os.getenv("AZURE_STORAGE_CONNECTION_STRING"))
    container_name: str = Field(default_factory=lambda: os.getenv("AZURE_STORAGE_CONTAINER_NAME"))


class AzureSearchConfig(BaseModel):
    """Azure AI Search configuration"""
    endpoint: str = Field(default_factory=lambda: os.getenv("AZURE_SEARCH_ENDPOINT"))
    api_key: str = Field(default_factory=lambda: os.getenv("AZURE_SEARCH_API_KEY"))
    index_name: str = Field(default_factory=lambda: os.getenv("AZURE_SEARCH_INDEX_NAME"))


class AzureDocumentIntelligenceConfig(BaseModel):
    """Azure Document Intelligence configuration"""
    endpoint: str = Field(default_factory=lambda: os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", ""))
    api_key: str = Field(default_factory=lambda: os.getenv("AZURE_DOCUMENT_INTELLIGENCE_API_KEY", ""))
    enabled: bool = Field(default_factory=lambda: os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENABLED", "true").lower() == "true")


class AzureVisionConfig(BaseModel):
    """Azure AI Vision configuration"""
    endpoint: str = Field(default_factory=lambda: os.getenv("AZURE_VISION_ENDPOINT", ""))
    api_key: str = Field(default_factory=lambda: os.getenv("AZURE_VISION_API_KEY", ""))
    enabled: bool = Field(default_factory=lambda: os.getenv("AZURE_VISION_ENABLED", "true").lower() == "true")


class AgentConfig(BaseModel):
    """Agent configuration"""
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    max_tokens: int = Field(default_factory=lambda: int(os.getenv("MAX_TOKENS", "4000")))
    temperature: float = Field(default_factory=lambda: float(os.getenv("TEMPERATURE", "0.7")))


class Config:
    """Main configuration class"""
    def __init__(self):
        self.azure_openai = AzureOpenAIConfig()
        self.azure_storage = AzureStorageConfig()
        self.azure_search = AzureSearchConfig()
        self.azure_document_intelligence = AzureDocumentIntelligenceConfig()
        self.azure_vision = AzureVisionConfig()
        self.agent = AgentConfig()

    def validate(self) -> bool:
        """Validate that all required config is present"""
        required_fields = [
            (self.azure_openai.endpoint, "AZURE_OPENAI_ENDPOINT"),
            (self.azure_openai.api_key, "AZURE_OPENAI_API_KEY"),
            (self.azure_openai.deployment_name, "AZURE_OPENAI_DEPLOYMENT_NAME"),
            (self.azure_storage.connection_string, "AZURE_STORAGE_CONNECTION_STRING"),
            (self.azure_storage.container_name, "AZURE_STORAGE_CONTAINER_NAME"),
            (self.azure_search.endpoint, "AZURE_SEARCH_ENDPOINT"),
            (self.azure_search.api_key, "AZURE_SEARCH_API_KEY"),
            (self.azure_search.index_name, "AZURE_SEARCH_INDEX_NAME"),
        ]

        missing = [name for value, name in required_fields if not value]
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        
        return True
