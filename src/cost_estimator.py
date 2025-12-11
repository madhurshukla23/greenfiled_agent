"""
Azure Cost Estimation Engine
Estimates Azure costs based on Landing Zone requirements
"""
from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass


class AzureRegion(str, Enum):
    """Azure regions for pricing"""
    EAST_US = "eastus"
    EAST_US_2 = "eastus2"
    WEST_US = "westus"
    WEST_US_2 = "westus2"
    WEST_EUROPE = "westeurope"
    NORTH_EUROPE = "northeurope"


@dataclass
class CostEstimate:
    """Cost estimate for a resource"""
    resource_type: str
    resource_name: str
    monthly_cost: float
    annual_cost: float
    assumptions: List[str]
    details: Optional[str] = None


class AzureCostEstimator:
    """Estimates Azure Landing Zone costs"""
    
    # Approximate monthly costs (USD) - update with current pricing
    BASE_PRICING = {
        # Networking
        "vnet": 0,  # VNets are free
        "expressroute_50mbps": 55,
        "expressroute_100mbps": 100,
        "expressroute_200mbps": 190,
        "expressroute_500mbps": 460,
        "expressroute_1gbps": 950,
        "expressroute_10gbps": 8500,
        "vpn_gateway_basic": 27,
        "vpn_gateway_vpngw1": 140,
        "vpn_gateway_vpngw2": 360,
        "application_gateway_v2": 250,
        "firewall_premium": 1250,
        "firewall_standard": 625,
        
        # Compute (per VM)
        "vm_d2s_v3": 70,  # 2 vCPU, 8GB
        "vm_d4s_v3": 140,  # 4 vCPU, 16GB
        "vm_d8s_v3": 280,  # 8 vCPU, 32GB
        
        # Storage (per TB)
        "storage_blob_hot": 18,
        "storage_blob_cool": 10,
        "storage_blob_archive": 1,
        "storage_disk_premium_p30": 135,  # 1TB SSD
        
        # Database
        "sql_db_s3": 150,  # 100 DTU
        "cosmos_db_400ru": 24,
        
        # Monitoring & Security
        "log_analytics_100gb": 230,
        "sentinel_100gb": 200,
        "security_center_standard_per_vm": 15,
        "backup_per_vm": 10,
        
        # Identity
        "aad_premium_p1_per_user": 6,
        "aad_premium_p2_per_user": 9,
    }
    
    def __init__(self, region: AzureRegion = AzureRegion.EAST_US):
        self.region = region
        self.region_multiplier = self._get_region_multiplier()
    
    def _get_region_multiplier(self) -> float:
        """Get pricing multiplier for region"""
        multipliers = {
            AzureRegion.EAST_US: 1.0,
            AzureRegion.EAST_US_2: 1.0,
            AzureRegion.WEST_US: 1.05,
            AzureRegion.WEST_US_2: 1.0,
            AzureRegion.WEST_EUROPE: 1.15,
            AzureRegion.NORTH_EUROPE: 1.1,
        }
        return multipliers.get(self.region, 1.0)
    
    def estimate_networking(self, requirements: Dict) -> List[CostEstimate]:
        """Estimate networking costs"""
        estimates = []
        
        # ExpressRoute
        er_bandwidth = requirements.get('expressroute_bandwidth', '').lower()
        if 'expressroute' in requirements.get('connectivity_method', '').lower():
            bandwidth_map = {
                '50': 'expressroute_50mbps',
                '100': 'expressroute_100mbps',
                '200': 'expressroute_200mbps',
                '500': 'expressroute_500mbps',
                '1': 'expressroute_1gbps',
                '10': 'expressroute_10gbps',
            }
            
            for key, resource in bandwidth_map.items():
                if key in er_bandwidth:
                    monthly = self.BASE_PRICING[resource] * self.region_multiplier
                    estimates.append(CostEstimate(
                        resource_type="ExpressRoute",
                        resource_name=f"ExpressRoute Circuit ({key} {'Gbps' if key in ['1', '10'] else 'Mbps'})",
                        monthly_cost=monthly,
                        annual_cost=monthly * 12,
                        assumptions=["Unlimited data plan", "Standard SKU"],
                        details=f"Dedicated hybrid connectivity to on-premises"
                    ))
                    break
        
        # VPN Gateway
        if 'vpn' in requirements.get('connectivity_method', '').lower():
            monthly = self.BASE_PRICING['vpn_gateway_vpngw1'] * self.region_multiplier
            estimates.append(CostEstimate(
                resource_type="VPN Gateway",
                resource_name="VPN Gateway (VpnGw1)",
                monthly_cost=monthly,
                annual_cost=monthly * 12,
                assumptions=["VpnGw1 SKU", "Active-passive configuration"],
                details="Site-to-site VPN for hybrid connectivity"
            ))
        
        # Azure Firewall
        if requirements.get('use_firewall', True):
            fw_type = 'firewall_premium' if 'premium' in requirements.get('firewall_sku', '').lower() else 'firewall_standard'
            monthly = self.BASE_PRICING[fw_type] * self.region_multiplier
            estimates.append(CostEstimate(
                resource_type="Azure Firewall",
                resource_name=f"Azure Firewall ({'Premium' if fw_type == 'firewall_premium' else 'Standard'})",
                monthly_cost=monthly,
                annual_cost=monthly * 12,
                assumptions=["Deployed in hub VNet", "Moderate traffic (<10TB/month)"],
                details="Centralized network security and traffic filtering"
            ))
        
        # Application Gateway (if web workloads)
        if requirements.get('web_workloads', False):
            monthly = self.BASE_PRICING['application_gateway_v2'] * self.region_multiplier
            estimates.append(CostEstimate(
                resource_type="Application Gateway",
                resource_name="Application Gateway v2",
                monthly_cost=monthly,
                annual_cost=monthly * 12,
                assumptions=["WAF enabled", "2 capacity units", "Moderate traffic"],
                details="Web application firewall and load balancer"
            ))
        
        return estimates
    
    def estimate_compute(self, requirements: Dict) -> List[CostEstimate]:
        """Estimate compute costs"""
        estimates = []
        
        vm_count = requirements.get('vm_count', 0)
        if vm_count > 0:
            vm_size = requirements.get('vm_size', 'd2s_v3').lower()
            vm_resource = f"vm_{vm_size}" if f"vm_{vm_size}" in self.BASE_PRICING else 'vm_d2s_v3'
            
            monthly_per_vm = self.BASE_PRICING[vm_resource] * self.region_multiplier
            total_monthly = monthly_per_vm * vm_count
            
            estimates.append(CostEstimate(
                resource_type="Virtual Machines",
                resource_name=f"{vm_count}x {vm_size.upper()} VMs",
                monthly_cost=total_monthly,
                annual_cost=total_monthly * 12,
                assumptions=[
                    "Pay-as-you-go pricing",
                    "24x7 runtime",
                    f"Avg cost: ${monthly_per_vm:.2f}/VM/month"
                ],
                details=f"Estimated for {vm_count} VMs running continuously"
            ))
            
            # Reserved instances savings (1-year RI ~30% savings)
            ri_monthly = total_monthly * 0.7
            ri_savings = (total_monthly - ri_monthly) * 12
            estimates.append(CostEstimate(
                resource_type="Reserved Instances",
                resource_name=f"1-Year RI Savings for {vm_count} VMs",
                monthly_cost=-1 * (total_monthly - ri_monthly),
                annual_cost=-1 * ri_savings,
                assumptions=["1-year commitment", "~30% discount"],
                details=f"Potential annual savings: ${ri_savings:,.2f}"
            ))
        
        return estimates
    
    def estimate_storage(self, requirements: Dict) -> List[CostEstimate]:
        """Estimate storage costs"""
        estimates = []
        
        storage_tb = requirements.get('storage_tb', 0)
        if storage_tb > 0:
            monthly = self.BASE_PRICING['storage_blob_hot'] * storage_tb * self.region_multiplier
            estimates.append(CostEstimate(
                resource_type="Blob Storage",
                resource_name=f"{storage_tb}TB Blob Storage (Hot tier)",
                monthly_cost=monthly,
                annual_cost=monthly * 12,
                assumptions=["Hot access tier", "LRS redundancy", "Standard performance"],
                details="Primary data storage"
            ))
        
        return estimates
    
    def estimate_monitoring(self, requirements: Dict) -> List[CostEstimate]:
        """Estimate monitoring and security costs"""
        estimates = []
        
        vm_count = requirements.get('vm_count', 0)
        
        # Log Analytics
        log_size_gb = max(100, vm_count * 10)  # ~10GB per VM
        monthly = (log_size_gb / 100) * self.BASE_PRICING['log_analytics_100gb']
        estimates.append(CostEstimate(
            resource_type="Log Analytics",
            resource_name=f"Log Analytics Workspace (~{log_size_gb}GB/month)",
            monthly_cost=monthly,
            annual_cost=monthly * 12,
            assumptions=["Pay-as-you-go tier", f"~{log_size_gb}GB ingestion/month"],
            details="Centralized logging and monitoring"
        ))
        
        # Defender for Cloud (per VM)
        if vm_count > 0:
            monthly = self.BASE_PRICING['security_center_standard_per_vm'] * vm_count
            estimates.append(CostEstimate(
                resource_type="Defender for Cloud",
                resource_name=f"Defender for Cloud ({vm_count} VMs)",
                monthly_cost=monthly,
                annual_cost=monthly * 12,
                assumptions=["Standard tier", f"${self.BASE_PRICING['security_center_standard_per_vm']}/VM/month"],
                details="Advanced threat protection and security posture management"
            ))
        
        # Azure Backup
        if vm_count > 0:
            monthly = self.BASE_PRICING['backup_per_vm'] * vm_count
            estimates.append(CostEstimate(
                resource_type="Azure Backup",
                resource_name=f"VM Backup ({vm_count} VMs)",
                monthly_cost=monthly,
                annual_cost=monthly * 12,
                assumptions=["Standard tier", "Daily backups", "30-day retention"],
                details="Automated backup and disaster recovery"
            ))
        
        return estimates
    
    def generate_full_estimate(self, requirements: Dict) -> Dict:
        """Generate complete cost estimate"""
        all_estimates = []
        
        all_estimates.extend(self.estimate_networking(requirements))
        all_estimates.extend(self.estimate_compute(requirements))
        all_estimates.extend(self.estimate_storage(requirements))
        all_estimates.extend(self.estimate_monitoring(requirements))
        
        total_monthly = sum(e.monthly_cost for e in all_estimates if e.monthly_cost > 0)
        total_annual = sum(e.annual_cost for e in all_estimates if e.annual_cost > 0)
        total_savings = sum(abs(e.annual_cost) for e in all_estimates if e.annual_cost < 0)
        
        return {
            "estimates": all_estimates,
            "summary": {
                "monthly_cost": total_monthly,
                "annual_cost": total_annual,
                "potential_savings": total_savings,
                "net_annual_cost": total_annual - total_savings,
                "region": self.region.value,
                "currency": "USD"
            },
            "breakdown": self._create_breakdown(all_estimates)
        }
    
    def _create_breakdown(self, estimates: List[CostEstimate]) -> Dict:
        """Create cost breakdown by category"""
        categories = {}
        
        for est in estimates:
            if est.monthly_cost > 0:  # Exclude savings
                category = est.resource_type
                if category not in categories:
                    categories[category] = {
                        "monthly": 0,
                        "annual": 0,
                        "items": []
                    }
                
                categories[category]["monthly"] += est.monthly_cost
                categories[category]["annual"] += est.annual_cost
                categories[category]["items"].append(est.resource_name)
        
        return categories
