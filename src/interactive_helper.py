"""
Interactive Help System for Discovery Workshop
Provides commands and information during the workshop
"""
from typing import Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich import box

from src.discovery_framework import (
    DISCOVERY_QUESTIONS,
    DiscoveryCategory,
    InformationPriority,
    get_questions_by_category,
    get_critical_questions
)
from src.validators import AzureValidator

console = Console()


class InteractiveHelper:
    """Interactive help system for workshop"""
    
    COMMANDS = {
        'help': 'Show all available commands',
        'list': 'List all discovery questions',
        'list-critical': 'List only critical questions',
        'list-category': 'List questions by category',
        'naming': 'Show Azure naming conventions',
        'ip-ranges': 'Show IP address range best practices',
        'regions': 'Show Azure regions information',
        'compliance': 'Show compliance frameworks',
        'costs': 'Show cost optimization tips',
        'progress': 'Show current progress',
        'answered': 'Show all answered questions',
        'missing': 'Show missing/unanswered questions',
        'examples': 'Show examples for current question',
        'skip': 'Skip current question',
        'quit': 'Exit workshop',
    }
    
    def __init__(self, agent=None):
        self.agent = agent
    
    def show_help(self):
        """Display help menu with all commands"""
        console.print("\n[bold cyan]Available Commands[/bold cyan]")
        console.print("[dim]Type any command during a question prompt[/dim]\n")
        
        table = Table(box=box.SIMPLE)
        table.add_column("Command", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        
        for cmd, desc in self.COMMANDS.items():
            table.add_row(f"?{cmd}", desc)
        
        console.print(table)
        console.print("\n[dim]Example: Type '?list' to see all questions[/dim]\n")
    
    def list_all_questions(self):
        """List all discovery questions"""
        console.print("\n[bold cyan]All Discovery Questions[/bold cyan]")
        console.print(f"[dim]Total: {len(DISCOVERY_QUESTIONS)} questions across {len(DiscoveryCategory)} categories[/dim]\n")
        
        for category in DiscoveryCategory:
            questions = get_questions_by_category(category)
            console.print(f"\n[bold]{category.value}[/bold] ({len(questions)} questions)")
            
            for q in questions:
                priority_color = {
                    InformationPriority.CRITICAL: "red",
                    InformationPriority.HIGH: "yellow",
                    InformationPriority.MEDIUM: "cyan",
                    InformationPriority.LOW: "white"
                }[q.priority]
                
                status = ""
                if self.agent and self.agent.session:
                    if q.id in self.agent.session.answers:
                        status = " [green]✓[/green]"
                
                console.print(f"  [{priority_color}]{q.priority.value.upper()}[/{priority_color}] {q.question}{status}")
        
        console.print()
    
    def list_critical_questions(self):
        """List only critical priority questions"""
        console.print("\n[bold red]Critical Questions[/bold red]")
        critical = get_critical_questions()
        console.print(f"[dim]Total: {len(critical)} critical questions[/dim]\n")
        
        for i, q in enumerate(critical, 1):
            status = ""
            if self.agent and self.agent.session:
                if q.id in self.agent.session.answers:
                    status = " [green]✓ Answered[/green]"
                else:
                    status = " [red]✗ Missing[/red]"
            
            console.print(f"{i}. {q.question}{status}")
            if q.help_text:
                console.print(f"   [dim]{q.help_text}[/dim]")
        
        console.print()
    
    def list_by_category(self, category_name: Optional[str] = None):
        """List questions by specific category"""
        if not category_name:
            console.print("\n[bold cyan]Categories:[/bold cyan]\n")
            for i, cat in enumerate(DiscoveryCategory, 1):
                console.print(f"{i}. {cat.value}")
            console.print("\n[dim]Usage: ?list-category <number>[/dim]\n")
            return
        
        try:
            idx = int(category_name) - 1
            categories = list(DiscoveryCategory)
            if 0 <= idx < len(categories):
                category = categories[idx]
                questions = get_questions_by_category(category)
                
                console.print(f"\n[bold]{category.value}[/bold] ({len(questions)} questions)\n")
                
                for q in questions:
                    status = ""
                    if self.agent and self.agent.session:
                        if q.id in self.agent.session.answers:
                            status = " [green]✓[/green]"
                    
                    priority_color = {
                        InformationPriority.CRITICAL: "red",
                        InformationPriority.HIGH: "yellow",
                        InformationPriority.MEDIUM: "cyan",
                        InformationPriority.LOW: "white"
                    }[q.priority]
                    
                    console.print(f"[{priority_color}]{q.priority.value.upper()}[/{priority_color}] {q.question}{status}")
                    if q.help_text:
                        console.print(f"  [dim]{q.help_text}[/dim]")
                    console.print()
            else:
                console.print("[red]Invalid category number[/red]")
        except ValueError:
            console.print("[red]Invalid category number[/red]")
    
    def show_naming_conventions(self):
        """Display Azure naming conventions"""
        naming_guide = """
# Azure Naming Conventions

## General Rules
- Use lowercase letters, numbers, and hyphens
- Keep names between 3-63 characters
- Start with a letter
- Avoid special characters except hyphens
- Be descriptive and consistent

## Recommended Prefixes

| Resource Type | Prefix | Example |
|---------------|--------|---------|
| Virtual Network | `vnet-` | `vnet-hub-prod-001` |
| Subnet | `snet-` | `snet-web-prod-001` |
| Network Security Group | `nsg-` | `nsg-web-prod-001` |
| Virtual Machine | `vm-` | `vm-web-prod-001` |
| Storage Account | `st` | `stwebprod001` (no hyphens) |
| Key Vault | `kv-` | `kv-secrets-prod-001` |
| Application Gateway | `agw-` | `agw-web-prod-001` |
| Load Balancer | `lb-` | `lb-web-prod-001` |
| Public IP | `pip-` | `pip-web-prod-001` |
| Azure Firewall | `afw-` | `afw-hub-prod-001` |
| Log Analytics | `log-` | `log-workspace-prod-001` |
| Resource Group | `rg-` | `rg-networking-prod-001` |

## Naming Pattern
```
<prefix>-<workload>-<environment>-<region>-<instance>
```

**Example:** `vnet-hub-prod-eastus-001`
- `vnet-` = Resource type
- `hub` = Workload/purpose
- `prod` = Environment
- `eastus` = Azure region
- `001` = Instance number

## Environment Abbreviations
- `dev` - Development
- `test` - Testing
- `uat` - User Acceptance Testing
- `stg` - Staging
- `prod` - Production

## Region Abbreviations
- `eus` - East US
- `wus` - West US
- `neu` - North Europe
- `weu` - West Europe
- `sea` - Southeast Asia
"""
        console.print(Panel(Markdown(naming_guide), title="Azure Naming Conventions", border_style="cyan"))
    
    def show_ip_ranges(self):
        """Display IP range best practices"""
        ip_guide = """
# Azure IP Address Ranges Best Practices

## Private IP Ranges (RFC 1918)
- `10.0.0.0/8` - Largest range (16.7M addresses)
- `172.16.0.0/12` - Medium range (1M addresses)
- `192.168.0.0/16` - Small range (65K addresses)

## Recommended VNet Sizes
- **Hub VNet:** /16 (65,536 addresses)
- **Spoke VNets:** /16 to /20 (4,096-65,536 addresses)
- **Subnets:** /24 to /27 (16-256 addresses)

## Azure Reserved Addresses
Azure reserves **5 IP addresses** in each subnet:
- `.0` - Network address
- `.1` - Default gateway
- `.2, .3` - Azure DNS
- `.255` - Broadcast address

**Example:** In 10.0.1.0/24 (256 addresses), only 251 are usable.

## Common Subnet Allocations

| Subnet Type | Size | Usable IPs | Example CIDR |
|-------------|------|------------|--------------|
| Gateway Subnet | /27 | 27 | 10.0.0.0/27 |
| Azure Firewall | /26 | 59 | 10.0.0.64/26 |
| Azure Bastion | /26 | 59 | 10.0.0.128/26 |
| Application Gateway | /24 | 251 | 10.0.1.0/24 |
| Web Tier | /24 | 251 | 10.0.2.0/24 |
| App Tier | /24 | 251 | 10.0.3.0/24 |
| Database Tier | /25 | 123 | 10.0.4.0/25 |

## Hub-Spoke IP Design Example
```
Hub VNet:              10.0.0.0/16
├─ GatewaySubnet:      10.0.0.0/27
├─ AzureFirewallSubnet: 10.0.0.64/26
└─ Shared Services:    10.0.1.0/24

Spoke 1 (Prod):        10.1.0.0/16
├─ Web Tier:           10.1.1.0/24
├─ App Tier:           10.1.2.0/24
└─ Data Tier:          10.1.3.0/24

Spoke 2 (Dev):         10.2.0.0/16
└─ General:            10.2.1.0/24
```

## Tips
✓ Use /16 for VNets to allow growth
✓ Use /24 for most subnets (good balance)
✓ Avoid overlapping with on-premises networks
✓ Leave gaps for future expansion
✗ Don't use /29 or smaller (too few IPs)
"""
        console.print(Panel(Markdown(ip_guide), title="IP Address Ranges", border_style="cyan"))
    
    def show_regions(self):
        """Display Azure regions information"""
        regions_guide = """
# Azure Regions

## US Regions
- **East US** - Virginia (Primary)
- **East US 2** - Virginia (Secondary)
- **Central US** - Iowa
- **North Central US** - Illinois
- **South Central US** - Texas
- **West US** - California
- **West US 2** - Washington
- **West US 3** - Arizona

## Europe Regions
- **North Europe** - Ireland
- **West Europe** - Netherlands
- **UK South** - London
- **UK West** - Cardiff
- **France Central** - Paris
- **Germany West Central** - Frankfurt
- **Switzerland North** - Zurich

## Asia Pacific Regions
- **Southeast Asia** - Singapore
- **East Asia** - Hong Kong
- **Japan East** - Tokyo
- **Japan West** - Osaka
- **Australia East** - New South Wales
- **Australia Southeast** - Victoria

## Region Pairs (for DR)
- East US ↔ West US
- East US 2 ↔ Central US
- North Europe ↔ West Europe
- Southeast Asia ↔ East Asia

## Considerations
✓ Choose regions close to users (lower latency)
✓ Check compliance requirements (data sovereignty)
✓ Use region pairs for disaster recovery
✓ Verify service availability in selected regions
✓ Consider pricing differences between regions
"""
        console.print(Panel(Markdown(regions_guide), title="Azure Regions", border_style="cyan"))
    
    def show_compliance(self):
        """Display compliance frameworks"""
        compliance_guide = """
# Compliance Frameworks

## Common Frameworks

### HIPAA (Health Insurance Portability and Accountability Act)
- **Applies to:** Healthcare organizations, health plans
- **Requirements:** PHI protection, encryption, access controls
- **Azure Services:** HIPAA-compliant configurations available

### PCI-DSS (Payment Card Industry Data Security Standard)
- **Applies to:** Organizations handling credit card data
- **Requirements:** Network security, encryption, monitoring
- **Levels:** 1-4 based on transaction volume

### SOC 2 Type II
- **Applies to:** Service providers, SaaS companies
- **Requirements:** Security, availability, confidentiality
- **Focus:** Trust services criteria

### ISO 27001
- **Applies to:** All organizations
- **Requirements:** Information security management
- **Certification:** Internationally recognized standard

### GDPR (General Data Protection Regulation)
- **Applies to:** EU data processing
- **Requirements:** Data privacy, consent, right to deletion
- **Penalties:** Up to 4% of global revenue

### FedRAMP (Federal Risk and Authorization Management Program)
- **Applies to:** US government cloud services
- **Levels:** Low, Moderate, High
- **Requirements:** Extensive security controls

## Azure Compliance Tools
- **Microsoft Purview Compliance Manager**
- **Azure Policy** - Enforce compliance rules
- **Azure Blueprints** - Compliant templates
- **Compliance Score** - Track compliance posture

## Best Practices
✓ Identify applicable frameworks early
✓ Use Azure Policy for enforcement
✓ Enable audit logging and monitoring
✓ Implement encryption (at-rest and in-transit)
✓ Regular compliance assessments
✓ Document compliance controls
"""
        console.print(Panel(Markdown(compliance_guide), title="Compliance Frameworks", border_style="cyan"))
    
    def show_cost_tips(self):
        """Display cost optimization tips"""
        cost_guide = """
# Azure Cost Optimization Tips

## Compute Savings
✓ **Reserved Instances** - Save 30-40% with 1-3 year commitment
✓ **Azure Hybrid Benefit** - Use existing Windows/SQL licenses
✓ **Spot VMs** - Save up to 90% for interruptible workloads
✓ **Auto-shutdown** - Stop VMs during non-business hours
✓ **Right-sizing** - Match VM size to actual needs

## Storage Optimization
✓ **Access Tiers** - Use Cool/Archive for infrequent data
✓ **Lifecycle Management** - Auto-move aging data to cheaper tiers
✓ **Storage Reservations** - Save 38% with 1-3 year commitment
✓ **Managed Disks** - Choose appropriate disk type (Standard vs Premium)

## Networking Costs
✓ **Azure ExpressRoute** - Lower egress costs vs VPN
✓ **CDN** - Cache content closer to users
✓ **VNet Peering** - Lower cost than VPN Gateway within region
⚠ **Data Egress** - Most expensive (outbound data transfer)

## Monitoring & Management
✓ **Azure Advisor** - Get personalized cost recommendations
✓ **Cost Management + Billing** - Set budgets and alerts
✓ **Log Analytics** - Set data retention limits (default: 30 days)
✓ **Tags** - Track costs by project/department

## General Strategies
1. **Start Small** - Begin with minimal resources, scale up
2. **Use Dev/Test Pricing** - Lower rates for non-production
3. **Delete Unused Resources** - Remove orphaned disks, NICs, IPs
4. **Monitor Regularly** - Review costs weekly
5. **Set Budget Alerts** - Get notified at 50%, 80%, 100%

## Cost Breakdown (Typical Landing Zone)

| Category | Monthly | Annual | Optimization |
|----------|---------|--------|--------------|
| Networking | $1,000 | $12,000 | ExpressRoute vs VPN |
| Compute | $700 | $8,400 | Reserved Instances |
| Storage | $200 | $2,400 | Access tiers |
| Monitoring | $400 | $4,800 | Retention limits |
| **Total** | **$2,300** | **$27,600** | |
| **With RI** | **$2,000** | **$24,000** | **Save $3,600** |
"""
        console.print(Panel(Markdown(cost_guide), title="Cost Optimization", border_style="cyan"))
    
    def show_answered(self):
        """Show all answered questions"""
        if not self.agent or not self.agent.session:
            console.print("[yellow]No active session[/yellow]")
            return
        
        if not self.agent.session.answers:
            console.print("[yellow]No answers recorded yet[/yellow]")
            return
        
        console.print(f"\n[bold green]Answered Questions[/bold green] ({len(self.agent.session.answers)})\n")
        
        for qid, answer in self.agent.session.answers.items():
            question = DISCOVERY_QUESTIONS.get(qid)
            if question:
                console.print(f"[bold]{question.question}[/bold]")
                console.print(f"Answer: [cyan]{answer.answer}[/cyan]")
                console.print(f"Source: [dim]{answer.source} | Confidence: {answer.confidence:.0%}[/dim]\n")
    
    def show_missing(self):
        """Show missing/unanswered questions"""
        if not self.agent:
            console.print("[yellow]No active session[/yellow]")
            return
        
        missing = self.agent.get_missing_information()
        critical_missing = [q for q in missing if q.priority == InformationPriority.CRITICAL]
        other_missing = [q for q in missing if q.priority != InformationPriority.CRITICAL]
        
        console.print(f"\n[bold yellow]Missing Information[/bold yellow] ({len(missing)} questions)\n")
        
        if critical_missing:
            console.print(f"[bold red]Critical ({len(critical_missing)})[/bold red]\n")
            for q in critical_missing:
                console.print(f"• {q.question}")
            console.print()
        
        if other_missing:
            console.print(f"[bold]Other ({len(other_missing)})[/bold]\n")
            for q in other_missing[:10]:  # Show first 10
                console.print(f"• [{q.priority.value}] {q.question}")
            if len(other_missing) > 10:
                console.print(f"[dim]... and {len(other_missing) - 10} more[/dim]")
    
    def process_command(self, command: str) -> bool:
        """Process interactive command. Returns True if command was handled."""
        if not command.startswith('?'):
            return False
        
        # Remove '?' and parse
        cmd_parts = command[1:].strip().split(maxsplit=1)
        cmd = cmd_parts[0].lower()
        args = cmd_parts[1] if len(cmd_parts) > 1 else None
        
        if cmd == 'help':
            self.show_help()
        elif cmd == 'list':
            self.list_all_questions()
        elif cmd == 'list-critical':
            self.list_critical_questions()
        elif cmd == 'list-category':
            self.list_by_category(args)
        elif cmd == 'naming':
            self.show_naming_conventions()
        elif cmd == 'ip-ranges':
            self.show_ip_ranges()
        elif cmd == 'regions':
            self.show_regions()
        elif cmd == 'compliance':
            self.show_compliance()
        elif cmd == 'costs':
            self.show_cost_tips()
        elif cmd == 'answered':
            self.show_answered()
        elif cmd == 'missing':
            self.show_missing()
        elif cmd == 'progress':
            if self.agent:
                from src.discovery_workshop import DiscoveryWorkshopCLI
                # Show progress inline
                cli = DiscoveryWorkshopCLI()
                cli.agent = self.agent
                cli.show_discovery_progress()
        else:
            console.print(f"[red]Unknown command: {cmd}[/red]")
            console.print("[dim]Type '?help' for available commands[/dim]")
        
        return True
