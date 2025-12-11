"""
Azure Best Practices Validation Engine
Validates answers against Azure Landing Zone best practices
"""
import re
from typing import List, Optional, Tuple, Dict
from enum import Enum
import ipaddress


class ValidationSeverity(str, Enum):
    """Severity levels for validation findings"""
    ERROR = "error"  # Blocks deployment
    WARNING = "warning"  # Should be addressed
    INFO = "info"  # Recommendation
    SUCCESS = "success"  # Meets best practices


class ValidationResult:
    """Result of a validation check"""
    def __init__(
        self,
        severity: ValidationSeverity,
        message: str,
        recommendation: Optional[str] = None
    ):
        self.severity = severity
        self.message = message
        self.recommendation = recommendation


class AzureValidator:
    """Validates Azure Landing Zone configurations"""
    
    @staticmethod
    def validate_ip_range(ip_range: str) -> List[ValidationResult]:
        """Validate IP address range for Azure VNet"""
        results = []
        
        try:
            network = ipaddress.ip_network(ip_range, strict=False)
            
            # Check if private IP space
            if not network.is_private:
                results.append(ValidationResult(
                    ValidationSeverity.ERROR,
                    f"IP range {ip_range} is not in private address space",
                    "Use private IP ranges: 10.0.0.0/8, 172.16.0.0/12, or 192.168.0.0/16"
                ))
            
            # Check subnet size
            if network.prefixlen > 29:
                results.append(ValidationResult(
                    ValidationSeverity.WARNING,
                    f"Subnet /{network.prefixlen} is very small (max {2**(32-network.prefixlen)-5} usable IPs)",
                    "Consider using /24 or larger for production workloads"
                ))
            elif network.prefixlen < 16:
                results.append(ValidationResult(
                    ValidationSeverity.WARNING,
                    f"Network /{network.prefixlen} is very large",
                    "Consider segmenting into smaller VNets for better security and management"
                ))
            
            # Best practice: /16 for VNet, /24 for subnets
            if 16 <= network.prefixlen <= 24:
                results.append(ValidationResult(
                    ValidationSeverity.SUCCESS,
                    f"IP range {ip_range} follows Azure best practices"
                ))
                
        except ValueError as e:
            results.append(ValidationResult(
                ValidationSeverity.ERROR,
                f"Invalid IP range format: {ip_range}",
                "Use CIDR notation (e.g., 10.0.0.0/16)"
            ))
        
        return results
    
    @staticmethod
    def validate_naming_convention(name: str, resource_type: str) -> List[ValidationResult]:
        """Validate Azure resource naming conventions"""
        results = []
        
        # General naming rules
        if not re.match(r'^[a-z0-9-]+$', name.lower()):
            results.append(ValidationResult(
                ValidationSeverity.WARNING,
                f"Name '{name}' contains invalid characters",
                "Use lowercase letters, numbers, and hyphens only"
            ))
        
        # Length check (most Azure resources: 1-63 chars)
        if len(name) > 63:
            results.append(ValidationResult(
                ValidationSeverity.ERROR,
                f"Name '{name}' is too long ({len(name)} chars, max 63)",
                "Shorten the resource name"
            ))
        elif len(name) < 3:
            results.append(ValidationResult(
                ValidationSeverity.WARNING,
                f"Name '{name}' is very short",
                "Consider using descriptive names for better management"
            ))
        
        # Check for recommended prefixes
        recommended_prefixes = {
            'vnet': ['vnet-', 'vn-'],
            'subnet': ['snet-', 'sub-'],
            'nsg': ['nsg-'],
            'vm': ['vm-'],
            'storage': ['st', 'stor'],
            'keyvault': ['kv-'],
            'law': ['law-', 'log-']
        }
        
        if resource_type in recommended_prefixes:
            has_prefix = any(name.lower().startswith(prefix) for prefix in recommended_prefixes[resource_type])
            if not has_prefix:
                results.append(ValidationResult(
                    ValidationSeverity.INFO,
                    f"Consider using recommended prefix for {resource_type}",
                    f"Suggested prefixes: {', '.join(recommended_prefixes[resource_type])}"
                ))
        
        return results
    
    @staticmethod
    def validate_environment_separation(answer: str) -> List[ValidationResult]:
        """Validate environment separation strategy"""
        results = []
        
        answer_lower = answer.lower()
        
        # Check for subscription-level isolation (recommended)
        if 'subscription' in answer_lower and 'separate' in answer_lower:
            results.append(ValidationResult(
                ValidationSeverity.SUCCESS,
                "Subscription-level isolation follows Azure best practices",
                "This provides the strongest security boundary and governance"
            ))
        # Resource group isolation (acceptable but less secure)
        elif 'resource group' in answer_lower:
            results.append(ValidationResult(
                ValidationSeverity.INFO,
                "Resource group isolation is acceptable for small deployments",
                "Consider subscription-level isolation for production workloads"
            ))
        # Single environment (not recommended)
        elif 'single' in answer_lower or 'same' in answer_lower:
            results.append(ValidationResult(
                ValidationSeverity.WARNING,
                "Single environment approach increases risk",
                "Strongly recommend separating dev, test, and production environments"
            ))
        
        return results
    
    @staticmethod
    def validate_backup_strategy(answer: str) -> List[ValidationResult]:
        """Validate backup and DR strategy"""
        results = []
        
        answer_lower = answer.lower()
        
        # Check for RPO/RTO defined
        has_rpo = 'rpo' in answer_lower or 'recovery point' in answer_lower
        has_rto = 'rto' in answer_lower or 'recovery time' in answer_lower
        
        if has_rpo and has_rto:
            results.append(ValidationResult(
                ValidationSeverity.SUCCESS,
                "RPO and RTO objectives defined",
                "Ensure backup solutions meet these requirements"
            ))
        else:
            missing = []
            if not has_rpo:
                missing.append("RPO (Recovery Point Objective)")
            if not has_rto:
                missing.append("RTO (Recovery Time Objective)")
            
            results.append(ValidationResult(
                ValidationSeverity.WARNING,
                f"Missing critical DR metrics: {', '.join(missing)}",
                "Define RPO and RTO to determine appropriate backup strategy"
            ))
        
        # Check for geo-redundancy
        if 'geo' in answer_lower or 'region' in answer_lower:
            results.append(ValidationResult(
                ValidationSeverity.SUCCESS,
                "Geo-redundancy mentioned for disaster recovery"
            ))
        else:
            results.append(ValidationResult(
                ValidationSeverity.INFO,
                "Consider geo-redundancy for critical workloads",
                "Azure Backup and ASR support cross-region replication"
            ))
        
        return results
    
    @staticmethod
    def validate_connectivity_method(answer: str) -> List[ValidationResult]:
        """Validate hybrid connectivity choices"""
        results = []
        
        answer_lower = answer.lower()
        
        # ExpressRoute (recommended for production)
        if 'expressroute' in answer_lower or 'express route' in answer_lower:
            results.append(ValidationResult(
                ValidationSeverity.SUCCESS,
                "ExpressRoute provides dedicated, low-latency connectivity",
                "Recommended for production workloads with high throughput needs"
            ))
        
        # VPN (acceptable for dev/test)
        elif 'vpn' in answer_lower:
            results.append(ValidationResult(
                ValidationSeverity.INFO,
                "VPN is cost-effective but has bandwidth/latency limitations",
                "Consider ExpressRoute for production workloads or high data transfer"
            ))
        
        # Dual connectivity (best practice)
        if ('expressroute' in answer_lower or 'express route' in answer_lower) and 'vpn' in answer_lower:
            results.append(ValidationResult(
                ValidationSeverity.SUCCESS,
                "Dual connectivity (ExpressRoute + VPN) provides redundancy",
                "This is the best practice for mission-critical workloads"
            ))
        
        return results
    
    @staticmethod
    def validate_budget(answer: str) -> List[ValidationResult]:
        """Validate budget and cost management"""
        results = []
        
        answer_lower = answer.lower()
        
        # Check if budget amount is specified
        if re.search(r'\$[\d,]+|\d+\s*(k|thousand|m|million)', answer_lower):
            results.append(ValidationResult(
                ValidationSeverity.SUCCESS,
                "Budget amount specified"
            ))
        else:
            results.append(ValidationResult(
                ValidationSeverity.WARNING,
                "No specific budget amount mentioned",
                "Define a clear budget to enable cost controls and alerts"
            ))
        
        # Check for cost monitoring
        if 'monitor' in answer_lower or 'alert' in answer_lower or 'budget alert' in answer_lower:
            results.append(ValidationResult(
                ValidationSeverity.SUCCESS,
                "Cost monitoring mentioned",
                "Azure Cost Management provides budgets, alerts, and recommendations"
            ))
        
        return results
    
    @staticmethod
    def validate_security_requirements(answer: str) -> List[ValidationResult]:
        """Validate security and compliance requirements"""
        results = []
        
        answer_lower = answer.lower()
        
        # Check for compliance frameworks
        frameworks = {
            'pci': 'PCI-DSS',
            'hipaa': 'HIPAA',
            'soc': 'SOC 2',
            'iso': 'ISO 27001',
            'gdpr': 'GDPR',
            'fedramp': 'FedRAMP'
        }
        
        found_frameworks = [name for key, name in frameworks.items() if key in answer_lower]
        
        if found_frameworks:
            results.append(ValidationResult(
                ValidationSeverity.SUCCESS,
                f"Compliance frameworks identified: {', '.join(found_frameworks)}",
                "Ensure Landing Zone meets these compliance requirements"
            ))
        
        # Check for MFA
        if 'mfa' in answer_lower or 'multi-factor' in answer_lower:
            results.append(ValidationResult(
                ValidationSeverity.SUCCESS,
                "MFA requirement mentioned - critical for security"
            ))
        else:
            results.append(ValidationResult(
                ValidationSeverity.WARNING,
                "MFA not mentioned in security requirements",
                "Strongly recommend enforcing MFA for all user access"
            ))
        
        return results


class QuestionValidator:
    """Validates answers to specific discovery questions"""
    
    VALIDATORS: Dict[str, callable] = {
        'net_001': AzureValidator.validate_ip_range,
        'gov_003': AzureValidator.validate_environment_separation,
        'dr_001': AzureValidator.validate_backup_strategy,
        'net_003': AzureValidator.validate_connectivity_method,
        'cost_001': AzureValidator.validate_budget,
        'sec_001': AzureValidator.validate_security_requirements,
    }
    
    @staticmethod
    def validate_answer(question_id: str, answer: str) -> List[ValidationResult]:
        """Validate an answer based on question ID"""
        validator = QuestionValidator.VALIDATORS.get(question_id)
        
        if validator:
            return validator(answer)
        
        return []  # No specific validation for this question
