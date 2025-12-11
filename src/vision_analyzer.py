"""
GPT-4 Vision integration for analyzing architectural diagrams and visual content
"""
import base64
import logging
from typing import Dict, Any, Optional
from openai import AzureOpenAI

logger = logging.getLogger(__name__)


class VisionAnalyzer:
    """Analyzes images and diagrams using GPT-4 Vision"""
    
    def __init__(self, config):
        """
        Initialize Vision Analyzer with Azure OpenAI GPT-4 Vision
        
        Args:
            config: Config object with Azure OpenAI credentials
        """
        self.config = config
        self.client = AzureOpenAI(
            api_key=config.azure_openai.api_key,
            api_version=config.azure_openai.api_version,
            azure_endpoint=config.azure_openai.endpoint
        )
        self.deployment_name = config.azure_openai.deployment_name
        
    def analyze_diagram(self, image_data: bytes, analysis_type: str = "architecture") -> Dict[str, Any]:
        """
        Analyze architectural diagrams, network topology, or other visual content
        
        Args:
            image_data: Raw image bytes
            analysis_type: Type of analysis - "architecture", "network", "workflow", or "general"
            
        Returns:
            Dictionary with extracted information
        """
        # Encode image to base64
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        # Create analysis prompt based on type
        prompts = {
            "architecture": """Analyze this Azure architecture diagram and extract:
1. Azure services depicted (VMs, storage, networking, databases, etc.)
2. Network topology and connectivity patterns (hub-spoke, VNET peering, etc.)
3. Security components (NSGs, firewalls, WAF, private endpoints)
4. Data flow and integration points
5. Any IP address ranges, subnet information, or naming conventions visible
6. Compliance or governance elements shown

Provide a structured summary of all technical details you can identify.""",
            
            "network": """Analyze this network diagram and extract:
1. Network topology type (hub-spoke, mesh, etc.)
2. IP address ranges and subnet allocations
3. Connectivity methods (VPN, ExpressRoute, VNET peering)
4. Network security groups and firewall rules
5. DNS configuration
6. Any on-premises connections shown

Provide detailed network specifications.""",
            
            "workflow": """Analyze this workflow or process diagram and extract:
1. Main process steps and flow
2. Decision points and conditional logic
3. Systems or services involved
4. Data transformations or integrations
5. Error handling or fallback mechanisms

Provide a clear description of the workflow.""",
            
            "general": """Analyze this diagram/image and extract any relevant technical information for Azure Landing Zone planning:
- Infrastructure components
- Network architecture
- Security controls
- Naming conventions
- Compliance requirements
- Any text, labels, or annotations visible

Provide a comprehensive description of all identifiable elements."""
        }
        
        prompt = prompts.get(analysis_type, prompts["general"])
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an Azure architecture expert analyzing technical diagrams. Extract all visible technical details accurately."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                temperature=0.3  # Lower temperature for more accurate extraction
            )
            
            analysis_result = response.choices[0].message.content
            
            return {
                "success": True,
                "analysis": analysis_result,
                "analysis_type": analysis_type,
                "model": self.deployment_name,
                "confidence": "high" if response.choices[0].finish_reason == "stop" else "medium"
            }
            
        except Exception as e:
            logger.error(f"GPT-4 Vision analysis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis": f"[Vision analysis failed: {str(e)}]"
            }
    
    def answer_question_from_image(self, image_data: bytes, question: str) -> Dict[str, Any]:
        """
        Answer a specific question based on image content
        
        Args:
            image_data: Raw image bytes
            question: Specific question to answer
            
        Returns:
            Dictionary with answer and confidence
        """
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are analyzing technical diagrams to answer specific questions about Azure Landing Zone requirements. Be precise and extract only verifiable information from the image."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"Question: {question}\n\nAnalyze the image and provide a specific answer. If the information is not visible in the image, clearly state 'Information not found in image'."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000,
                temperature=0.2
            )
            
            answer = response.choices[0].message.content
            
            # Determine if answer was found
            not_found_indicators = ["not found", "not visible", "cannot determine", "not shown", "not present"]
            found = not any(indicator in answer.lower() for indicator in not_found_indicators)
            
            return {
                "success": True,
                "answer": answer,
                "found": found,
                "confidence": 0.8 if found else 0.2,
                "model": self.deployment_name
            }
            
        except Exception as e:
            logger.error(f"GPT-4 Vision question answering failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "answer": "",
                "found": False,
                "confidence": 0.0
            }
    
    def extract_text_from_whiteboard(self, image_data: bytes) -> str:
        """
        Extract text from whiteboard photos or handwritten notes
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            Extracted text content
        """
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are extracting text from whiteboard photos or handwritten notes. Transcribe all visible text accurately, preserving structure and organization."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Please transcribe all text visible in this image. Maintain any lists, bullet points, or structure. Include all technical details, IP addresses, and specifications."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                temperature=0.1  # Very low for accurate transcription
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Whiteboard text extraction failed: {e}")
            return f"[Text extraction failed: {str(e)}]"
