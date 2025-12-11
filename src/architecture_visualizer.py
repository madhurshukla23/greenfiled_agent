"""
Architecture Visualization Generator
Creates visual representations of Azure Landing Zone architecture
"""
import json
from typing import Dict, List, Optional
from pathlib import Path


class ArchitectureVisualizer:
    """Generates architecture diagrams from discovery data"""
    
    def __init__(self, discovery_data: Dict):
        self.data = discovery_data
        self.answers = {a['question_id']: a for a in discovery_data.get('answers', [])}
    
    def generate_mermaid_diagram(self) -> str:
        """Generate Mermaid diagram syntax"""
        diagram = ["graph TB"]
        diagram.append("    %% Azure Landing Zone Architecture")
        diagram.append("")
        
        # Add components based on answers
        components = self._identify_components()
        
        # Hub VNet
        if components.get('hub_vnet'):
            diagram.append("    subgraph Hub[\"Hub VNet\"]")
            diagram.append("        FW[Azure Firewall]")
            diagram.append("        GW[VPN/ExpressRoute Gateway]")
            diagram.append("    end")
            diagram.append("")
        
        # Spoke VNets
        spoke_count = components.get('spoke_count', 2)
        for i in range(1, spoke_count + 1):
            diagram.append(f"    subgraph Spoke{i}[\"Spoke VNet {i}\"]")
            diagram.append(f"        VM{i}[Virtual Machines]")
            diagram.append(f"        NSG{i}[Network Security Group]")
            diagram.append(f"    end")
            diagram.append("")
        
        # On-premises connection
        if components.get('hybrid_connectivity'):
            diagram.append("    OnPrem[On-Premises Network]")
            diagram.append("    OnPrem -->|ExpressRoute/VPN| GW")
            diagram.append("")
        
        # Hub-Spoke connections
        for i in range(1, spoke_count + 1):
            diagram.append(f"    Hub <-->|VNet Peering| Spoke{i}")
        
        # Management services
        if components.get('monitoring'):
            diagram.append("")
            diagram.append("    subgraph Management[\"Management & Monitoring\"]")
            diagram.append("        LAW[Log Analytics Workspace]")
            diagram.append("        Defender[Defender for Cloud]")
            diagram.append("        Backup[Azure Backup]")
            diagram.append("    end")
        
        # Styling
        diagram.append("")
        diagram.append("    classDef azure fill:#0078D4,stroke:#0078D4,color:#fff")
        diagram.append("    classDef onprem fill:#FFB900,stroke:#FFB900,color:#000")
        diagram.append("    class Hub,Spoke1,Spoke2,Management azure")
        diagram.append("    class OnPrem onprem")
        
        return "\n".join(diagram)
    
    def generate_ascii_diagram(self) -> str:
        """Generate simple ASCII architecture diagram"""
        components = self._identify_components()
        
        lines = []
        lines.append("=" * 70)
        lines.append("Azure Landing Zone Architecture".center(70))
        lines.append("=" * 70)
        lines.append("")
        
        # On-premises
        if components.get('hybrid_connectivity'):
            connectivity = self.answers.get('net_003', {}).get('answer', 'VPN')
            lines.append("┌─────────────────────┐")
            lines.append("│  On-Premises        │")
            lines.append("│  Network            │")
            lines.append("└──────────┬──────────┘")
            lines.append(f"           │ {connectivity}")
            lines.append("           ▼")
        
        # Hub VNet
        hub_cidr = self.answers.get('net_001', {}).get('answer', '10.0.0.0/16')
        lines.append("┌─────────────────────────────────────────────────┐")
        lines.append(f"│  Hub VNet ({hub_cidr})                          │")
        lines.append("│  ┌──────────────┐    ┌──────────────┐          │")
        lines.append("│  │ Azure        │    │ VPN/ER       │          │")
        lines.append("│  │ Firewall     │    │ Gateway      │          │")
        lines.append("│  └──────────────┘    └──────────────┘          │")
        lines.append("└────────┬─────────────────────┬──────────────────┘")
        lines.append("         │                     │")
        lines.append("         │ VNet Peering        │ VNet Peering")
        lines.append("         ▼                     ▼")
        
        # Spoke VNets
        spoke_count = components.get('spoke_count', 2)
        spoke_lines = ["┌──────────────────┐"] * spoke_count
        spoke_lines2 = []
        for i in range(1, spoke_count + 1):
            spoke_lines2.append(f"│  Spoke VNet {i}    │")
        spoke_lines3 = ["│  - VMs           │"] * spoke_count
        spoke_lines4 = ["│  - NSGs          │"] * spoke_count
        spoke_lines5 = ["└──────────────────┘"] * spoke_count
        
        lines.append("  " + "     ".join(spoke_lines))
        lines.append("  " + "     ".join(spoke_lines2))
        lines.append("  " + "     ".join(spoke_lines3))
        lines.append("  " + "     ".join(spoke_lines4))
        lines.append("  " + "     ".join(spoke_lines5))
        
        # Management
        if components.get('monitoring'):
            lines.append("")
            lines.append("Management & Monitoring:")
            lines.append("  • Log Analytics Workspace")
            lines.append("  • Microsoft Defender for Cloud")
            lines.append("  • Azure Backup")
        
        lines.append("")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def generate_html_diagram(self, output_path: str) -> str:
        """Generate interactive HTML diagram"""
        mermaid_code = self.generate_mermaid_diagram()
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Azure Landing Zone Architecture</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #0078D4;
            border-bottom: 3px solid #0078D4;
            padding-bottom: 10px;
        }}
        .metadata {{
            background: #f8f8f8;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
        }}
        .metadata h3 {{
            margin-top: 0;
            color: #333;
        }}
        .mermaid {{
            background: white;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Azure Landing Zone Architecture</h1>
        
        <div class="metadata">
            <h3>Configuration Summary</h3>
            <ul>
                <li><strong>Hub VNet CIDR:</strong> {self.answers.get('net_001', {}).get('answer', 'Not specified')}</li>
                <li><strong>Connectivity:</strong> {self.answers.get('net_003', {}).get('answer', 'Not specified')}</li>
                <li><strong>Environment:</strong> {self.answers.get('gov_003', {}).get('answer', 'Not specified')}</li>
            </ul>
        </div>
        
        <div class="mermaid">
{mermaid_code}
        </div>
        
        <div class="metadata">
            <h3>Legend</h3>
            <p><strong>Blue:</strong> Azure Resources | <strong>Yellow:</strong> On-Premises</p>
            <p>This diagram is generated based on your discovery workshop answers.</p>
        </div>
    </div>
    
    <script>
        mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
    </script>
</body>
</html>
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return output_path
    
    def _identify_components(self) -> Dict:
        """Identify what components to include in diagram"""
        components = {
            'hub_vnet': True,  # Always have hub
            'spoke_count': 2,  # Default
            'hybrid_connectivity': False,
            'monitoring': False,
        }
        
        # Check for hybrid connectivity
        connectivity = self.answers.get('net_003', {}).get('answer', '').lower()
        if 'vpn' in connectivity or 'expressroute' in connectivity:
            components['hybrid_connectivity'] = True
        
        # Check for monitoring/management
        if any(qid.startswith('ops_') for qid in self.answers.keys()):
            components['monitoring'] = True
        
        # Estimate spoke count from answers
        # Look for environment separation
        env_answer = self.answers.get('gov_003', {}).get('answer', '').lower()
        if 'dev' in env_answer and 'test' in env_answer and 'prod' in env_answer:
            components['spoke_count'] = 3
        elif 'subscription' in env_answer:
            components['spoke_count'] = 3
        
        return components
    
    def save_all_formats(self, base_path: str = "."):
        """Save diagrams in all formats"""
        Path(base_path).mkdir(parents=True, exist_ok=True)
        
        outputs = {}
        
        # ASCII
        ascii_path = f"{base_path}/architecture_ascii.txt"
        with open(ascii_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_ascii_diagram())
        outputs['ascii'] = ascii_path
        
        # Mermaid
        mermaid_path = f"{base_path}/architecture_diagram.mmd"
        with open(mermaid_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_mermaid_diagram())
        outputs['mermaid'] = mermaid_path
        
        # HTML
        html_path = f"{base_path}/architecture_diagram.html"
        outputs['html'] = self.generate_html_diagram(html_path)
        
        return outputs
