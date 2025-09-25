# Azure Container Apps Python Code Interpreter Sessions

This project demonstrates how to use **Azure Container Apps dynamic sessions** with Python code interpreter capabilities to create an AI-powered application that can execute Python code securely and return results in real-time.

## Overview

The application is a FastAPI-based web API that leverages **Azure Container Apps Python code interpreter sessions** to execute Python code dynamically. When users ask mathematical questions or request calculations, the application automatically detects the need for code execution and runs Python code in isolated, secure session pools. For general conversation, it uses Azure OpenAI for natural language responses.

## Features

- **Python Code Interpreter Sessions**: Primary feature using Azure Container Apps dynamic sessions for secure Python code execution
- **Intelligent Request Routing**: Automatically detects when Python code execution is needed vs. general conversation
- **Secure Isolated Execution**: Each code execution runs in a separate, secure container session
- **Azure OpenAI Integration**: Handles conversational AI and generates Python code when needed
- **FastAPI Web API**: Provides RESTful endpoints and interactive web interface
- **Session Management**: Tracks and manages multiple concurrent Python execution sessions

## Prerequisites

- Python 3.10 or later
- Azure subscription with access to:
  - **Azure Container Apps** (for Python session pools)
  - **Azure OpenAI Service** (for AI conversations and code generation)
- Azure CLI installed and configured
- [Azure Developer CLI (azd)](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd) installed
- Git

## Quick Start with Azure Developer CLI (azd)

The easiest way to deploy this application is using the Azure Developer CLI (azd):

### 1. Initialize and Deploy

```bash
# Clone the repository
git clone <your-repo-url>
cd aca-python-code-interpreter-session

# Login to Azure
azd auth login

# Initialize the project (first time only)
azd init

# Deploy to Azure (provisions resources and deploys the app)
azd up
```

The `azd up` command will:

- Create a new resource group
- **Deploy Azure Container Apps session pool** configured for Python code interpretation
- Deploy Azure OpenAI service with GPT-3.5 Turbo model
- Deploy the FastAPI application to Azure Container Apps
- Configure managed identity and permissions for secure session access

### 2. Access Your Application

After deployment, azd will provide you with:
- **Application URL**: Access your chat interface at `/ui`
- **API Documentation**: View API docs at `/docs`
- **Environment Details**: See resource details with `azd show`

### 3. Manage Your Deployment

```bash
# View deployment status and URLs
azd show

# Redeploy after code changes
azd deploy

# View logs
azd logs

# Clean up resources
azd down
```

## Local Development

### 1. Setup Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.sample` to `.env` and configure:

```env
AZURE_OPENAI_ENDPOINT=<your-azure-openai-endpoint>
POOL_MANAGEMENT_ENDPOINT=<your-session-pool-management-endpoint>
```

### 3. Run Locally

```bash
fastapi dev main.py
```

Access the application at:

- **Chat Interface**: <http://localhost:8000/ui>
- **API Documentation**: <http://localhost:8000/docs>

## How Python Session Pools Work

This application showcases **Azure Container Apps dynamic sessions** with Python code interpreter capabilities:

1. **Session Creation**: When code execution is needed, the app requests a new Python session from the session pool
2. **Code Execution**: Python code runs in an isolated, secure container environment
3. **State Persistence**: Variables and imports persist within the same session for follow-up questions
4. **Resource Management**: Sessions automatically scale up/down based on demand and have configurable timeouts
5. **Security**: Each user gets isolated execution environments with no cross-contamination

### Example Interaction Flow

```text
User: "What is 25 * 847?"
App: Detects math → Generates Python code → Executes in session pool
Session Pool: Runs "print(25 * 847)" → Returns "21175"
App: Returns formatted result to user

User: "What's the square root of that?"
App: Uses same session → Executes "import math; print(math.sqrt(21175))"
Session Pool: Returns "145.51..." (remembers previous calculation)
```

## Manual Azure Deployment (Alternative)

If you prefer manual deployment without azd, you can use Azure CLI:

### Create Azure Resources

```bash
# Set variables
RESOURCE_GROUP_NAME=aca-sessions-tutorial
AZURE_OPENAI_LOCATION=swedencentral
AZURE_OPENAI_NAME=<UNIQUE_OPEN_AI_NAME>
SESSION_POOL_LOCATION=eastasia
SESSION_POOL_NAME=code-interpreter-pool

# Create resource group
az group create --name $RESOURCE_GROUP_NAME --location $SESSION_POOL_LOCATION

# Create Azure OpenAI service
az cognitiveservices account create \
    --name $AZURE_OPENAI_NAME \
    --resource-group $RESOURCE_GROUP_NAME \
    --location $AZURE_OPENAI_LOCATION \
    --kind OpenAI \
    --sku s0 \
    --custom-domain $AZURE_OPENAI_NAME

# Deploy GPT-3.5 Turbo model
az cognitiveservices account deployment create \
    --resource-group $RESOURCE_GROUP_NAME \
    --name $AZURE_OPENAI_NAME \
    --deployment-name gpt-35-turbo \
    --model-name gpt-35-turbo \
    --model-version "1106" \
    --model-format OpenAI \
    --sku-capacity "100" \
    --sku-name "Standard"

# Create session pool
az containerapp sessionpool create \
    --name $SESSION_POOL_NAME \
    --resource-group $RESOURCE_GROUP_NAME \
    --location $SESSION_POOL_LOCATION \
    --max-sessions 100 \
    --container-type PythonLTS \
    --cooldown-period 300

# Deploy application
ENVIRONMENT_NAME=aca-sessions-tutorial-env
CONTAINER_APP_NAME=chat-api

az containerapp up \
    --name $CONTAINER_APP_NAME \
    --resource-group $RESOURCE_GROUP_NAME \
    --location $SESSION_POOL_LOCATION \
    --environment $ENVIRONMENT_NAME \
    --env-vars "AZURE_OPENAI_ENDPOINT=<OPEN_AI_ENDPOINT>" "POOL_MANAGEMENT_ENDPOINT=<SESSION_POOL_MANAGEMENT_ENDPOINT>" \
    --source .
```

**Note**: Configure managed identity and permissions as described in the [Azure Container Apps Sessions Tutorial](https://learn.microsoft.com/en-us/azure/container-apps/sessions-tutorial-semantic-kernel).

## API Usage

### Chat Endpoint

**GET** `/chat?message=<your-message>`

Example:

```bash
GET /chat?message=What time is it right now?
```

Response:

```json
{
  "output": "The current time is 2024-01-15 14:30:25 UTC"
}
```

### Interactive Web Interface

Visit `/ui` for a web-based chat interface that demonstrates Python code interpreter sessions:

- **Math and calculation questions** automatically trigger secure Python code execution in session pools
- **Code-related requests** are processed in isolated container sessions with persistent state
- **Regular conversation** gets AI responses without code execution
- **Session tracking** shows which responses used Python interpretation vs. conversational AI

## Key Components

### Azure Container Apps Python Session Pools

- **Primary feature**: Secure, isolated Python code execution environments
- **Dynamic scaling**: Sessions are created and destroyed based on demand
- **Persistent state**: Each session maintains Python variable state during the conversation
- **Security**: Complete isolation between different user sessions

### Intelligent Request Router

- Automatically detects when Python code execution is needed
- Routes mathematical and computational requests to session pools
- Handles conversational requests with Azure OpenAI directly
- Seamlessly combines both capabilities in a single interface

### Azure OpenAI Integration

- Generates Python code for mathematical and computational problems
- Provides conversational AI responses for general queries
- Uses Semantic Kernel framework for structured AI interactions

### Authentication & Security

- Uses Azure DefaultAzureCredential for secure service-to-service authentication
- Managed identity configuration for session pool access
- No hardcoded credentials or connection strings

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Ensure proper role assignments for Azure services
2. **Environment Variables**: Verify all required environment variables are set
3. **Python Version**: Use Python 3.10 or later for compatibility

### Required Azure Roles

- **Cognitive Services OpenAI User**: For Azure OpenAI access
- **Azure ContainerApps Session Executor**: For session pool access

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## References

- [Azure Container Apps Dynamic Sessions Overview](https://learn.microsoft.com/en-us/azure/container-apps/sessions)
- [Azure Container Apps Sessions with Python Tutorial](https://learn.microsoft.com/en-us/azure/container-apps/sessions-tutorial-semantic-kernel)
- [Azure Container Apps Sessions Code Interpreter](https://learn.microsoft.com/en-us/azure/container-apps/sessions-code-interpreter)
- [Azure Developer CLI Documentation](https://learn.microsoft.com/azure/developer/azure-developer-cli/)
- [Azure Container Apps Documentation](https://learn.microsoft.com/en-us/azure/container-apps/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
