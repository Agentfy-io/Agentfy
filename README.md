# 🚀 Agentfy Developer Documentation

## 📋 Overview

Agentfy is a modular microservices architecture designed to process user requests and execute workflows across multiple social media platforms. The system leverages LLM capabilities to dynamically match user needs with appropriate agents and functions.

## 🚦 Development Getting Started

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create or Update `agent_registry.json` file with available agents and functions (Optional)
   - Example:
     ```json
     {
       "agents": [
         {
           "name": "agent_name",
           "description": "Agent description",
           "functions": [
             {
               "name": "function_name",
               "description": "Function description"
             }
           ]
         }
       ]
     }
     ```
4. Set environment variables or update `config.py`
5. Run the API: `uvicorn main:app --reload` or `python main.py` or `python3 main.py`

## ➕ If You Need to Add New Sub Agents....

1. Create a new directory under `agents/` for the platform
2. Implement agent functions in appropriate files (crawler, analysis, interactive)
3. Add agent definitions to the agent registry JSON
4. The system will automatically incorporate these into workflows when appropriate


## 🏗️ System Architecture

```
Agentfy/
├── core/                       # Core system components
│   ├── perception/             # Input validation & output formatting
│   ├── memory/                 # Data persistence & retrieval
│   ├── reasoning/              # Request analysis & workflow planning
│   ├── action/                 # Workflow execution
│   ├── monitoring/             # Execution monitoring (optional)
│   └── communication/          # Inter-agent communication (optional)
├── common/                     # Shared utilities 
│   ├── ais/                    # ai utilities, e.g., wrapper class for ChatGPT, Claude, DeepSeek
│   ├── models/                 # models for data structures, design for communication between modules, e.g., messages, workflows, users
│   ├── security/               # Security utilities
│   ├── utils/                  # Common utilities  
│   └── exceptions/             # Custom exceptions
├── agents/                     # Platform-specific agents
│   ├── tiktok/                 # TikTok agents
│   ├── twitter/                # Twitter agents
│   └── ...                     # Other platform agents
├── config.py                   # Configuration management 
├── agents_registry.json        # Agent registry for available agents and functions
├── requirements.txt            # Python dependencies
├── README.md                   # Documentation
└── main.py                     # Main entry point for Agentfy, for testing and development
```

## 🧩 Core Modules

### 👁️ Perception Module

> The Perception Module handles input validation and output formatting. It ensures that user requests are properly formatted and validated before being processed by the system.

**Key Files**:
- `module.py`: Main module functionality
- `validators.py`: Input validation utilities (optional)
- `formatters.py`: formatting outputs before sending them to the frontend (optional), e.g., JSON formatting, HTML sanitization.

### 🤔 Reasoning Module

> The Reasoning Module leverages ChatGPT to analyze user requests and determine the appropriate agents and steps needed to fulfill them. It passes the user request and agent registry to ChatGPT and receives a structured workflow in response.

**Key Files**:
- `module.py`: Main module functionality

### ⚙️ Action Module

> The Action Module takes the workflow output from the Reasoning Module and executes each step in sequence, finding and calling the appropriate agent functions.

**Key Files**:
- `module.py`: Main module functionality (simplified execution engine)

## 🔧 Common Components

### 📊 Models

**Purpose**: Define data structures used throughout the system.

**Key Files**:
- `messages.py`: Message-related models, like message receives from users, messages sent to users, etc. (mostly for perception module)
- `workflows.py`: Workflow-related models, like workflow definitions, execution results, etc. (mostly for reasoning and action modules)
- `agents.py`: SubAgent-related models (used in action module and future communication module)

### ⚠️ Exceptions

**Purpose**: Define custom exceptions for error handling.

**Key Files**:
- `exceptions.py`: Custom exception hierarchy, including `AgentNotFound`, `WorkflowError`, etc.

### 🛠️ Utils

**Purpose**: Shared utility functions.

**Key Files**:
- `logging.py`: Structured logging
- `helpers.py`: Common helper functions, e.g., date formatting, string manipulation

### 🔒 Security

**Purpose**: Security-related utilities.

**Key Files**:
- `validators.py`: Security validation utilities
- `sanitizers.py`: Input sanitization utilities

## 🤖 Agents

Each social media platform has its own set of agents divided into categories:

1. **Crawlers**: Data collection from social platforms
2. **Analysis**: Data processing and insights generation
3. **Interactive**: Actions that interact with social platforms

## 🌐 FastAPI Integration

The `main.py` file integrates all modules into a cohesive API with these endpoints:

- `/process`: Process user requests and build workflows
- `/workflow/{id}/status`: Check workflow status
- `/workflow/parameters`: Update missing parameters and execute workflows
- `/workflow/{id}/result`: Retrieve workflow results
- `/workflow/{id}/cancel`: Cancel a workflow
