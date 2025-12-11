"""
Discovery Workshop Agent for Azure Landing Zone
Systematically gathers required information from documents and user input
"""
import json
import logging
import re
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.contents.chat_history import ChatHistory
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

from src.discovery_framework import (
    DISCOVERY_QUESTIONS,
    DiscoveryQuestion,
    DiscoveryAnswer,
    DiscoveryCategory,
    InformationPriority,
    get_questions_by_category,
    get_critical_questions
)
from src.config import Config
from src.storage_client import StorageClient
from src.search_client import SearchIndexClient
from src.document_processor import DocumentProcessor
from src.models import ProcessedContent
from src.validators import QuestionValidator, ValidationResult, ValidationSeverity
from src.cost_estimator import AzureCostEstimator, AzureRegion
from src.export_utils import ReportExporter

logger = logging.getLogger(__name__)


class DiscoverySession(BaseModel):
    """Represents a discovery workshop session"""
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    answers: Dict[str, DiscoveryAnswer] = Field(default_factory=dict)
    documents_analyzed: List[str] = Field(default_factory=list)
    completion_percentage: float = 0.0
    missing_critical_info: List[str] = Field(default_factory=list)
    
    def get_answered_count(self) -> int:
        """Count answered questions"""
        return len(self.answers)
    
    def get_total_count(self) -> int:
        """Total questions in framework"""
        return len(DISCOVERY_QUESTIONS)
    
    def update_completion(self):
        """Update completion percentage"""
        self.completion_percentage = (self.get_answered_count() / self.get_total_count()) * 100


class DiscoveryAgent:
    """
    Discovery Workshop Agent
    Extracts answers from documents and asks users for missing information
    """
    
    def __init__(self, config):
        self.config = config
        self.storage_client = StorageClient(config.azure_storage)
        self.search_client = SearchIndexClient(config.azure_search)
        self.document_processor = DocumentProcessor(config)
        self.kernel = self._setup_kernel()
        self.session: Optional[DiscoverySession] = None
        self.use_search_index = True  # Flag to enable/disable search optimization
        self.auto_save_interval = 5  # Auto-save every 5 answers
        self.confidence_threshold = 0.85  # Auto-accept answers above this threshold
        self.answer_cache = {}  # Cache for validated answers
        
    def _setup_kernel(self) -> Kernel:
        """Initialize Semantic Kernel"""
        kernel = Kernel()
        
        chat_service = AzureChatCompletion(
            deployment_name=self.config.azure_openai.deployment_name,
            endpoint=self.config.azure_openai.endpoint,
            api_key=self.config.azure_openai.api_key
        )
        
        kernel.add_service(chat_service)
        return kernel
    
    async def start_discovery_workshop(self, session_id: str, auto_resume: bool = True) -> DiscoverySession:
        """Start a new discovery workshop session and auto-index artifacts"""
        self.session = DiscoverySession(session_id=session_id)
        logger.info(f"Started discovery workshop: {session_id}")
        
        # Auto-load latest previous session if enabled
        if auto_resume:
            await self._auto_load_previous_session()
        
        # Auto-index artifacts if using search
        if self.use_search_index:
            await self._auto_index_artifacts()
            await self._index_previous_answers()  # Index answers from previous sessions
        
        return self.session
    
    async def _auto_load_previous_session(self):
        """Automatically load answers from the most recent session"""
        try:
            import glob
            import os
            
            result_files = glob.glob("discovery_results_*.json")
            if not result_files:
                logger.info("No previous session found")
                return
            
            # Get the most recent file
            latest = max(result_files, key=os.path.getctime)
            logger.info(f"Found previous session: {latest}")
            
            with open(latest, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            # Load all answers into current session
            loaded_count = 0
            for answer_data in results.get('answers', []):
                answer = DiscoveryAnswer(
                    question_id=answer_data['question_id'],
                    answer=answer_data['answer'],
                    source=answer_data['source'],
                    confidence=answer_data['confidence'],
                    document_reference=answer_data.get('document_reference')
                )
                self.session.answers[answer_data['question_id']] = answer
                loaded_count += 1
            
            self.session.update_completion()
            logger.info(f"✓ Auto-loaded {loaded_count} answers from previous session")
            
        except Exception as e:
            logger.warning(f"Failed to auto-load previous session: {e}")
    
    async def _auto_index_artifacts(self):
        """Automatically index artifacts from blob storage into AI Search"""
        try:
            logger.info("Auto-indexing artifacts from blob storage...")
            
            # Initialize search client for indexing
            search_client = SearchClient(
                endpoint=self.config.azure_search.endpoint,
                index_name=self.config.azure_search.index_name,
                credential=AzureKeyCredential(self.config.azure_search.api_key)
            )
            
            # Get all artifacts from storage
            artifacts = self.storage_client.list_artifacts()
            logger.info(f"Found {len(artifacts)} artifacts to index")
            
            indexed_count = 0
            skipped_count = 0
            
            for artifact in artifacts:
                try:
                    # Create document ID from blob name
                    document_id = hashlib.md5(artifact.blob_name.encode()).hexdigest()
                    
                    # Check if already indexed by searching for this ID
                    try:
                        existing = search_client.get_document(key=document_id)
                        # Check if document was modified since last index
                        if existing and existing.get('last_modified'):
                            existing_modified = datetime.fromisoformat(existing['last_modified'])
                            if artifact.last_modified <= existing_modified:
                                logger.debug(f"Skipping (already indexed): {artifact.blob_name}")
                                skipped_count += 1
                                continue
                    except:
                        pass  # Document not found, will index it
                    
                    logger.info(f"Indexing: {artifact.blob_name}")
                    
                    # Download and process artifact
                    content = self.storage_client.download_artifact(artifact.blob_name)
                    processed = self.document_processor.process(
                        content,
                        artifact.document_type,
                        artifact.blob_name
                    )
                    
                    # Create search document
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
                        logger.warning(f"✗ Failed to index: {artifact.blob_name}")
                
                except Exception as e:
                    logger.error(f"Error indexing {artifact.blob_name}: {e}")
                    continue
            
            logger.info(f"Auto-indexing complete: {indexed_count} indexed, {skipped_count} skipped (already current)")
            
        except Exception as e:
            logger.warning(f"Auto-indexing failed: {e}. Will fall back to direct blob access.")
            self.use_search_index = False
    
    async def _index_previous_answers(self):
        """Index answers from previous discovery sessions into search for reference"""
        try:
            import glob
            import os
            
            # Find all previous discovery result files
            result_files = glob.glob("discovery_results_*.json")
            if not result_files:
                logger.info("No previous sessions found to index")
                return
            
            logger.info(f"Indexing answers from {len(result_files)} previous session(s)...")
            
            search_client = SearchClient(
                endpoint=self.config.azure_search.endpoint,
                index_name=self.config.azure_search.index_name,
                credential=AzureKeyCredential(self.config.azure_search.api_key)
            )
            
            indexed_answers = 0
            
            for result_file in result_files:
                try:
                    with open(result_file, 'r', encoding='utf-8') as f:
                        results = json.load(f)
                    
                    session_id = results.get('session', {}).get('id', 'unknown')
                    answers = results.get('answers', [])
                    
                    for answer_data in answers:
                        # Create a searchable document from the answer
                        document_id = hashlib.md5(f"{session_id}_{answer_data['question_id']}".encode()).hexdigest()
                        
                        # Build content from question and answer
                        content = f"""
Question: {answer_data['question']}
Category: {answer_data['category']}
Answer: {answer_data['answer']}

This is a previously answered discovery question from session {session_id}.
Source: {answer_data['source']}
Confidence: {answer_data['confidence']}
"""
                        
                        search_document = {
                            "id": document_id,
                            "blob_name": f"answer_{answer_data['question_id']}_{session_id}.txt",
                            "content": content,
                            "document_type": "text",
                            "keywords": [answer_data['category'], answer_data['priority'], "answer", "discovery"],
                            "last_modified": datetime.now().isoformat()
                        }
                        
                        # Upload to search index
                        result = search_client.upload_documents(documents=[search_document])
                        
                        if result[0].succeeded:
                            indexed_answers += 1
                            logger.debug(f"Indexed answer for: {answer_data['question_id']}")
                
                except Exception as e:
                    logger.warning(f"Failed to index answers from {result_file}: {e}")
                    continue
            
            logger.info(f"✓ Indexed {indexed_answers} previous answers for reference")
            
        except Exception as e:
            logger.warning(f"Failed to index previous answers: {e}")
    
    async def analyze_documents(self) -> Tuple[int, List[str]]:
        """
        Analyze uploaded documents to extract answers
        Uses Azure AI Search for efficient querying when available
        Returns: (answers_found, documents_processed)
        """
        if not self.session:
            raise ValueError("No active discovery session. Call start_discovery_workshop() first.")
        
        # Try search-optimized approach first
        if self.use_search_index:
            try:
                return await self._analyze_with_search_index()
            except Exception as e:
                logger.warning(f"Search index not available: {e}. Falling back to direct blob access.")
                self.use_search_index = False
        
        # Fallback: Direct blob storage approach
        return await self._analyze_from_blob_storage()
    
    async def _analyze_with_search_index(self) -> Tuple[int, List[str]]:
        """
        Optimized document analysis using Azure AI Search
        Queries only relevant content for each question
        """
        logger.info("Using Azure AI Search for optimized document analysis...")
        
        answers_found = 0
        documents_used = set()
        
        # Process questions by category for better context
        for category in DiscoveryCategory:
            category_questions = get_questions_by_category(category)
            
            for question in category_questions:
                if question.id in self.session.answers:
                    continue  # Skip already answered
                
                try:
                    # Build search query from question and help text
                    search_query = f"{question.question} {question.help_text or ''}"
                    
                    # Semantic search for relevant content
                    results = self.search_client.search(
                        query=search_query,
                        top=3,  # Top 3 most relevant documents
                        select=["blob_name", "content", "document_type"]
                    )
                    
                    if not results:
                        continue
                    
                    # Extract answer from search results
                    answer = await self._extract_answer_from_search_results(
                        question,
                        results
                    )
                    
                    if answer:
                        # Smart inference: auto-accept high confidence answers
                        if answer.confidence >= self.confidence_threshold:
                            self.session.answers[question.id] = answer
                            answers_found += 1
                            documents_used.add(answer.document_reference)
                            logger.info(f"✓ Auto-answered {question.id} (confidence: {answer.confidence:.0%})")
                        else:
                            # Store for user review if confidence is low
                            self.answer_cache[question.id] = answer
                            logger.debug(f"Cached low-confidence answer for {question.id} (confidence: {answer.confidence:.0%})")
                
                except Exception as e:
                    logger.error(f"Error searching for {question.id}: {e}")
                    continue
        
        self.session.documents_analyzed = list(documents_used)
        self.session.update_completion()
        
        logger.info(f"Extracted {answers_found} answers from {len(documents_used)} documents using search index")
        return answers_found, self.session.documents_analyzed
    
    async def _analyze_from_blob_storage(self) -> Tuple[int, List[str]]:
        """
        Fallback: Analyze documents directly from blob storage
        Used when search index is not available
        """
        logger.info("Retrieving artifacts from blob storage...")
        artifacts = self.storage_client.list_artifacts()
        
        if not artifacts:
            logger.warning("No documents found in blob storage")
            return 0, []
        
        logger.info(f"Found {len(artifacts)} documents to analyze")
        answers_found = 0
        
        for artifact_name in artifacts:
            try:
                logger.info(f"Processing document: {artifact_name}")
                content = self.storage_client.download_artifact(artifact_name)
                processed = self.document_processor.process(artifact_name, content)
                
                # Extract answers from document
                extracted_answers = await self._extract_answers_from_document(
                    artifact_name, 
                    processed
                )
                
                answers_found += len(extracted_answers)
                self.session.documents_analyzed.append(artifact_name)
                
                logger.info(f"Extracted {len(extracted_answers)} answers from {artifact_name}")
                
            except Exception as e:
                logger.error(f"Error processing {artifact_name}: {e}")
                continue
        
        self.session.update_completion()
        return answers_found, self.session.documents_analyzed
    
    async def _extract_answer_from_search_results(
        self,
        question: DiscoveryQuestion,
        search_results: List[Dict[str, Any]]
    ) -> Optional[DiscoveryAnswer]:
        """
        Extract answer to a specific question from search results
        More efficient than processing entire documents
        """
        if not search_results:
            return None
        
        # Combine relevant content from top results
        combined_content = "\n\n".join([
            f"Document: {result.get('blob_name', 'unknown')}\n{result.get('content', '')[:2000]}"
            for result in search_results[:3]
        ])
        
        prompt = f"""Extract the answer to this specific question from the provided content.

QUESTION: {question.question}
CONTEXT: {question.help_text or 'N/A'}
{f"EXAMPLES: {question.examples}" if question.examples else ""}

RELEVANT CONTENT:
{combined_content}

TASK: If you find a clear answer, return JSON with:
{{
  "answer": "the specific answer text",
  "confidence": 0.0-1.0,
  "source_document": "document name where answer was found"
}}

If no clear answer found, return: {{"answer": null}}
"""
        
        try:
            chat_service = self.kernel.get_service(type=ChatCompletionClientBase)
            chat_history = ChatHistory()
            chat_history.add_user_message(prompt)
            
            response = await chat_service.get_chat_message_content(
                chat_history=chat_history,
                settings=self.kernel.get_prompt_execution_settings_from_service_id(
                    service_id=chat_service.service_id
                )
            )
            
            # Parse response
            cleaned = self._clean_json_response(str(response))
            data = json.loads(cleaned)
            
            if data.get("answer"):
                return DiscoveryAnswer(
                    question_id=question.id,
                    answer=data["answer"],
                    source="search_index",
                    confidence=data.get("confidence", 0.8),
                    document_reference=data.get("source_document", search_results[0].get("blob_name", "unknown")),
                    notes=None
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting answer for {question.id}: {e}")
            return None
    
    async def _extract_answers_from_document(
        self, 
        document_name: str, 
        content: ProcessedContent
    ) -> List[DiscoveryAnswer]:
        """Extract answers to discovery questions from document content"""
        
        # Build extraction prompt
        questions_text = "\n".join([
            f"{qid}: {q.question}"
            for qid, q in DISCOVERY_QUESTIONS.items()
        ])
        
        prompt = f"""You are analyzing a document to extract information for Azure Landing Zone deployment discovery.

DOCUMENT: {document_name}
CONTENT:
{content.text_content[:8000]}

DISCOVERY QUESTIONS:
{questions_text}

TASK: Extract answers from the document content. For each question where you find relevant information:
1. Identify the question ID
2. Extract the specific answer
3. Rate your confidence (0.0 to 1.0)
4. Note the relevant document section

Return ONLY valid JSON array format:
[
  {{
    "question_id": "biz_001",
    "answer": "Digital transformation and datacenter exit",
    "confidence": 0.95,
    "document_reference": "Executive Summary, page 1"
  }}
]

Only include questions where you found clear, relevant information. Return empty array [] if nothing found.
"""
        
        try:
            chat_service = self.kernel.get_service(type=ChatCompletionClientBase)
            chat_history = ChatHistory()
            chat_history.add_user_message(prompt)
            
            response = await chat_service.get_chat_message_content(
                chat_history=chat_history,
                settings=self.kernel.get_prompt_execution_settings_from_service_id(
                    service_id=chat_service.service_id
                )
            )
            
            # Clean and parse JSON response
            cleaned_response = self._clean_json_response(str(response))
            extracted_data = json.loads(cleaned_response)
            
            # Convert to DiscoveryAnswer objects
            answers = []
            for item in extracted_data:
                answer = DiscoveryAnswer(
                    question_id=item["question_id"],
                    answer=item["answer"],
                    source="document",
                    confidence=item.get("confidence", 0.8),
                    document_reference=item.get("document_reference", document_name),
                    notes=None
                )
                
                # Store in session
                self.session.answers[answer.question_id] = answer
                answers.append(answer)
            
            return answers
            
        except Exception as e:
            logger.error(f"Error extracting answers: {e}")
            return []
    
    def _clean_json_response(self, response: str) -> str:
        """Clean AI response to extract pure JSON"""
        # Remove markdown code blocks
        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*', '', cleaned)
        
        # Try to extract JSON array
        match = re.search(r'\[.*\]', cleaned, re.DOTALL)
        if match:
            return match.group(0)
        
        # Try to extract JSON object
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            return match.group(0)
        
        return cleaned.strip()
    
    def get_missing_information(self, priority: Optional[InformationPriority] = None) -> List[DiscoveryQuestion]:
        """Get questions that still need answers"""
        if not self.session:
            return []
        
        missing = []
        for qid, question in DISCOVERY_QUESTIONS.items():
            # Filter by priority if specified
            if priority and question.priority != priority:
                continue
            
            # Check if answered
            if qid not in self.session.answers:
                missing.append(question)
        
        return missing
    
    def get_critical_gaps(self) -> List[DiscoveryQuestion]:
        """Get unanswered CRITICAL priority questions"""
        return self.get_missing_information(InformationPriority.CRITICAL)
    
    def get_cached_answers_for_review(self) -> Dict[str, DiscoveryAnswer]:
        """Get cached low-confidence answers that need user review"""
        return self.answer_cache.copy()
    
    async def ask_user_question(self, question: DiscoveryQuestion, user_answer: str) -> Tuple[DiscoveryAnswer, List[ValidationResult]]:
        """Record user's answer to a discovery question with validation"""
        answer = DiscoveryAnswer(
            question_id=question.id,
            answer=user_answer,
            source="user_input",
            confidence=1.0,
            document_reference=None,
            notes="Provided during interactive discovery session"
        )
        
        # Validate answer against Azure best practices
        validations = QuestionValidator.validate_answer(question.id, user_answer)
        
        self.session.answers[question.id] = answer
        self.session.update_completion()
        
        # Auto-save checkpoint every N answers
        if len(self.session.answers) % self.auto_save_interval == 0:
            self._auto_save_checkpoint()
        
        return answer, validations
    
    def _auto_save_checkpoint(self):
        """Auto-save session checkpoint"""
        try:
            checkpoint_file = f"checkpoint_{self.session.session_id}.json"
            self.export_discovery_results(checkpoint_file)
            logger.info(f"✓ Auto-saved checkpoint: {checkpoint_file}")
        except Exception as e:
            logger.warning(f"Failed to auto-save checkpoint: {e}")
    
    def get_discovery_summary(self) -> Dict:
        """Generate summary of discovery session"""
        if not self.session:
            return {}
        
        # Count by source
        document_answers = sum(1 for a in self.session.answers.values() if a.source == "document")
        user_answers = sum(1 for a in self.session.answers.values() if a.source == "user_input")
        
        # Count by priority
        critical_answered = sum(
            1 for qid in self.session.answers.keys()
            if DISCOVERY_QUESTIONS[qid].priority == InformationPriority.CRITICAL
        )
        critical_total = len(get_critical_questions())
        
        # Group by category
        answers_by_category = {}
        for category in DiscoveryCategory:
            category_questions = get_questions_by_category(category)
            answered = sum(1 for q in category_questions if q.id in self.session.answers)
            answers_by_category[category.value] = {
                "answered": answered,
                "total": len(category_questions),
                "percentage": (answered / len(category_questions) * 100) if category_questions else 0
            }
        
        return {
            "session_id": self.session.session_id,
            "timestamp": self.session.timestamp.isoformat(),
            "total_questions": self.session.get_total_count(),
            "answered": self.session.get_answered_count(),
            "completion_percentage": round(self.session.completion_percentage, 2),
            "documents_analyzed": len(self.session.documents_analyzed),
            "answers_from_documents": document_answers,
            "answers_from_user": user_answers,
            "critical_questions": {
                "answered": critical_answered,
                "total": critical_total,
                "percentage": round((critical_answered / critical_total * 100), 2) if critical_total > 0 else 0
            },
            "by_category": answers_by_category,
            "missing_critical": [q.question for q in self.get_critical_gaps()]
        }
    
    def export_discovery_results(self, output_path: str):
        """Export discovery results to JSON file"""
        if not self.session:
            raise ValueError("No active discovery session")
        
        results = {
            "session": {
                "id": self.session.session_id,
                "timestamp": self.session.timestamp.isoformat(),
                "completion": self.session.completion_percentage
            },
            "summary": self.get_discovery_summary(),
            "answers": [
                {
                    "question_id": qid,
                    "question": DISCOVERY_QUESTIONS[qid].question,
                    "category": DISCOVERY_QUESTIONS[qid].category.value,
                    "priority": DISCOVERY_QUESTIONS[qid].priority.value,
                    "answer": answer.answer,
                    "source": answer.source,
                    "confidence": answer.confidence,
                    "document_reference": answer.document_reference
                }
                for qid, answer in self.session.answers.items()
            ],
            "missing_information": [
                {
                    "question_id": q.id,
                    "question": q.question,
                    "category": q.category.value,
                    "priority": q.priority.value,
                    "help_text": q.help_text,
                    "examples": q.examples
                }
                for q in self.get_missing_information()
            ]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Discovery results exported to {output_path}")
    
    def import_discovery_results(self, input_path: str) -> bool:
        """Import and resume from previous discovery session"""
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            # Create session from imported data
            session_data = results.get('session', {})
            self.session = DiscoverySession(session_id=session_data.get('id', f"resumed_{datetime.now().strftime('%Y%m%d_%H%M%S')}"))
            
            # Import all answers
            for answer_data in results.get('answers', []):
                answer = DiscoveryAnswer(
                    question_id=answer_data['question_id'],
                    answer=answer_data['answer'],
                    source=answer_data['source'],
                    confidence=answer_data['confidence'],
                    document_reference=answer_data.get('document_reference')
                )
                self.session.answers[answer_data['question_id']] = answer
            
            self.session.update_completion()
            logger.info(f"Imported {len(self.session.answers)} answers from {input_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to import discovery results: {e}")
            return False
    
    def estimate_costs(self) -> Optional[Dict]:
        """Estimate Azure costs based on requirements gathered"""
        if not self.session:
            return None
        
        try:
            # Extract key parameters from answers
            requirements = self._extract_cost_parameters()
            
            # Use cost estimator
            estimator = AzureCostEstimator(region=AzureRegion.EAST_US)
            estimate = estimator.generate_full_estimate(requirements)
            
            return estimate
        except Exception as e:
            logger.error(f"Cost estimation failed: {e}")
            return None
    
    def _extract_cost_parameters(self) -> Dict:
        """Extract cost-relevant parameters from answers"""
        params = {
            'vm_count': 0,
            'storage_tb': 0,
            'connectivity_method': '',
            'expressroute_bandwidth': '',
            'use_firewall': True,
            'web_workloads': False,
        }
        
        # Parse answers to extract relevant info
        for qid, answer in self.session.answers.items():
            answer_text = answer.answer.lower()
            
            # Connectivity method
            if 'net_003' == qid:
                params['connectivity_method'] = answer.answer
            
            # ExpressRoute bandwidth
            if 'net_004' == qid:
                params['expressroute_bandwidth'] = answer.answer
            
            # VM count (estimate from workload descriptions)
            if 'vm' in answer_text or 'virtual machine' in answer_text:
                # Try to extract numbers
                import re
                numbers = re.findall(r'\d+', answer_text)
                if numbers:
                    params['vm_count'] = max(params['vm_count'], int(numbers[0]))
            
            # Storage (estimate from data volume)
            if 'tb' in answer_text or 'terabyte' in answer_text:
                import re
                numbers = re.findall(r'(\d+)\s*tb', answer_text)
                if numbers:
                    params['storage_tb'] = max(params['storage_tb'], int(numbers[0]))
        
        # Default estimates if not specified
        if params['vm_count'] == 0:
            params['vm_count'] = 10  # Default assumption
        
        return params
    
    def export_enhanced_report(self, output_path: str, format: str = 'pdf') -> str:
        """Export enhanced report with multiple formats"""
        if not self.session:
            raise ValueError("No active session")
        
        # Get full results
        results = {
            "session": {
                "id": self.session.session_id,
                "timestamp": self.session.timestamp.isoformat(),
                "completion": self.session.completion_percentage
            },
            "summary": self.get_discovery_summary(),
            "answers": [
                {
                    "question_id": qid,
                    "question": DISCOVERY_QUESTIONS[qid].question,
                    "category": DISCOVERY_QUESTIONS[qid].category.value,
                    "priority": DISCOVERY_QUESTIONS[qid].priority.value,
                    "answer": answer.answer,
                    "source": answer.source,
                    "confidence": answer.confidence,
                    "document_reference": answer.document_reference
                }
                for qid, answer in self.session.answers.items()
            ],
            "missing_information": [
                {
                    "question_id": q.id,
                    "question": q.question,
                    "category": q.category.value,
                    "priority": q.priority.value,
                    "help_text": q.help_text,
                    "examples": q.examples
                }
                for q in self.get_missing_information()
            ]
        }
        
        exporter = ReportExporter(results, self.session.session_id)
        
        if format.lower() == 'pdf':
            return exporter.export_to_pdf(output_path)
        elif format.lower() == 'word' or format.lower() == 'docx':
            return exporter.export_to_word(output_path)
        elif format.lower() == 'excel' or format.lower() == 'xlsx':
            return exporter.export_to_excel(output_path)
        elif format.lower() == 'markdown' or format.lower() == 'md':
            return exporter.export_to_markdown(output_path)
        else:
            return exporter.export_to_pdf(output_path)
