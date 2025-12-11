# Azure Resource Setup Script for Landing Zone Orchestrator Agent
# This script creates all required Azure resources

param(
    [Parameter(Mandatory = $false)]
    [string]$Location = "eastus",
    
    [Parameter(Mandatory = $false)]
    [string]$ResourceGroup = "rg-landing-zone-agent",
    
    [Parameter(Mandatory = $false)]
    [switch]$SkipOpenAI
)

# Color output functions
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

Write-Success "=========================================="
Write-Success "Azure Landing Zone Agent - Resource Setup"
Write-Success "=========================================="

# Check if Azure CLI is installed
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Error "Azure CLI is not installed. Please install it from: https://docs.microsoft.com/cli/azure/install-azure-cli"
    exit 1
}

# Login check
Write-Info "`nChecking Azure login status..."
$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Warning "Not logged in to Azure. Please login..."
    az login
    $account = az account show | ConvertFrom-Json
}

Write-Success "Logged in as: $($account.user.name)"
Write-Success "Subscription: $($account.name) ($($account.id))"

# Generate unique names
$timestamp = Get-Date -Format "yyyyMMddHHmmss"
$random = Get-Random -Maximum 9999
$openaiName = "openai-lz-agent-$random"
$storageName = "stlzagent$random"
$searchName = "search-lz-agent-$random"
$docIntelName = "docintel-lz-agent-$random"
$visionName = "vision-lz-agent-$random"
$containerName = "customer-artifacts"

Write-Info "`nResource names:"
Write-Info "  Resource Group: $ResourceGroup"
Write-Info "  Location: $Location"
Write-Info "  OpenAI: $openaiName"
Write-Info "  Storage: $storageName"
Write-Info "  Search: $searchName"
Write-Info "  Document Intelligence: $docIntelName"
Write-Info "  AI Vision: $visionName"

# Create resource group
Write-Info "`n[1/5] Creating resource group..."
az group create `
    --name $ResourceGroup `
    --location $Location `
    --output none

if ($LASTEXITCODE -eq 0) {
    Write-Success "✓ Resource group created"
}
else {
    Write-Error "✗ Failed to create resource group"
    exit 1
}

# Create Azure OpenAI Service
if (-not $SkipOpenAI) {
    Write-Info "`n[2/5] Creating Azure OpenAI Service..."
    Write-Warning "Note: This may take 2-3 minutes..."
    
    az cognitiveservices account create `
        --name $openaiName `
        --resource-group $ResourceGroup `
        --location eastus `
        --kind OpenAI `
        --sku S0 `
        --custom-domain $openaiName `
        --output none
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "✓ Azure OpenAI created"
        
        Write-Info "  Deploying GPT-4 model..."
        az cognitiveservices account deployment create `
            --name $openaiName `
            --resource-group $ResourceGroup `
            --deployment-name gpt-4 `
            --model-name gpt-4 `
            --model-version "turbo-2024-04-09" `
            --model-format OpenAI `
            --sku-capacity 10 `
            --sku-name "Standard" `
            --output none
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "✓ GPT-4 model deployed"
        }
        else {
            Write-Warning "✗ Failed to deploy GPT-4, trying gpt-35-turbo instead..."
            az cognitiveservices account deployment create `
                --name $openaiName `
                --resource-group $ResourceGroup `
                --deployment-name gpt-4 `
                --model-name gpt-35-turbo `
                --model-version "0125" `
                --model-format OpenAI `
                --sku-capacity 10 `
                --sku-name "Standard" `
                --output none
            Write-Success "✓ GPT-3.5-Turbo model deployed instead"
        }
        
        # Get credentials
        $openaiEndpoint = az cognitiveservices account show `
            --name $openaiName `
            --resource-group $ResourceGroup `
            --query properties.endpoint `
            --output tsv
        
        $openaiKey = az cognitiveservices account keys list `
            --name $openaiName `
            --resource-group $ResourceGroup `
            --query key1 `
            --output tsv
    }
    else {
        Write-Error "✗ Failed to create Azure OpenAI"
        exit 1
    }
}
else {
    Write-Warning "`n[2/5] Skipping Azure OpenAI (--SkipOpenAI flag set)"
    Write-Warning "You'll need to configure OpenAI credentials manually in .env"
    $openaiEndpoint = "https://your-resource.openai.azure.com/"
    $openaiKey = "your-api-key-here"
}

# Create Storage Account
Write-Info "`n[3/7] Creating Azure Storage Account..."
az storage account create `
    --name $storageName `
    --resource-group $ResourceGroup `
    --location $Location `
    --sku Standard_LRS `
    --kind StorageV2 `
    --allow-blob-public-access false `
    --output none

if ($LASTEXITCODE -eq 0) {
    Write-Success "✓ Storage account created"
    
    # Get connection string
    $storageConnString = az storage account show-connection-string `
        --name $storageName `
        --resource-group $ResourceGroup `
        --query connectionString `
        --output tsv
    
    # Create blob container
    Write-Info "  Creating blob container..."
    az storage container create `
        --name $containerName `
        --connection-string $storageConnString `
        --output none
    
    Write-Success "✓ Blob container '$containerName' created"
}
else {
    Write-Error "✗ Failed to create storage account"
    exit 1
}

# Create AI Search Service
Write-Info "`n[4/7] Creating Azure AI Search Service..."
Write-Warning "Note: This may take 2-3 minutes..."

az search service create `
    --name $searchName `
    --resource-group $ResourceGroup `
    --location $Location `
    --sku basic `
    --output none

if ($LASTEXITCODE -eq 0) {
    Write-Success "✓ AI Search service created"
    
    # Get credentials
    $searchEndpoint = "https://$searchName.search.windows.net"
    $searchKey = az search admin-key show `
        --service-name $searchName `
        --resource-group $ResourceGroup `
        --query primaryKey `
        --output tsv
    
    # Create search index
    Write-Info "  Creating search index..."
    
    $indexSchema = @{
        name   = "artifacts-index"
        fields = @(
            @{ name = "id"; type = "Edm.String"; key = $true; searchable = $false }
            @{ name = "blob_name"; type = "Edm.String"; searchable = $true; filterable = $true }
            @{ name = "content"; type = "Edm.String"; searchable = $true; analyzer = "standard.lucene" }
            @{ name = "document_type"; type = "Edm.String"; filterable = $true; facetable = $true }
            @{ name = "keywords"; type = "Collection(Edm.String)"; searchable = $true; filterable = $true }
            @{ name = "last_modified"; type = "Edm.DateTimeOffset"; filterable = $true; sortable = $true }
        )
    } | ConvertTo-Json -Depth 10
    
    $headers = @{
        "Content-Type" = "application/json"
        "api-key"      = $searchKey
    }
    
    try {
        Invoke-RestMethod `
            -Uri "$searchEndpoint/indexes?api-version=2023-11-01" `
            -Method Post `
            -Headers $headers `
            -Body $indexSchema `
            -ErrorAction Stop | Out-Null
        Write-Success "✓ Search index 'artifacts-index' created"
    }
    catch {
        Write-Warning "✗ Failed to create search index (you can create it later manually)"
    }
}
else {
    Write-Error "✗ Failed to create AI Search service"
    exit 1
}

# Create Azure Document Intelligence Service
Write-Info "`n[5/7] Creating Azure Document Intelligence Service..."

az cognitiveservices account create `
    --name $docIntelName `
    --resource-group $ResourceGroup `
    --location $Location `
    --kind FormRecognizer `
    --sku S0 `
    --custom-domain $docIntelName `
    --output none

if ($LASTEXITCODE -eq 0) {
    Write-Success "✓ Document Intelligence service created"
    
    # Get credentials
    $docIntelEndpoint = az cognitiveservices account show `
        --name $docIntelName `
        --resource-group $ResourceGroup `
        --query properties.endpoint `
        --output tsv
    
    $docIntelKey = az cognitiveservices account keys list `
        --name $docIntelName `
        --resource-group $ResourceGroup `
        --query key1 `
        --output tsv
}
else {
    Write-Warning "✗ Failed to create Document Intelligence (optional - will use fallback processors)"
    $docIntelEndpoint = ""
    $docIntelKey = ""
}

# Create Azure AI Vision Service
Write-Info "`n[6/7] Creating Azure AI Vision Service..."

az cognitiveservices account create `
    --name $visionName `
    --resource-group $ResourceGroup `
    --location $Location `
    --kind ComputerVision `
    --sku S1 `
    --custom-domain $visionName `
    --output none

if ($LASTEXITCODE -eq 0) {
    Write-Success "✓ AI Vision service created"
    
    # Get credentials
    $visionEndpoint = az cognitiveservices account show `
        --name $visionName `
        --resource-group $ResourceGroup `
        --query properties.endpoint `
        --output tsv
    
    $visionKey = az cognitiveservices account keys list `
        --name $visionName `
        --resource-group $ResourceGroup `
        --query key1 `
        --output tsv
}
else {
    Write-Warning "✗ Failed to create AI Vision (optional - will skip image OCR)"
    $visionEndpoint = ""
    $visionKey = ""
}

# Create .env file
Write-Info "`n[7/7] Creating .env configuration file..."

$envContent = @"
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=$openaiEndpoint
AZURE_OPENAI_API_KEY=$openaiKey
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Azure Storage Configuration
AZURE_STORAGE_CONNECTION_STRING=$storageConnString
AZURE_STORAGE_CONTAINER_NAME=$containerName

# Azure AI Search Configuration
AZURE_SEARCH_ENDPOINT=$searchEndpoint
AZURE_SEARCH_API_KEY=$searchKey
AZURE_SEARCH_INDEX_NAME=artifacts-index

# Azure Document Intelligence Configuration (Optional - Enhanced document processing)
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=$docIntelEndpoint
AZURE_DOCUMENT_INTELLIGENCE_API_KEY=$docIntelKey
AZURE_DOCUMENT_INTELLIGENCE_ENABLED=true

# Azure AI Vision Configuration (Optional - Image OCR and analysis)
AZURE_VISION_ENDPOINT=$visionEndpoint
AZURE_VISION_API_KEY=$visionKey
AZURE_VISION_ENABLED=true

# Agent Configuration
LOG_LEVEL=INFO
MAX_TOKENS=4000
TEMPERATURE=0.7
"@

$envPath = Join-Path $PSScriptRoot ".env"
$envContent | Out-File -FilePath $envPath -Encoding utf8 -Force

Write-Success "✓ .env file created at: $envPath"

# Summary
Write-Success "`n=========================================="
Write-Success "Setup Complete!"
Write-Success "=========================================="
Write-Info "`nResource Summary:"
Write-Info "  Resource Group: $ResourceGroup"
Write-Info "  Location: $Location"
Write-Info "  OpenAI Service: $openaiName"
Write-Info "  Storage Account: $storageName"
Write-Info "  Search Service: $searchName"
Write-Info "  Document Intelligence: $docIntelName"
Write-Info "  AI Vision: $visionName"
Write-Info "  Blob Container: $containerName"

Write-Info "`nConfiguration saved to: $envPath"

Write-Success "`nNext Steps:"
Write-Info "  1. Upload customer artifacts to blob storage:"
Write-Info "     az storage blob upload --container-name $containerName --name 'your-file.pdf' --file 'path/to/file.pdf' --connection-string '<connection-string>'"
Write-Info ""
Write-Info "  2. Install Python dependencies:"
Write-Info "     pip install -r requirements.txt"
Write-Info ""
Write-Info "  3. Run the orchestrator agent:"
Write-Info "     python -m src.main"

Write-Success "`n=========================================="

# Cost information
Write-Warning "`nEstimated Monthly Costs (minimal usage):"
Write-Warning "  - Azure OpenAI: Pay-as-you-go (~$0.03/1K tokens)"
Write-Warning "  - Storage Account: ~$0.02/GB"
Write-Warning "  - AI Search (Basic): ~$75/month"
Write-Warning "  - Document Intelligence (S0): ~$1.50/1K pages"
Write-Warning "  - AI Vision (S1): ~$1.00/1K images"
Write-Warning "  Total: ~$75-100/month + usage-based AI services"
Write-Warning "`nNote: Document Intelligence and AI Vision are optional"
Write-Warning "      and only used when processing specific document types"
