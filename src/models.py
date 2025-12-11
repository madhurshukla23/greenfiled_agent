"""
Data models for the Orchestrator Agent
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class DocumentType(str, Enum):
    """Supported document types"""
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    XLSX = "xlsx"
    VSDX = "vsdx"
    IMAGE = "image"
    TEXT = "text"
    UNKNOWN = "unknown"


class ConflictSeverity(str, Enum):
    """Severity levels for conflicts"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Artifact(BaseModel):
    """Represents a customer artifact"""
    blob_name: str
    document_type: DocumentType
    size_bytes: int
    last_modified: datetime
    url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProcessedContent(BaseModel):
    """Normalized content from an artifact"""
    artifact_name: str
    document_type: DocumentType
    extracted_text: str
    structured_data: Dict[str, Any] = Field(default_factory=dict)
    sections: List[Dict[str, str]] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    confidence_score: float = 1.0


class Conflict(BaseModel):
    """Represents a detected conflict or inconsistency"""
    severity: ConflictSeverity
    description: str
    sources: List[str]
    suggested_resolution: Optional[str] = None


class Unknown(BaseModel):
    """Represents missing or unknown information"""
    category: str
    description: str
    impact: str
    recommended_action: str


class Requirement(BaseModel):
    """Represents a gathered requirement"""
    category: str  # e.g., "networking", "security", "governance"
    requirement: str
    source: str
    priority: Optional[str] = None
    compliance_related: bool = False


class ContextPackage(BaseModel):
    """Structured output for the Design Agent"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    artifacts_processed: int
    requirements: List[Requirement] = Field(default_factory=list)
    business_constraints: List[str] = Field(default_factory=list)
    technical_specifications: Dict[str, Any] = Field(default_factory=dict)
    compliance_needs: List[str] = Field(default_factory=list)
    conflicts: List[Conflict] = Field(default_factory=list)
    unknowns: List[Unknown] = Field(default_factory=list)
    summary: str
    confidence_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return self.model_dump(mode='json')
