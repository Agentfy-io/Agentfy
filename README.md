# 🚀 Agentfy Developer Documentation

## 📋 Overview

Agentfy is a modular microservices architecture designed to process user requests and execute workflows across multiple social media platforms. The system leverages LLM capabilities to dynamically match user needs with appropriate agents and functions.

## 🚦 Development Getting Started

# Installation and Setup

1. Clone the repository 
2. Install dependencies: `pip install -r requirements.txt`
3. Create or Update `agent_registry.json` file with available sub-agents and functions (Optional)
   - Example:
     ```json
     {
       "AGENT_REGISTRY": {
         "platform_name": {
           "crawlers": [
             {
               "agent_id": "agent_name",
               "function_id": "function_name",
               "description": "Function description",
               "parameters": [
                 {
                   "name": "para1_name",
                   "type": "para1_type",
                   "description": "para1 description",
                   "required": true
                 },
                 {
                   "name": "para2_type",
                   "type": "para2_type",
                   "description": "para2 description",
                   "required": false
                 }
               ],
               "returns": {
                 "type": "return_type",
                 "description": "Return value description"
               }
             }
           ]
         }
       }
     }
     ```
4. Set environment variables in `.env` file or update `config.py` (optional)
   - Required API keys and configurations can be found in `config.py`
   - Example `.env` file:
     ```
     OPENAI_API_KEY=your_key_here
     X_API_KEY=your_key_here
     X_API_SECRET=your_secret_here
     YOUTUBE_API_KEY=your_key_here
     ....
     ```

## Running the Program

You can interact with the program in three different ways:

### 1. Command Line Interface (CLI)
```bash
python run_agent_cli.py
```
- Runs the program in command-line interface mode
- Interactive mode for direct user input
- Useful for quick testing and debugging
- Simple text-based interface

### 2. FastAPI Web Interface (Currently Unavailable, Do not Use!)
```bash
python run_agent_api.py
```
- Runs the program as a FastAPI server
- Access the web interface at `http://localhost:8000`
- Available endpoints:
  - `/process`: Process user requests
  - `/workflow/{id}/status`: Check workflow status
  - `/workflow/parameters`: Update workflow parameters
  - `/workflow/{id}/result`: Get workflow results
  - `/workflow/{id}/cancel`: Cancel a workflow
- RESTful API for programmatic access

### 3. Streamlit Web Interface
```bash
streamlit run run_agent_app.py
```
- Runs the program with a Streamlit web interface
- Access the interface at `http://localhost:8501`
- User-friendly graphical interface
- Real-time updates and visual feedback
- Interactive widgets for parameter input

## Important Notes

1. Some interactive agents may require additional setup:
   - YouTube agents need OAuth2 authentication
   - Twitter agents need API keys and access tokens
   - Other platform-specific requirements may apply

2. If you encounter errors during execution:
   - Check your API keys and credentials
   - Verify the agent registry configuration
   - Ensure all required dependencies are installed
   - Check the logs in the `logs` directory for detailed error messages

3. The system is still in development, so some features may not be fully implemented or may change in future updates.

## 🏗️ System Architecture

```
Agentfy/
├── core/                    # Core system components
│   ├── perception/             # Input validation & output formatting (partially complete)
│   │   ├── module.py          # Main module for input validation and output formatting
│   │   ├── validators.py      # Input validation utilities (optional)
│   │   └── formatters.py      # Output formatting utilities (optional)
│   ├── memory/                 # Data persistence & retrieval (partially complete)
│   │   ├── module.py          # Main module for data persistence and retrieval
│   │   └── storage.py         # Data storage implementations
│   ├── reasoning/              # Request analysis & workflow planning (partially complete)
│   │   ├── module.py          # Main module for analyzing user input and generating workflows
│   │   └── workflow_generator.py # Workflow generation logic
│   ├── action/                 # Workflow execution (partially complete)
│   │   ├── module.py          # Main module for workflow execution
│   │   └── executor.py        # Workflow execution engine
│   ├── monitoring/             # Execution monitoring (Under Development, Not Available)
│   │   ├── module.py          # Main module for execution monitoring
│   │   └── metrics.py         # Performance tracking utilities
│   └── communication/          # Inter-agent communication (Under Development, Not Available)
│       ├── module.py          # Main module for inter-agent communication
│       └── message_bus.py     # Message passing system
├── common/                  # Shared utilities 
│   ├── ais/                    # AI utilities
│   │   ├── module.py          # Main module for AI service wrappers
│   │   ├── chatgpt.py         # ChatGPT API wrapper
│   │   ├── claude.py          # Claude API wrapper
│   │   └── deepseek.py        # DeepSeek API wrapper
│   ├── models/                 # Data structures and communication models
│   │   ├── messages.py        # Message-related models for user communication
│   │   ├── workflows.py       # Workflow-related models for execution
│   │   └── agents.py          # SubAgent-related models
│   ├── security/               # Security utilities
│   │   ├── validators.py      # Security validation utilities
│   │   └── sanitizers.py      # Input sanitization utilities
│   ├── utils/                  # Common utilities
│   │   ├── logging.py         # Structured logging utilities
│   │   └── helpers.py         # Common helper functions
│   └── exceptions/             # Custom exceptions
│       └── exceptions.py      # Custom exception hierarchy
├── agents/                  # Platform-specific agents
│   ├── tiktok/                 # TikTok agents
│   │   ├── crawlers.py        # TikTok data collection agents
│   │   ├── analysis.py        # TikTok data analysis agents
│   │   └── interactive.py     # TikTok interaction agents
│   ├── twitter/                # Twitter agents
│   │   ├── crawlers.py        # Twitter data collection agents
│   │   ├── analysis.py        # Twitter data analysis agents
│   │   └── interactive.py     # Twitter interaction agents
│   └── ...                     # Other platform agents
├── config.py                # Configuration management 
├── agents_registry.json     # Agent registry for available agents and functions
├── requirements.txt         # Python dependencies
├── README.md                # Documentation
├── run_agent_cli.py         # CLI interface entry point
├── run_agent_app.py         # Streamlit web interface entry point
└── run_agent_api.py         # FastAPI interface entry point (Under Development)

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

## ➕ If You Need to Add New Sub Agents....

1. Create a new directory under `agents/` for the platform
2. Implement agent functions in appropriate files (crawler, analysis, interactive)
3. Add agent definitions to the agent registry JSON
4. The system will automatically incorporate these into workflows when appropriate

