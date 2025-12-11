"""
Azure Landing Zone Discovery Framework
Defines all required information for successful deployment
"""
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel


class DiscoveryCategory(str, Enum):
    """Categories of information to discover"""
    BUSINESS_CONTEXT = "Business Context"
    NETWORK_DESIGN = "Network Design"
    SECURITY_IDENTITY = "Security & Identity"
    GOVERNANCE = "Governance"
    COMPLIANCE = "Compliance & Regulatory"
    OPERATIONS = "Operations & Management"
    WORKLOAD_PLANNING = "Workload Planning"
    COST_BUDGETING = "Cost & Budgeting"
    INTEGRATION = "Integration & Connectivity"
    DISASTER_RECOVERY = "Disaster Recovery & Backup"


class InformationPriority(str, Enum):
    """Priority levels for discovery items"""
    CRITICAL = "critical"  # Must have before deployment
    HIGH = "high"  # Should have, can proceed with assumptions
    MEDIUM = "medium"  # Nice to have, can be defined later
    LOW = "low"  # Optional, can evolve over time


class DiscoveryQuestion(BaseModel):
    """A single discovery question"""
    id: str
    category: DiscoveryCategory
    question: str
    priority: InformationPriority
    help_text: Optional[str] = None
    examples: Optional[List[str]] = None
    validation_pattern: Optional[str] = None
    default_value: Optional[str] = None
    related_questions: Optional[List[str]] = None


class DiscoveryAnswer(BaseModel):
    """Answer to a discovery question"""
    question_id: str
    answer: str
    source: str  # "document", "user_input", "assumption"
    confidence: float  # 0.0 to 1.0
    document_reference: Optional[str] = None
    notes: Optional[str] = None


# Azure Landing Zone Discovery Framework
DISCOVERY_QUESTIONS: Dict[str, DiscoveryQuestion] = {
    
    # BUSINESS CONTEXT
    "biz_001": DiscoveryQuestion(
        id="biz_001",
        category=DiscoveryCategory.BUSINESS_CONTEXT,
        question="What is the primary business objective for moving to Azure?",
        priority=InformationPriority.CRITICAL,
        help_text="Understanding business drivers helps align technical decisions",
        examples=[
            "Digital transformation initiative",
            "Cost optimization and datacenter exit",
            "Support new products/services",
            "Improve agility and time-to-market"
        ]
    ),
    
    "biz_002": DiscoveryQuestion(
        id="biz_002",
        category=DiscoveryCategory.BUSINESS_CONTEXT,
        question="What is the expected timeline for Azure deployment?",
        priority=InformationPriority.CRITICAL,
        help_text="Timeline impacts design choices and migration strategy",
        examples=["3 months", "6 months", "12 months", "18+ months"]
    ),
    
    "biz_003": DiscoveryQuestion(
        id="biz_003",
        category=DiscoveryCategory.BUSINESS_CONTEXT,
        question="What are the critical workloads to migrate first?",
        priority=InformationPriority.HIGH,
        help_text="Identifies pilot workloads and initial design requirements"
    ),
    
    "biz_004": DiscoveryQuestion(
        id="biz_004",
        category=DiscoveryCategory.BUSINESS_CONTEXT,
        question="What is the organization's cloud maturity level?",
        priority=InformationPriority.MEDIUM,
        examples=["No cloud experience", "Some cloud pilots", "Cloud-first strategy", "Multi-cloud expertise"]
    ),
    
    # NETWORK DESIGN
    "net_001": DiscoveryQuestion(
        id="net_001",
        category=DiscoveryCategory.NETWORK_DESIGN,
        question="What IP address ranges are available for Azure VNets?",
        priority=InformationPriority.CRITICAL,
        help_text="Must not conflict with on-premises or other cloud networks",
        examples=["10.100.0.0/16", "172.16.0.0/12", "192.168.0.0/16"],
        validation_pattern=r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}$"
    ),
    
    "net_002": DiscoveryQuestion(
        id="net_002",
        category=DiscoveryCategory.NETWORK_DESIGN,
        question="What on-premises networks need connectivity to Azure?",
        priority=InformationPriority.CRITICAL,
        help_text="Determines ExpressRoute or VPN requirements"
    ),
    
    "net_003": DiscoveryQuestion(
        id="net_003",
        category=DiscoveryCategory.NETWORK_DESIGN,
        question="Preferred connectivity method: ExpressRoute, Site-to-Site VPN, or both?",
        priority=InformationPriority.CRITICAL,
        examples=["ExpressRoute (dedicated, low-latency)", "S2S VPN (cost-effective)", "Hybrid (both for redundancy)"]
    ),
    
    "net_004": DiscoveryQuestion(
        id="net_004",
        category=DiscoveryCategory.NETWORK_DESIGN,
        question="What is the required ExpressRoute bandwidth?",
        priority=InformationPriority.HIGH,
        examples=["50 Mbps", "100 Mbps", "500 Mbps", "1 Gbps", "10 Gbps"],
        related_questions=["net_003"]
    ),
    
    "net_005": DiscoveryQuestion(
        id="net_005",
        category=DiscoveryCategory.NETWORK_DESIGN,
        question="What is the hub-spoke topology design? (Number of spokes, segmentation strategy)",
        priority=InformationPriority.HIGH,
        help_text="Hub-spoke is Azure Landing Zone recommended pattern"
    ),
    
    "net_006": DiscoveryQuestion(
        id="net_006",
        category=DiscoveryCategory.NETWORK_DESIGN,
        question="What are the DNS server IPs (on-premises and Azure)?",
        priority=InformationPriority.HIGH,
        examples=["On-prem: 10.50.10.5, 10.50.10.6", "Azure: 168.63.129.16 (default)"]
    ),
    
    "net_007": DiscoveryQuestion(
        id="net_007",
        category=DiscoveryCategory.NETWORK_DESIGN,
        question="Are Private Endpoints required for Azure PaaS services?",
        priority=InformationPriority.MEDIUM,
        examples=["Yes, for all PaaS", "Only for critical services", "No, use service endpoints"]
    ),
    
    # SECURITY & IDENTITY
    "sec_001": DiscoveryQuestion(
        id="sec_001",
        category=DiscoveryCategory.SECURITY_IDENTITY,
        question="Is Multi-Factor Authentication (MFA) required for all users?",
        priority=InformationPriority.CRITICAL,
        examples=["Yes, all users", "Admins only", "Conditional access based"]
    ),
    
    "sec_002": DiscoveryQuestion(
        id="sec_002",
        category=DiscoveryCategory.SECURITY_IDENTITY,
        question="What is the identity provider? (Azure AD, Hybrid, Federated)",
        priority=InformationPriority.CRITICAL,
        examples=["Azure AD (cloud-only)", "Hybrid with AD Connect", "Federated (ADFS, PingFederate)"]
    ),
    
    "sec_003": DiscoveryQuestion(
        id="sec_003",
        category=DiscoveryCategory.SECURITY_IDENTITY,
        question="What encryption requirements exist? (at-rest, in-transit, CMK)",
        priority=InformationPriority.CRITICAL,
        help_text="Customer-Managed Keys (CMK) vs Microsoft-managed keys"
    ),
    
    "sec_004": DiscoveryQuestion(
        id="sec_004",
        category=DiscoveryCategory.SECURITY_IDENTITY,
        question="Is Privileged Identity Management (PIM) required?",
        priority=InformationPriority.HIGH,
        examples=["Yes, for all admins", "Yes, for production only", "No"]
    ),
    
    "sec_005": DiscoveryQuestion(
        id="sec_005",
        category=DiscoveryCategory.SECURITY_IDENTITY,
        question="What are the firewall requirements? (Azure Firewall, NVA, both)",
        priority=InformationPriority.HIGH,
        examples=["Azure Firewall", "Third-party NVA (Palo Alto, Fortinet)", "Hybrid approach"]
    ),
    
    "sec_006": DiscoveryQuestion(
        id="sec_006",
        category=DiscoveryCategory.SECURITY_IDENTITY,
        question="Is DDoS Protection Standard required?",
        priority=InformationPriority.MEDIUM,
        examples=["Yes, for internet-facing apps", "No, Basic tier sufficient"]
    ),
    
    "sec_007": DiscoveryQuestion(
        id="sec_007",
        category=DiscoveryCategory.SECURITY_IDENTITY,
        question="What SIEM solution will be used? (Sentinel, third-party)",
        priority=InformationPriority.MEDIUM,
        examples=["Azure Sentinel", "Splunk", "QRadar", "Existing on-prem SIEM"]
    ),
    
    # GOVERNANCE
    "gov_001": DiscoveryQuestion(
        id="gov_001",
        category=DiscoveryCategory.GOVERNANCE,
        question="What is the Azure subscription strategy? (per workload, per environment, per business unit)",
        priority=InformationPriority.CRITICAL,
        help_text="Subscription design impacts billing, limits, and isolation"
    ),
    
    "gov_002": DiscoveryQuestion(
        id="gov_002",
        category=DiscoveryCategory.GOVERNANCE,
        question="What Management Group hierarchy is required?",
        priority=InformationPriority.HIGH,
        examples=["Tenant Root > Platform > Landing Zones", "By geography", "By business unit"]
    ),
    
    "gov_003": DiscoveryQuestion(
        id="gov_003",
        category=DiscoveryCategory.GOVERNANCE,
        question="What mandatory tags must be enforced on all resources?",
        priority=InformationPriority.HIGH,
        examples=["CostCenter, Owner, Environment, Application", "ProjectCode, Compliance, DataClassification"]
    ),
    
    "gov_004": DiscoveryQuestion(
        id="gov_004",
        category=DiscoveryCategory.GOVERNANCE,
        question="What naming conventions will be used for Azure resources?",
        priority=InformationPriority.HIGH,
        help_text="Consistent naming aids management and automation",
        examples=["<resource-type>-<workload>-<env>-<region>-<instance>"]
    ),
    
    "gov_005": DiscoveryQuestion(
        id="gov_005",
        category=DiscoveryCategory.GOVERNANCE,
        question="Which Azure regions are approved for deployment?",
        priority=InformationPriority.CRITICAL,
        examples=["East US, West US", "West Europe, North Europe", "Southeast Asia, East Asia"]
    ),
    
    "gov_006": DiscoveryQuestion(
        id="gov_006",
        category=DiscoveryCategory.GOVERNANCE,
        question="What resource types are prohibited? (VM sizes, services)",
        priority=InformationPriority.MEDIUM,
        examples=["No F-series VMs", "No Basic tier services", "No public IPs on VMs"]
    ),
    
    # COMPLIANCE
    "comp_001": DiscoveryQuestion(
        id="comp_001",
        category=DiscoveryCategory.COMPLIANCE,
        question="What regulatory compliance requirements apply? (HIPAA, PCI-DSS, SOC2, ISO)",
        priority=InformationPriority.CRITICAL,
        help_text="Determines required controls and certifications"
    ),
    
    "comp_002": DiscoveryQuestion(
        id="comp_002",
        category=DiscoveryCategory.COMPLIANCE,
        question="What is the data sovereignty requirement? (data residency, cross-border restrictions)",
        priority=InformationPriority.CRITICAL,
        examples=["Data must stay in US", "EU GDPR compliance", "No restrictions"]
    ),
    
    "comp_003": DiscoveryQuestion(
        id="comp_003",
        category=DiscoveryCategory.COMPLIANCE,
        question="What is the required audit log retention period?",
        priority=InformationPriority.HIGH,
        examples=["90 days", "1 year", "7 years (financial)", "Indefinite"]
    ),
    
    "comp_004": DiscoveryQuestion(
        id="comp_004",
        category=DiscoveryCategory.COMPLIANCE,
        question="Are there specific security frameworks to follow? (NIST, CIS, Azure Security Benchmark)",
        priority=InformationPriority.HIGH
    ),
    
    # OPERATIONS
    "ops_001": DiscoveryQuestion(
        id="ops_001",
        category=DiscoveryCategory.OPERATIONS,
        question="What monitoring solution will be used? (Azure Monitor, third-party)",
        priority=InformationPriority.HIGH,
        examples=["Azure Monitor + Log Analytics", "Datadog", "Dynatrace", "Hybrid"]
    ),
    
    "ops_002": DiscoveryQuestion(
        id="ops_002",
        category=DiscoveryCategory.OPERATIONS,
        question="What are the SLA requirements for production workloads?",
        priority=InformationPriority.HIGH,
        examples=["99.9% (3-9s)", "99.95% (zone-redundant)", "99.99% (4-9s)", "99.999% (5-9s)"]
    ),
    
    "ops_003": DiscoveryQuestion(
        id="ops_003",
        category=DiscoveryCategory.OPERATIONS,
        question="What is the maintenance window for production systems?",
        priority=InformationPriority.MEDIUM,
        examples=["Saturday 2-6 AM EST", "No maintenance window (always-on)", "Flexible"]
    ),
    
    "ops_004": DiscoveryQuestion(
        id="ops_004",
        category=DiscoveryCategory.OPERATIONS,
        question="Is automation required for provisioning? (IaC tool preference)",
        priority=InformationPriority.HIGH,
        examples=["Terraform", "Bicep", "ARM Templates", "Azure DevOps Pipelines", "GitHub Actions"]
    ),
    
    "ops_005": DiscoveryQuestion(
        id="ops_005",
        category=DiscoveryCategory.OPERATIONS,
        question="What ticketing/ITSM system is used?",
        priority=InformationPriority.MEDIUM,
        examples=["ServiceNow", "Jira Service Desk", "BMC Remedy", "Azure DevOps"]
    ),
    
    # DISASTER RECOVERY
    "dr_001": DiscoveryQuestion(
        id="dr_001",
        category=DiscoveryCategory.DISASTER_RECOVERY,
        question="What are the RPO (Recovery Point Objective) requirements?",
        priority=InformationPriority.CRITICAL,
        help_text="How much data loss is acceptable",
        examples=["15 minutes", "1 hour", "4 hours", "24 hours"]
    ),
    
    "dr_002": DiscoveryQuestion(
        id="dr_002",
        category=DiscoveryCategory.DISASTER_RECOVERY,
        question="What are the RTO (Recovery Time Objective) requirements?",
        priority=InformationPriority.CRITICAL,
        help_text="How quickly must systems be restored",
        examples=["1 hour", "4 hours", "8 hours", "24 hours"]
    ),
    
    "dr_003": DiscoveryQuestion(
        id="dr_003",
        category=DiscoveryCategory.DISASTER_RECOVERY,
        question="Is multi-region deployment required for DR?",
        priority=InformationPriority.HIGH,
        examples=["Yes, active-active", "Yes, active-passive", "No, zone-redundant sufficient"]
    ),
    
    "dr_004": DiscoveryQuestion(
        id="dr_004",
        category=DiscoveryCategory.DISASTER_RECOVERY,
        question="What backup retention policy is required?",
        priority=InformationPriority.HIGH,
        examples=["Daily for 30 days", "Daily/7d, Weekly/4w, Monthly/12m, Yearly/7y"]
    ),
    
    # COST & BUDGETING
    "cost_001": DiscoveryQuestion(
        id="cost_001",
        category=DiscoveryCategory.COST_BUDGETING,
        question="What is the approved budget for Azure (Year 1)?",
        priority=InformationPriority.CRITICAL,
        examples=["$100K", "$500K", "$1M", "$5M+"]
    ),
    
    "cost_002": DiscoveryQuestion(
        id="cost_002",
        category=DiscoveryCategory.COST_BUDGETING,
        question="How should costs be allocated? (business unit, project, environment)",
        priority=InformationPriority.HIGH
    ),
    
    "cost_003": DiscoveryQuestion(
        id="cost_003",
        category=DiscoveryCategory.COST_BUDGETING,
        question="Are Azure Reservations or Savings Plans being considered?",
        priority=InformationPriority.MEDIUM,
        examples=["Yes, 1-year commitment", "Yes, 3-year commitment", "No, pay-as-you-go"]
    ),
    
    "cost_004": DiscoveryQuestion(
        id="cost_004",
        category=DiscoveryCategory.COST_BUDGETING,
        question="What cost alert thresholds should be configured?",
        priority=InformationPriority.MEDIUM,
        examples=["80% budget warning, 90% critical", "Monthly variance >10%"]
    ),
    
    # INTEGRATION
    "int_001": DiscoveryQuestion(
        id="int_001",
        category=DiscoveryCategory.INTEGRATION,
        question="What on-premises systems need integration with Azure?",
        priority=InformationPriority.HIGH,
        examples=["Active Directory", "SAP", "Oracle ERP", "File servers", "Databases"]
    ),
    
    "int_002": DiscoveryQuestion(
        id="int_002",
        category=DiscoveryCategory.INTEGRATION,
        question="Are hybrid file services required? (Azure File Sync, NetApp)",
        priority=InformationPriority.MEDIUM
    ),
    
    "int_003": DiscoveryQuestion(
        id="int_003",
        category=DiscoveryCategory.INTEGRATION,
        question="What third-party SaaS applications need integration?",
        priority=InformationPriority.MEDIUM,
        examples=["Salesforce", "Office 365", "ServiceNow", "Workday"]
    ),
    
    # WORKLOAD PLANNING
    "wkld_001": DiscoveryQuestion(
        id="wkld_001",
        category=DiscoveryCategory.WORKLOAD_PLANNING,
        question="How many VMs are expected in Year 1?",
        priority=InformationPriority.HIGH,
        examples=["<50", "50-200", "200-500", "500+"]
    ),
    
    "wkld_002": DiscoveryQuestion(
        id="wkld_002",
        category=DiscoveryCategory.WORKLOAD_PLANNING,
        question="What application architectures will be used? (IaaS, PaaS, containers, serverless)",
        priority=InformationPriority.HIGH
    ),
    
    "wkld_003": DiscoveryQuestion(
        id="wkld_003",
        category=DiscoveryCategory.WORKLOAD_PLANNING,
        question="Is Kubernetes/AKS required? If yes, how many clusters?",
        priority=InformationPriority.MEDIUM
    ),
    
    "wkld_004": DiscoveryQuestion(
        id="wkld_004",
        category=DiscoveryCategory.WORKLOAD_PLANNING,
        question="What database platforms are needed? (SQL, Cosmos DB, PostgreSQL, MySQL)",
        priority=InformationPriority.HIGH
    ),
}


def get_questions_by_category(category: DiscoveryCategory) -> List[DiscoveryQuestion]:
    """Get all questions for a specific category"""
    return [q for q in DISCOVERY_QUESTIONS.values() if q.category == category]


def get_questions_by_priority(priority: InformationPriority) -> List[DiscoveryQuestion]:
    """Get all questions of a specific priority"""
    return [q for q in DISCOVERY_QUESTIONS.values() if q.priority == priority]


def get_critical_questions() -> List[DiscoveryQuestion]:
    """Get all CRITICAL priority questions"""
    return get_questions_by_priority(InformationPriority.CRITICAL)
