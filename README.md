# Azure Landing Zone Discovery Agent

An intelligent agent for analyzing customer artifacts and discovering Azure Landing Zone requirements.

## Prerequisites

Before starting, ensure you have the following installed:

1. **Python 3.10 or higher**
   - Download from [python.org](https://www.python.org/downloads/)
   - Verify: `python --version`

2. **Azure CLI**
   - Download from [Microsoft Docs](https://docs.microsoft.com/cli/azure/install-azure-cli)
   - Verify: `az --version`

3. **Git** (for cloning the repository)
   - Download from [git-scm.com](https://git-scm.com/)

4. **Azure Subscription**
   - You need access to an Azure subscription with permissions to create resources

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd greenfiled_agent
```

### 2. Create Python Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Mac/Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Azure Login

Login to your Azure account:

```bash
az login
```

Set your subscription (if you have multiple):
```bash
az account set --subscription "<subscription-id-or-name>"
```

### 5. Create Azure Resources

Run the setup script to create all required Azure resources:

**Windows (PowerShell):**
```powershell
.\scripts\setup-azure-resources.ps1
```

**Optional parameters:**
```powershell
.\scripts\setup-azure-resources.ps1 -Location "westus" -ResourceGroup "my-custom-rg"
```

This script will create:
- Azure OpenAI Service with GPT-4 deployment
- Azure Storage Account with blob container
- Azure AI Search service
- Azure Document Intelligence service
- Azure AI Vision service

**Note:** The script will output environment variables at the end. Save these for the next step!

### 6. Configure Environment Variables

Create a `.env` file in the project root directory:

```bash
# Copy from the template
cp .env.example .env
```

Edit the `.env` file with the values from the setup script output:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Azure Storage Configuration
AZURE_STORAGE_CONNECTION_STRING=your-connection-string
AZURE_STORAGE_CONTAINER_NAME=customer-artifacts

# Azure AI Search Configuration
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_API_KEY=your-search-key
AZURE_SEARCH_INDEX_NAME=customer-artifacts-index

# Azure Document Intelligence (Optional)
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-docintel.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_API_KEY=your-docintel-key
AZURE_DOCUMENT_INTELLIGENCE_ENABLED=true

# Azure AI Vision (Optional)
AZURE_VISION_ENDPOINT=https://your-vision.cognitiveservices.azure.com/
AZURE_VISION_API_KEY=your-vision-key
AZURE_VISION_ENABLED=true

# Agent Configuration (Optional)
LOG_LEVEL=INFO
MAX_TOKENS=4000
TEMPERATURE=0.7
```

### 7. Upload Sample Artifacts (Optional)

If you want to test with sample documents:

```powershell
.\scripts\upload-artifacts.ps1 -SourceFolder ".\sample-artifacts"
```

### 8. Verify Setup

Run the health check script:

```powershell
.\scripts\health-check.ps1
```

This will verify:
- Python environment is activated
- All required packages are installed
- Azure resources are accessible
- Environment variables are configured correctly

## Running the Agent

### Interactive Mode

```bash
python run_agent.py
```

Or use the PowerShell wrapper:
```powershell
.\run-agent.ps1
```

### Command Line Options

The agent provides an interactive CLI interface with the following features:
- Upload and process customer documents
- Analyze artifacts and extract requirements
- Generate compliance reports
- Export findings to various formats

## Project Structure

```
greenfiled_agent/
├── src/                      # Source code
│   ├── config.py             # Configuration management
│   ├── discovery_agent.py    # Main agent logic
│   ├── discovery_framework.py # Core framework
│   ├── discovery_workshop.py  # Interactive workshop
│   ├── document_processor.py  # Document processing
│   ├── search_client.py       # Azure AI Search client
│   ├── storage_client.py      # Azure Storage client
│   ├── vision_analyzer.py     # Image analysis
│   └── ...
├── scripts/                   # Utility scripts
│   ├── setup-azure-resources.ps1
│   ├── health-check.ps1
│   ├── upload-artifacts.ps1
│   └── cleanup.ps1
├── sample-artifacts/          # Sample documents for testing
├── test_documents/            # Test files
├── output/                    # Generated reports
├── requirements.txt           # Python dependencies
├── run_agent.py              # Main entry point
└── README.md                 # This file
```

## Troubleshooting

### Issue: Module not found errors
**Solution:** Ensure virtual environment is activated:
```powershell
.\venv\Scripts\Activate.ps1
```

### Issue: Azure authentication errors
**Solution:** 
1. Run `az login` to authenticate
2. Verify subscription: `az account show`
3. Check your credentials have necessary permissions

### Issue: Missing environment variables
**Solution:** 
1. Verify `.env` file exists in project root
2. Check all required variables are set
3. Run `.\scripts\health-check.ps1` to diagnose

### Issue: Azure OpenAI quota errors
**Solution:** 
- Check your Azure OpenAI quota in the Azure Portal
- You may need to request quota increase
- Try a different region if quota is exhausted

### Issue: Python package conflicts
**Solution:**
```bash
pip uninstall -r requirements.txt -y
pip install -r requirements.txt
```

## Cleanup

To remove all Azure resources when done:

```powershell
.\scripts\cleanup.ps1 -ResourceGroup "rg-landing-zone-agent"
```

**Warning:** This will permanently delete all resources!

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Azure Portal for resource status
3. Check application logs in the `output/` directory

## License

[Add your license information here]

## Contributors

[Add contributor information here]
