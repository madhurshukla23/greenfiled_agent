"""
Vision AI Integration for Architecture Diagram Analysis
Extracts information from network diagrams, flowcharts, and architecture visuals
"""
import logging
from typing import List, Dict, Optional
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential

logger = logging.getLogger(__name__)


class VisionDiagramAnalyzer:
    """Analyzes architecture diagrams using Azure AI Vision"""
    
    def __init__(self, endpoint: str, api_key: str):
        self.client = ImageAnalysisClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(api_key)
        )
    
    def analyze_diagram_from_url(self, image_url: str) -> Dict:
        """Analyze architecture diagram from URL"""
        try:
            result = self.client.analyze_from_url(
                image_url=image_url,
                visual_features=[
                    VisualFeatures.CAPTION,
                    VisualFeatures.DENSE_CAPTIONS,
                    VisualFeatures.TAGS,
                    VisualFeatures.OBJECTS,
                    VisualFeatures.READ
                ]
            )
            
            return self._process_vision_results(result)
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            return {}
    
    def analyze_diagram_from_file(self, image_path: str) -> Dict:
        """Analyze architecture diagram from local file"""
        try:
            with open(image_path, 'rb') as image_data:
                result = self.client.analyze(
                    image_data=image_data,
                    visual_features=[
                        VisualFeatures.CAPTION,
                        VisualFeatures.DENSE_CAPTIONS,
                        VisualFeatures.TAGS,
                        VisualFeatures.OBJECTS,
                        VisualFeatures.READ
                    ]
                )
            
            return self._process_vision_results(result)
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            return {}
    
    def _process_vision_results(self, result) -> Dict:
        """Process vision analysis results"""
        extracted_info = {
            'description': '',
            'components': [],
            'text_content': [],
            'network_elements': [],
            'confidence': 0.0
        }
        
        # Main caption
        if hasattr(result, 'caption') and result.caption:
            extracted_info['description'] = result.caption.text
            extracted_info['confidence'] = result.caption.confidence
        
        # Dense captions (detailed descriptions)
        if hasattr(result, 'dense_captions') and result.dense_captions:
            for caption in result.dense_captions.list:
                extracted_info['components'].append({
                    'description': caption.text,
                    'confidence': caption.confidence,
                    'bbox': caption.bounding_box if hasattr(caption, 'bounding_box') else None
                })
        
        # Tags (keywords found in image)
        if hasattr(result, 'tags') and result.tags:
            azure_tags = [tag.name for tag in result.tags.list if self._is_azure_related(tag.name)]
            extracted_info['network_elements'].extend(azure_tags)
        
        # OCR text (read text from diagram)
        if hasattr(result, 'read') and result.read:
            for block in result.read.blocks:
                for line in block.lines:
                    extracted_info['text_content'].append(line.text)
        
        # Parse for Azure-specific information
        extracted_info['azure_services'] = self._extract_azure_services(extracted_info)
        extracted_info['ip_addresses'] = self._extract_ip_addresses(extracted_info['text_content'])
        extracted_info['subnet_info'] = self._extract_subnet_info(extracted_info['text_content'])
        
        return extracted_info
    
    def _is_azure_related(self, tag: str) -> bool:
        """Check if tag is Azure-related"""
        azure_keywords = [
            'azure', 'vnet', 'subnet', 'nsg', 'firewall', 'gateway', 
            'vpn', 'expressroute', 'load balancer', 'application gateway',
            'vm', 'virtual machine', 'storage', 'database', 'network'
        ]
        return any(keyword in tag.lower() for keyword in azure_keywords)
    
    def _extract_azure_services(self, info: Dict) -> List[str]:
        """Extract Azure service names from extracted information"""
        services = set()
        
        # Service name patterns
        service_patterns = {
            'Virtual Network': ['vnet', 'virtual network', 'network'],
            'VPN Gateway': ['vpn gateway', 'vpn', 'site-to-site'],
            'ExpressRoute': ['expressroute', 'express route'],
            'Azure Firewall': ['firewall', 'azure firewall'],
            'Application Gateway': ['app gateway', 'application gateway', 'waf'],
            'Load Balancer': ['load balancer', 'lb'],
            'Network Security Group': ['nsg', 'security group'],
            'Virtual Machine': ['vm', 'virtual machine'],
            'Storage Account': ['storage', 'blob', 'file share'],
            'Azure SQL': ['sql', 'database'],
            'Cosmos DB': ['cosmos', 'cosmosdb'],
            'Key Vault': ['key vault', 'keyvault', 'kv'],
            'Log Analytics': ['log analytics', 'logs', 'monitoring']
        }
        
        # Check all text content
        all_text = ' '.join(info.get('text_content', [])).lower()
        all_text += ' ' + info.get('description', '').lower()
        all_text += ' ' + ' '.join([c['description'] for c in info.get('components', [])]).lower()
        
        for service_name, patterns in service_patterns.items():
            if any(pattern in all_text for pattern in patterns):
                services.add(service_name)
        
        return list(services)
    
    def _extract_ip_addresses(self, text_lines: List[str]) -> List[str]:
        """Extract IP addresses from text"""
        import re
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b'
        
        ip_addresses = []
        for line in text_lines:
            matches = re.findall(ip_pattern, line)
            ip_addresses.extend(matches)
        
        return list(set(ip_addresses))
    
    def _extract_subnet_info(self, text_lines: List[str]) -> List[Dict]:
        """Extract subnet information from text"""
        import re
        subnets = []
        
        # Pattern to match subnet definitions
        # Examples: "subnet-1: 10.0.1.0/24", "GatewaySubnet 10.0.0.0/27"
        subnet_pattern = r'(\w+[-_]?\w*subnet\w*)[:\s]+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2})'
        
        for line in text_lines:
            matches = re.findall(subnet_pattern, line, re.IGNORECASE)
            for name, cidr in matches:
                subnets.append({
                    'name': name.strip(),
                    'cidr': cidr
                })
        
        return subnets
    
    def generate_discovery_insights(self, vision_results: Dict) -> List[Dict]:
        """Generate discovery question insights from vision analysis"""
        insights = []
        
        # IP addressing insights
        if vision_results.get('ip_addresses'):
            insights.append({
                'question_id': 'net_001',
                'suggested_answer': ', '.join(vision_results['ip_addresses']),
                'confidence': 0.8,
                'source': 'architecture_diagram'
            })
        
        # Subnet information
        if vision_results.get('subnet_info'):
            subnet_desc = '; '.join([
                f"{s['name']}: {s['cidr']}" for s in vision_results['subnet_info']
            ])
            insights.append({
                'question_id': 'net_005',
                'suggested_answer': subnet_desc,
                'confidence': 0.75,
                'source': 'architecture_diagram'
            })
        
        # Azure services detected
        if vision_results.get('azure_services'):
            services_desc = ', '.join(vision_results['azure_services'])
            insights.append({
                'question_id': 'workload_001',
                'suggested_answer': f"Diagram shows: {services_desc}",
                'confidence': 0.7,
                'source': 'architecture_diagram'
            })
        
        # Connectivity method (check for VPN/ExpressRoute)
        services = vision_results.get('azure_services', [])
        if 'VPN Gateway' in services or 'ExpressRoute' in services:
            connectivity = []
            if 'VPN Gateway' in services:
                connectivity.append('VPN')
            if 'ExpressRoute' in services:
                connectivity.append('ExpressRoute')
            
            insights.append({
                'question_id': 'net_003',
                'suggested_answer': ' + '.join(connectivity),
                'confidence': 0.85,
                'source': 'architecture_diagram'
            })
        
        return insights
