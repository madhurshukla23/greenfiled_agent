# Quick Start Guide

This guide will get you up and running in 15 minutes!

## ⚡ Quick Setup (15 minutes)

### Step 1: Prerequisites (5 min)
Install these if you don't have them:
- [ ] [Python 3.10+](https://www.python.org/downloads/)
- [ ] [Azure CLI](https://docs.microsoft.com/cli/azure/install-azure-cli)
- [ ] [Git](https://git-scm.com/)
- [ ] Azure subscription with contributor access

### Step 2: Setup (5 min)

```powershell
# 1. Clone and navigate
git clone <repo-url>
cd greenfiled_agent

# 2. Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Login to Azure
az login
```

### Step 3: Create Azure Resources (5 min)

```powershell
# Run the automated setup script
.\scripts\setup-azure-resources.ps1

# This creates:
# ✓ Azure OpenAI with GPT-4
# ✓ Storage Account
# ✓ AI Search
# ✓ Document Intelligence
# ✓ AI Vision
```

**Important:** The script will display environment variables at the end. Copy them!

### Step 4: Configure Environment

```powershell
# 1. Copy template
cp .env.example .env

# 2. Edit .env with values from setup script
notepad .env
```

Paste the values from the setup script output into your `.env` file.

### Step 5: Verify & Run

```powershell
# Verify everything is working
.\scripts\health-check.ps1

# Run the agent
python run_agent.py
```

## 🎯 First Run

When you run the agent for the first time:

1. You'll see an interactive menu
2. Choose "Upload Artifacts" to add documents
3. The agent will process and analyze them
4. Generate reports and insights

## 📝 Daily Usage

```powershell
# Activate environment
.\venv\Scripts\Activate.ps1

# Run agent
python run_agent.py

# Or use the wrapper
.\run-agent.ps1
```

## 🐛 Common Issues

**"Module not found"** → Activate venv: `.\venv\Scripts\Activate.ps1`

**"Azure auth failed"** → Run: `az login`

**"Missing .env variables"** → Run: `.\scripts\health-check.ps1`

**"OpenAI quota error"** → Check Azure Portal quota, may need increase

## 🧹 Cleanup

When done testing:
```powershell
.\scripts\cleanup.ps1 -ResourceGroup "rg-landing-zone-agent"
```

## 📚 Need More Help?

See [README.md](README.md) for detailed documentation.

## ✅ Checklist for Your Colleague

- [ ] Python 3.10+ installed
- [ ] Azure CLI installed
- [ ] Git cloned the repository
- [ ] Virtual environment created and activated
- [ ] Dependencies installed from requirements.txt
- [ ] Logged into Azure CLI
- [ ] Ran setup-azure-resources.ps1 successfully
- [ ] Created .env file with correct values
- [ ] Ran health-check.ps1 successfully
- [ ] Successfully ran the agent

---

**Estimated Total Time:** 15-20 minutes (excluding Azure resource deployment wait times)
