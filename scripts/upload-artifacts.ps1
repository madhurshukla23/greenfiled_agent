# Script to upload sample artifacts to Azure Blob Storage
# This helps you test the Orchestrator Agent with sample data

param(
    [Parameter(Mandatory = $false)]
    [string]$ArtifactsFolder = ".\sample-artifacts",
    
    [Parameter(Mandatory = $false)]
    [string]$ContainerName = "customer-artifacts"
)

function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Error { Write-Host $args -ForegroundColor Red }

Write-Success "=========================================="
Write-Success "Upload Artifacts to Azure Blob Storage"
Write-Success "=========================================="

# Load .env file
$envFile = Join-Path $PSScriptRoot ".." ".env"
if (-not (Test-Path $envFile)) {
    Write-Error ".env file not found. Please run setup-azure-resources.ps1 first"
    exit 1
}

Write-Info "`nLoading configuration from .env..."
$connectionString = $null
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^AZURE_STORAGE_CONNECTION_STRING=(.+)$') {
        $connectionString = $matches[1]
    }
}

if (-not $connectionString) {
    Write-Error "AZURE_STORAGE_CONNECTION_STRING not found in .env file"
    exit 1
}

Write-Success "✓ Configuration loaded"

# Check if artifacts folder exists
if (-not (Test-Path $ArtifactsFolder)) {
    Write-Info "`nArtifacts folder not found. Creating sample folder..."
    New-Item -ItemType Directory -Path $ArtifactsFolder -Force | Out-Null
    
    # Create sample files
    $sampleRequirements = @"
Azure Landing Zone Requirements - Contoso Corporation

Project Overview:
Contoso Corporation needs to establish a secure, compliant Azure Landing Zone for their enterprise workloads.

Network Requirements:
- Hub-spoke network topology
- 3 virtual networks: Hub (10.0.0.0/16), Prod (10.1.0.0/16), Dev (10.2.0.0/16)
- VPN Gateway for on-premises connectivity (500 Mbps)
- Azure Firewall in hub network
- Network Security Groups on all subnets
- Private DNS zones for Azure services

Security Requirements:
- All data must be encrypted at rest and in transit
- Multi-factor authentication required for all users
- Privileged Identity Management for admin access
- Azure Key Vault for secrets management
- Azure Defender enabled on all subscriptions

Governance Requirements:
- Separate subscriptions for Production and Development
- Resource naming convention: {environment}-{resource-type}-{workload}-{region}-{instance}
- Required tags: Environment, Owner, CostCenter, Project
- Azure Policy for compliance enforcement
- Management groups: Root > Contoso > [Production, Development]

Compliance Requirements:
- HIPAA compliance required
- Data residency: All data must remain in US East region
- Audit logs retention: 365 days
- Regular compliance reporting

Monitoring Requirements:
- Centralized Log Analytics workspace
- Azure Monitor for all resources
- Application Insights for applications
- Alerts for critical resource metrics
- Monthly security reports
"@
    
    $sampleRequirements | Out-File -FilePath "$ArtifactsFolder\requirements.txt" -Encoding utf8
    
    $sampleNotes = @"
Whiteboard Session Notes - December 2025

Attendees: John Smith (CTO), Sarah Johnson (Security Lead), Mike Chen (Network Architect)

Key Discussion Points:

1. Network Architecture
   - Decided on hub-spoke topology for better isolation
   - Hub VNet will host shared services (firewall, VPN gateway, DNS)
   - Spoke VNets for production and development workloads
   - Consider Azure Virtual WAN for future multi-region expansion

2. Security Posture
   - Zero trust approach
   - No public endpoints for databases and storage
   - Private endpoints for all PaaS services
   - Network traffic must go through firewall for inspection
   - Consider Azure Bastion for VM access (no public IPs)

3. Identity and Access
   - Azure AD as primary identity provider
   - Federate with on-premises AD
   - Conditional access policies
   - Break-glass accounts for emergency access

4. Backup and DR
   - RPO: 4 hours
   - RTO: 8 hours for critical workloads
   - Azure Backup for VMs
   - Geo-redundant storage for critical data
   - Secondary region: US West 2

5. Cost Management
   - Budget alerts at 80% and 90% of monthly allocation
   - Reserved instances for predictable workloads
   - Auto-shutdown for dev/test VMs
   - Monthly cost reviews

Open Questions:
- Do we need ExpressRoute or is VPN sufficient? (Follow up with network team)
- What's the exact list of workloads for migration? (Waiting for app team)
- Disaster recovery region preference? (Check with business stakeholders)
"@
    
    $sampleNotes | Out-File -FilePath "$ArtifactsFolder\whiteboard-notes.txt" -Encoding utf8
    
    $complianceDoc = @"
Compliance and Regulatory Requirements

Organization: Contoso Healthcare Solutions
Document Date: December 2025

REGULATORY FRAMEWORK:
- HIPAA (Health Insurance Portability and Accountability Act)
- HITECH (Health Information Technology for Economic and Clinical Health)
- SOC 2 Type II
- ISO 27001

DATA CLASSIFICATION:
1. Protected Health Information (PHI) - Highest sensitivity
   - Patient records, medical histories
   - Must be encrypted, access logged
   - Geographic restrictions: US only
   
2. Confidential - High sensitivity
   - Employee data, financial records
   - Encryption required
   
3. Internal - Medium sensitivity
   - Corporate communications
   - Standard security controls

SPECIFIC REQUIREMENTS:
1. Encryption
   - Data at rest: AES-256 minimum
   - Data in transit: TLS 1.2 or higher
   - Key management: Azure Key Vault with HSM

2. Access Control
   - Least privilege access
   - Regular access reviews (quarterly)
   - MFA for all administrative access
   - Activity logging for PHI access

3. Audit and Logging
   - Comprehensive audit trails
   - Log retention: 7 years for PHI
   - Tamper-proof logging
   - Real-time security monitoring

4. Incident Response
   - Breach notification within 72 hours
   - Incident response plan documented
   - Regular tabletop exercises

5. Business Continuity
   - Backup frequency: Daily
   - Backup retention: 30 days + yearly archives
   - DR testing: Quarterly
   - RTO/RPO documented and approved

GEOGRAPHIC RESTRICTIONS:
- All PHI must be stored in US regions only
- Approved regions: East US, West US 2, Central US
- No data replication outside US

VENDOR MANAGEMENT:
- All cloud providers must be HIPAA compliant
- Business Associate Agreement (BAA) required
- Regular security assessments
"@
    
    $complianceDoc | Out-File -FilePath "$ArtifactsFolder\compliance-requirements.txt" -Encoding utf8
    
    Write-Success "✓ Created sample artifacts in: $ArtifactsFolder"
    Write-Info "  - requirements.txt"
    Write-Info "  - whiteboard-notes.txt"
    Write-Info "  - compliance-requirements.txt"
}

# Upload all files
Write-Info "`nUploading artifacts to blob storage..."

$files = Get-ChildItem -Path $ArtifactsFolder -File
$uploadCount = 0

foreach ($file in $files) {
    Write-Info "  Uploading: $($file.Name)..."
    
    az storage blob upload `
        --container-name $ContainerName `
        --name $file.Name `
        --file $file.FullName `
        --connection-string $connectionString `
        --overwrite `
        --output none
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "  ✓ $($file.Name) uploaded"
        $uploadCount++
    }
    else {
        Write-Error "  ✗ Failed to upload $($file.Name)"
    }
}

Write-Success "`n=========================================="
Write-Success "Upload Complete!"
Write-Success "=========================================="
Write-Info "Uploaded $uploadCount file(s) to container: $ContainerName"

Write-Info "`nNext Steps:"
Write-Info "  1. Index the uploaded artifacts (create indexing script)"
Write-Info "  2. Run the orchestrator agent:"
Write-Info "     python -m src.main"
