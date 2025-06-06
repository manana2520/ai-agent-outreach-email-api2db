# AI Agent Platform

<div align="center">

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.11-009688.svg)](https://fastapi.tiangolo.com/)
[![CrewAI](https://img.shields.io/badge/CrewAI-0.108.0-ff69b4.svg)](https://github.com/joaomdmoura/crewAI)

**A self-contained deployment solution for AI agents built with frameworks like CrewAI**

</div>

## 🌟 Overview

The AI Agent Platform is designed to provide a comprehensive solution for deploying, managing, and interacting with AI agents. It addresses the needs of both developers and non-developers, offering a user-friendly web interface alongside powerful API capabilities.

<details>
<summary>🔍 Why AI Agent Platform?</summary>

AI agents are becoming increasingly powerful, but deploying and managing them in production environments remains challenging. The AI Agent Platform solves this by providing:

- **Simplified Deployment**: Deploy AI agents with minimal configuration
- **Framework Agnostic**: Support for multiple AI agent frameworks
- **Production-Ready**: Built with scalability and reliability in mind
- **Developer & Non-Developer Friendly**: Both API and UI interfaces
- **Asynchronous Execution**: Run long-running agent tasks without blocking
- **Stateful Run Management**: Track and manage run status across executions

</details>

## ✨ Key Features

- **Framework Agnostic**: Initially supports CrewAI, with extensibility for other AI agent frameworks
- **Multiple LLM Providers**: Supports OpenRouter, Anthropic, Azure OpenAI, and OpenAI, with easy configuration
- **Self-Contained Deployment**: Can be run locally or deployed to any Kubernetes cluster
- **Flexible Code Deployment**: Support for GitHub repositories, file uploads (ZIP archives), and direct code input
- **Web UI**: For code upload, configuration, and interaction with agents
- **API Gateway**: RESTful API for programmatic interaction
- **Run Management**: Asynchronous execution with status tracking
- **Human-in-the-Loop (HITL)**: Support for approval workflows and feedback incorporation
- **Webhook Notifications**: Get notified when runs complete or require human input

## 🏗️ Repository Structure

This repository is organized as a monorepo containing multiple components:

```
agentic-runtime/                        # Repository root
├── src/                                # Main Python package source code
│   └── ai_agent_platform/              # Main package
│       ├── common/                     # Shared utilities
│       │   ├── config/                 # Configuration settings
│       │   ├── files/                  # File handling utilities
│       │   ├── git/                    # Git repository management
│       │   ├── logging/                # Logging utilities
│       │   └── webhook/                # Webhook notification utilities
│       ├── management/                 # Management API service
│       └── runtime/                    # Runtime API service
│           └── core/                   # Core runtime functionality
│               └── run/                # Run management 
├── frontend/                           # TypeScript/JavaScript frontend
│   ├── src/                            # Frontend source code
│   ├── public/                         # Static assets
│   └── package.json                    # Frontend dependencies
├── kubernetes/                         # Kubernetes resources
│   ├── management/                     # Management API K8s resources
│   ├── operator/                       # K8s Operator code and resources
│   │   ├── charts/                     # Helm charts
│   │   ├── crds/                       # Custom Resource Definitions
│   │   ├── examples/                   # Example CR manifests
│   │   └── src/                        # Operator source code
│   └── runtime/                        # Runtime API K8s resources
├── docker/                             # Docker-related files
│   ├── frontend/                       # Frontend Docker configuration
│   ├── management/                     # Management API Docker configuration
│   ├── operator/                       # Operator Docker configuration
│   └── runtime/                        # Runtime API Docker configuration
├── examples/                           # Example agent implementations
├── tests/                              # Test suite
├── docs/                               # Documentation
├── scripts/                            # Utility scripts
│   ├── bin/                            # Executable scripts
│   ├── tools/                          # Testing tools
│   └── examples/                       # Example scripts
├── pyproject.toml                      # Python package configuration
└── .env.example                        # Example environment variables
```

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- `uv` (recommended for package management)
- A local Kubernetes cluster (e.g., Rancher Desktop, Minikube) with `kubectl` configured.
- `nerdctl` (if using Rancher Desktop) or `docker`
- `helm` (for deploying the operator)

### Local Development Setup

1. **Clone the repository**

    ```bash
    git clone https://github.com/yourusername/ai-agent-platform.git
    cd ai-agent-platform
    ```

2. **Install dependencies**

    ```bash
    uv pip install -e ".[dev]"
    ```

3. **Set up environment variables**

    ```bash
    cp .env.example .env
    # Edit .env with your settings (e.g., API_AUTH_TOKEN)
    ```

4. **Deploy Kubernetes Operator**
    - Ensure your local Kubernetes cluster is running.
    - Install the CRDs:

      ```bash
      kubectl apply -f kubernetes/operator/crds/
      ```

    - Deploy the Operator **and Management API** using the main Helm chart:

      ```bash
      # Ensure you are in the root directory or adjust the path
      helm upgrade --install ai-agent-platform ./kubernetes/helm/ai-agent-platform --namespace default --create-namespace
      ```

    - Verify the operator and management API pods are running:

      ```bash
      kubectl get pods -n default -l app.kubernetes.io/instance=ai-agent-platform
      ```

5. **Run the Management API Locally (Alternative for Development)**
    If you prefer to run the Management API directly for easier debugging (instead of using the one deployed by Helm):

    ```bash
    # Ensure the Helm-deployed Management API is scaled down or deleted if necessary to avoid conflicts
    # Activate virtual env if needed: source .venv/bin/activate
    export $(grep -v '^#' .env | xargs)
    # Make sure KUBECONFIG points to your local cluster if not default
    uvicorn ai_agent_platform.management.main:app --reload --port 8000
    ```

    The Management API will be accessible at `http://localhost:8000`.

6. **Test the Setup**
    - Create a sample `AIAgentRuntime` CR (see `kubernetes/operator/examples/`).

      ```bash
      kubectl apply -f kubernetes/operator/examples/sample-runtime-git.yaml
      ```

    - Verify the Runtime API pod is created and running:

      ```bash
      kubectl get pods -n default -l app=sample-runtime-git
      ```

    - You can now interact with the Management API (e.g., list runtimes) and the Runtime API (once its service is exposed or port-forwarded).

### Docker Deployment (Alternative)

While local Kubernetes is the primary development method, you can still build and run individual components using Docker for testing purposes. *Note: This does not include the Kubernetes Operator interaction.*

1. **Build the Docker image(s)** (Example for Management API)

    ```bash
    # Using Docker
    docker build -t ai-agent-platform-management:latest -f docker/management/Dockerfile .

    # Using Rancher Desktop with nerdctl
    nerdctl build -t ai-agent-platform-management:latest -f docker/management/Dockerfile .
    ```

2. **Run the Docker container(s)** (Example for Management API)

    ```bash
    # Using Docker
    docker run -d -p 8000:8000 --name ai-agent-management \
      -e API_AUTH_TOKEN=your-auth-token \
      --env-file .env \
      ai-agent-platform-management:latest

    # Using Rancher Desktop with nerdctl
    nerdctl run -d -p 8000:8000 --name ai-agent-management \
      -e API_AUTH_TOKEN=your-auth-token \
      --env-file .env \
      ai-agent-platform-management:latest
    ```

3. **Test the API**

    ```bash
    # Check if the API is running (won't list K8s-managed runtimes in this mode)
    curl -X GET "http://localhost:8000/api/runtimes" \
      -H "Authorization: Bearer ${API_AUTH_TOKEN}"
    ```

## 🔐 Authentication

The AI Agent Platform uses a unified authentication system that applies to both the Management API and Runtime APIs:

### Authentication Configuration

By default, authentication is enabled for all APIs except health check endpoints. The authentication system uses a simple token-based approach:

1. **Environment Variables**:
   - `API_AUTH_ENABLED`: Controls whether authentication is required (default: `true`)
   - `API_AUTH_TOKEN`: The token that must be provided with API requests

2. **Helm Chart Configuration**:

   ```yaml
   # API Authentication (applies to both Management API and Runtime API)
   auth:
     # Enable authentication for all APIs
     enabled: true
     # Token configuration
     token:
       # Use an existing secret instead of creating one
       existingSecret: ""
       # Secret key to use for the token
       secretKey: "api-token"
       # Set a fixed API token value (recommended for production)
       value: ""
       # Secret name to create if not using existingSecret
       secretName: "ai-agent-platform-api-auth"
   ```

### Making Authenticated Requests

To make requests to any platform API (Management or Runtime), include the token in the Authorization header:

```bash
curl -H "Authorization: Bearer YOUR_AUTH_TOKEN" https://api-url/endpoint
```

Replace `YOUR_AUTH_TOKEN` with your configured authentication token.

### Disabling Authentication

For development or testing, you can disable authentication by setting `API_AUTH_ENABLED=false` as an environment variable or `auth.enabled: false` in your Helm values.

### Endpoints Exempt from Authentication

The following endpoints remain accessible without authentication:

- `GET /health`: Health check endpoint for both Management API and Runtime APIs

All other endpoints require authentication when it is enabled.

### Kubernetes Deployment

The AI Agent Platform can be deployed to Kubernetes using the provided manifests:

1. **Create a namespace**

   ```bash
   kubectl create namespace ai-platform
   ```

2. **Create a secret for API authentication**

   ```bash
   kubectl create secret generic api-auth \
     --from-literal=API_AUTH_TOKEN=your-auth-token \
     -n ai-platform
   ```

3. **Deploy the platform**

   ```bash
   # Apply the deployment manifest
   kubectl apply -f kubernetes/management/deployment.yaml -n ai-platform

   # Apply the service manifest
   kubectl apply -f kubernetes/management/service.yaml -n ai-platform
   ```

4. **Create an AI Agent Runtime**

   ```yaml
   # agent-runtime.yaml
   apiVersion: agentic.keboola.io/v1alpha1
   kind: AIAgentRuntime
   metadata:
     name: demo-agent
     namespace: ai-platform
   spec:
     entrypoint: "crewai_app/main.py"
     codeSource:
       type: git
       gitRepo:
         url: "https://github.com/username/my-crewai-project"
         branch: "main"
     envVars:
       - name: OPENAI_API_KEY
         value: "sk-..."
     replicas: 1
   ```

   ```bash
   kubectl apply -f agent-runtime.yaml
   ```

5. **Access the API**

   ```bash
   # Port forward the service
   kubectl port-forward svc/ai-agent-platform-management 8080:80 -n ai-platform

   # Test the API
   curl -X GET "http://localhost:8080/api/runtimes" \
     -H "Authorization: Bearer ${API_AUTH_TOKEN}"
   ```

## 📖 Documentation

For detailed documentation, see the [docs](docs/) directory:

- [Documentation Hub](docs/README.md): Central documentation hub with links to all documentation
- [Architecture](docs/development/architecture.md): Comprehensive system architecture including design, components, deployment options and project structure
- [API Documentation](docs/api_wrapper_documentation.md): Detailed API reference
- [Docker Guide](docs/docker-guide.md): Comprehensive Docker setup and build process
- [Testing Guide](docs/testing_guide.md): How to test the platform
- [Packaging Guide](docs/packaging.md): How to build and distribute the package
- [CI/CD Guide](docs/ci_cd.md): Continuous integration and deployment

### Architecture Documentation

- [Architecture](docs/development/architecture.md): Comprehensive system architecture including design, components, deployment options and project structure
- [Implementation Plan](docs/architecture/implementation_plan.md): Development roadmap
- [User Workflow](docs/architecture/user_workflow.md): End-to-end user experience

## 🔍 API Endpoints

The platform provides a comprehensive RESTful API for interacting with AI agents:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check endpoint |
| `/kickoff` | POST | Start a new agent run |
| `/runs` | GET | List all runs with filtering options |
| `/runs/{run_id}` | GET | Get run status and results |
| `/runs/{run_id}/input` | POST | Provide feedback/input for HITL workflows |
| `/list-crews` | GET | List available crews |
| `/refresh-git-repo` | POST | Refresh the Git repository |
| `/agent/validate` | GET | Validate agent code |
| `/agent/metadata` | GET | Get agent metadata |

<details>
<summary>Example API Usage</summary>

```bash
# Start a new run
curl -X POST "http://localhost:8000/kickoff" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -d '{
    "crew": "newsletter",
    "inputs": {
      "topic": "AI trends in 2025"
    },
    "webhook_url": "https://your-webhook-endpoint.com/webhook" // Optional: For notifications
  }'

# List all runs
curl "http://localhost:8000/runs?limit=5&status=COMPLETED" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN"

# Check specific run status
curl "http://localhost:8000/runs/YOUR_RUN_ID" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN"

# Provide input/feedback (HITL)
# To approve/resume:
curl -X POST "http://localhost:8000/runs/YOUR_RUN_ID/input" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -d '{
    "approve": true
  }'

# To provide feedback (task restarts):
curl -X POST "http://localhost:8000/runs/YOUR_RUN_ID/input" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -d '{
    "approve": false,
    "feedback": "Please make it more concise"
  }'
```

</details>

## 🔄 Human-in-the-Loop (HITL) Workflow

The platform supports CrewAI's standard Human-in-the-Loop (HITL) functionality, allowing for human interaction during agent execution:

1. **Enable HITL**: Configure a task in your CrewAI agent with `human_input=True`.
2. **Start a Run**: Kick off a run using the `/kickoff` endpoint, providing a `webhook_url` if you want notifications.
3. **Task Pause & Notification**: When the agent executes the HITL-enabled task and calls `input()`, the run pauses with status `PENDING_HUMAN_INPUT`. A webhook is sent to your specified URL.
4. **Review Context**: Check the run status (`GET /runs/{run_id}`) to see the context, including the prompt provided by the agent (`hitl_context.prompt`).
5. **Provide Input/Feedback**: Call `POST /runs/{run_id}/input`:
    - To approve/resume without changes, send `{"approve": true}`.
    - To provide feedback for CrewAI to incorporate (triggering a task restart), send `{"approve": false, "feedback": "Your specific feedback..."}`.
6. **Execution Continues**: The agent resumes processing, eventually reaching `COMPLETED` or `ERROR` status.

This workflow enables interactive agent processes guided by human judgment.

## 🧩 Components

### Backend API

The backend API is built with FastAPI and provides endpoints for interacting with AI agents. It handles run management, agent execution, and webhook notifications.

### Framework Adapters

The platform includes adapters for different AI agent frameworks, starting with CrewAI. These adapters provide a common interface for executing agents and managing their lifecycle.

### Storage Implementations

Multiple storage backends are supported for run data, including in-memory storage (for development) and PostgreSQL (for production).

### Frontend (Coming Soon)

A web UI for interacting with AI agents, viewing run status, and managing configurations.

### Kubernetes Operator

A Kubernetes operator built with Kopf for declaratively managing AI agents in Kubernetes clusters. The operator handles the entire lifecycle of AI Agent Runtimes, including:

- Creation of necessary Kubernetes resources (Deployments, Services)
- Management of code sources (Git repositories)
- Automatic secret handling for LLM provider credentials
- Health monitoring and status reporting

For more information, see the [Kubernetes Operator Documentation](kubernetes/operator/README.md).

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the [Apache License 2.0](LICENSE).

# AI Agent Platform Management API Update

This update modernizes the Management API component of the AI Agent Platform with the following improvements:

## Technology Updates

- **Python 3.12**: Updated all components to use Python 3.12
- **UV Package Manager**: Replaced pip with UV for faster, more reliable package management
- **Latest Dependencies**: Updated all dependencies to their latest versions:
  - FastAPI 0.115.8
  - Uvicorn 0.34.0
  - Pydantic 2.10.6
  - Kubernetes 32.0.1
  - pytest 8.3.4
  - httpx 0.28.1
  - python-dotenv 1.0.1

## Code Improvements

- **Pydantic v2 Compatibility**: Updated all models to be compatible with Pydantic v2
- **Consistent Terminology**: Aligned naming conventions with the rest of the platform
  - Renamed models from `Runtime*` to `AIAgentRuntime*` for clarity
  - Updated service class names to match the new terminology
  - Updated API documentation to reflect the new naming

## Kubernetes Deployment

- **Resource Naming**: Updated all Kubernetes resources to follow the `ai-agent-platform-*` naming convention
- **Labels**: Added consistent labels including `part-of: ai-agent-platform`
- **Documentation**: Updated deployment documentation to reflect the new resource names

## Documentation

- **API Documentation**: Updated to reflect the new model names and API endpoints
- **Implementation Plan**: Revised to include the latest technology stack and implementation phases

These changes ensure the Management API is up-to-date with modern Python practices and maintains consistency with the rest of the AI Agent Platform.

## Project Structure

```
ai-agent-platform/
├── src/
│   ├── management-api/         # Management API service
│   │   ├── api/                # API routes and controllers
│   │   ├── models/             # Pydantic models
│   │   ├── services/           # Business logic
│   │   └── utils/              # Utilities
│   └── operator/               # Kubernetes operator
├── kubernetes/                 # Kubernetes manifests
│   ├── operator/               # Operator-related manifests
│   │   ├── charts/             # Helm charts for operator
│   │   ├── crds/               # CRD definitions (deprecated)
│   │   └── CRD-SPECIFICATION.md # Technical specification for the CRD
├── examples/                   # Example agent implementations
├── docs/                       # Documentation
└── tests/                      # Tests
```

## Architecture

The platform follows a modern microservices architecture with these core components:

1. **Management API**: RESTful API for creating and managing AI Agent Runtimes
2. **Kubernetes Operator**: Kopf-based operator that watches for custom resources and manages lifecycle
   - True multi-tenant architecture with namespace isolation and per-tenant operator instances
   - Comprehensive reconciliation mechanisms for high reliability
   - Well-documented CRD specification and reference implementation
3. **Database**: PostgreSQL for storing metadata about deployments
4. **Storage Service**: For managing user code and configurations
5. **Web UI**: (Planned) React-based dashboard for visually managing agents

The system uses Custom Resource Definitions (CRDs) to represent AI Agent Runtimes in Kubernetes, with the Management API translating user-friendly requests into these CRs.

## Authentication

The AI Agent Platform implements token-based authentication for both Management API and Runtime API. Authentication is controlled globally through Helm values and can be enabled/disabled as needed.

### Configuration

Authentication settings are defined in the Helm chart's `values.yaml`:

```yaml
# API Authentication (applies to both Management API and Runtime API)
auth:
  # Enable authentication for all APIs
  enabled: true
  # Token configuration
  token:
    existingSecret: ""  # Use existing secret instead of creating one
    secretKey: "api-token"  # Key in the secret
    value: ""  # Fixed token value (if not specified, random token is generated)
    secretName: "ai-agent-platform-api-auth"  # Secret name to create
```

### Making Authenticated Requests

When authentication is enabled, all API endpoints (except health checks) require the authentication token in the Authorization header:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" https://your-api-url/endpoint
```

For local development, you can:

1. Set `API_AUTH_ENABLED=false` in your environment to disable authentication
2. Set `API_AUTH_TOKEN=your-token` to use a specific token value

See [Authentication Implementation](docs/reference/authentication-implementation.md) for more details.

> [!NOTE]
> The `url` field is always present in the runtime response. If ingress/domain is not configured, it will be `null`.
