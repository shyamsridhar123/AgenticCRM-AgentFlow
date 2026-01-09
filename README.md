# 🚀 Agentic CRM - AI-Powered Sales Intelligence

A full-stack CRM application powered by **AgentFlow** architecture for intelligent, multi-step reasoning capabilities.

![AgentFlow CRM](https://img.shields.io/badge/AgentFlow-Enabled-brightgreen) ![Python](https://img.shields.io/badge/Python-3.11+-blue) ![React](https://img.shields.io/badge/React-18-61dafb) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791)

## ✨ Features

- **🤖 AI Chat Interface** - Natural language queries against your CRM data
- **📊 Lead Scoring** - AI-powered lead prioritization
- **📧 Email Drafting** - Context-aware email generation
- **📅 Meeting Scheduling** - Smart scheduling suggestions
- **📈 Pipeline Forecasting** - Predictive deal analytics
- **🔍 Smart Search** - Semantic search across all entities

## 🧠 AgentFlow Architecture

This application uses the [AgentFlow](https://github.com/lupantech/AgentFlow) pattern for agentic reasoning with multi-step query processing.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AGENTFLOW QUERY PROCESSING                        │
└─────────────────────────────────────────────────────────────────────────┘

  User Query: "Show me all hot leads from this month"
         │
         ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │  1. PLANNER                                                           │
  │     • analyze_query() - Interprets user intent                        │
  │     • generate_sql() - Creates database query                         │
  │     Output: SELECT * FROM leads WHERE lead_rating = 'Hot'             │
  └──────────────────────────────────────────────────────────────────────┘
         │
         ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │  2. EXECUTOR                                                          │
  │     • execute_tool("crm_database_query", sql)                         │
  │     • Runs SQL against PostgreSQL                                     │
  │     Output: {success: true, results: [...], result_count: 15}         │
  └──────────────────────────────────────────────────────────────────────┘
         │
         ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │  3. MEMORY                                                            │
  │     • add_action(step, tool, goal, command, result)                   │
  │     • Tracks execution history for multi-step reasoning               │
  └──────────────────────────────────────────────────────────────────────┘
         │
         ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │  4. VERIFIER                                                          │
  │     • verificate_context() - Validates results                        │
  │     • Decision: STOP (query answered) or CONTINUE (more steps)        │
  └──────────────────────────────────────────────────────────────────────┘
         │
         ▼
    Response to User
```

### Core Components

| Component | Purpose | Location |
|-----------|---------|----------|
| **Planner** | Analyzes queries, decides tools, generates SQL | `backend/app/agentflow_crm.py` |
| **Executor** | Runs CRM database tool, captures results | `backend/app/agentflow_crm.py` |
| **Verifier** | Validates results, decides if more steps needed | `backend/app/agentflow_crm.py` |
| **Memory** | Tracks action history across reasoning steps | `backend/app/agentflow_crm.py` |
| **CRMDatabaseTool** | Executes SQL against PostgreSQL | `backend/agentflow_sdk/.../tools/crm_database/tool.py` |

### Two Integration Approaches

| Approach | Location | Use Case |
|----------|----------|----------|
| **Custom Implementation** | `backend/app/agentflow_crm.py` | Production CRM workflows (simplified, optimized) |
| **SDK-based** | `backend/test_agentflow.py` | Testing, advanced multi-tool scenarios |

## 🛠️ Tech Stack

**Backend:**
- Python 3.11+ with FastAPI
- Azure OpenAI (GPT-5.2/O1 models)
- PostgreSQL database
- AgentFlow SDK

**Frontend:**
- React 18 with TypeScript
- Vite build tool
- TanStack Query for data fetching
- Modern dark theme UI

## 📦 Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Azure OpenAI API access

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/Antigravity.git
cd Antigravity
```

### 2. Database Setup
```bash
# Create database
psql -U postgres -c "CREATE DATABASE crm_db;"

# Run schema
psql -U postgres -d crm_db -f database/init_schema.sql
```

### 3. Backend Setup
```bash
cd backend

# Create virtual environment (optional)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Azure OpenAI credentials
```

### 4. Frontend Setup
```bash
cd frontend
npm install
```

## ⚙️ Configuration

Create `backend/.env` with:
```env
# Azure OpenAI
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5.2-chat

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/crm_db

# App Settings
APP_HOST=0.0.0.0
APP_PORT=8000
APP_DEBUG=true
AGENTFLOW_VERBOSE=true
```

## 🚀 Running the Application

### Start Backend
```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Start Frontend
```bash
cd frontend
npm run dev
```

Access the application at **http://localhost:3000**

## 💬 Usage Examples

### AI Chat Queries
```
"Show me all leads with annual revenue over 1 million"
"What deals are closing this quarter?"
"Find contacts from technology companies"
"Which leads are rated as hot?"
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agent/query` | POST | Natural language query |
| `/api/agent/score-lead/{id}` | POST | Score a lead |
| `/api/agent/draft-email` | POST | Generate email |
| `/api/pipeline/forecast` | GET | Pipeline forecast |
| `/api/pipeline/health` | GET | Pipeline health score |

## 📁 Project Structure

```
Antigravity/
├── backend/
│   ├── app/
│   │   ├── agents/              # Specialized AI agents
│   │   │   ├── nl_query_agent.py    # Natural language processing
│   │   │   ├── lead_agent.py        # Lead scoring
│   │   │   ├── email_agent.py       # Email drafting
│   │   │   ├── meeting_agent.py     # Meeting scheduling
│   │   │   ├── pipeline_agent.py    # Pipeline forecasting
│   │   │   └── followup_agent.py    # Follow-up automation
│   │   ├── tools/               # CRM tools (database, ML, calendar)
│   │   ├── agentflow_crm.py     # ⭐ Main AgentFlow solver
│   │   ├── agentflow_setup.py   # SDK path configuration
│   │   ├── llm_engine.py        # Azure OpenAI integration
│   │   ├── database.py          # PostgreSQL connection
│   │   ├── config.py            # App configuration
│   │   └── main.py              # FastAPI application
│   ├── agentflow_sdk/           # AgentFlow SDK (vendored)
│   │   └── agentflow/
│   │       └── agentflow/
│   │           ├── solver.py        # Core solver orchestrator
│   │           ├── models/          # Planner, Executor, Verifier, Memory
│   │           ├── engine/          # LLM engines (Azure, OpenAI, Anthropic, etc.)
│   │           └── tools/           # Tool implementations
│   │               ├── base.py          # BaseTool abstract class
│   │               ├── crm_database/    # CRM database tool
│   │               ├── google_search/   # Web search tool
│   │               ├── python_coder/    # Code execution tool
│   │               └── wikipedia_search/
│   ├── test_agentflow.py        # AgentFlow integration tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   │   ├── ChatInterface.tsx    # AI chat UI
│   │   │   ├── Dashboard.tsx        # Main dashboard
│   │   │   ├── LeadsList.tsx        # Leads management
│   │   │   ├── PipelineView.tsx     # Pipeline visualization
│   │   │   └── Sidebar.tsx          # Navigation
│   │   ├── services/api.ts      # API client
│   │   └── styles/              # CSS styles
│   └── package.json
└── database/
    └── init_schema.sql          # PostgreSQL schema
```

## 📦 Dependency Analysis

### AgentFlow Integration

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DEPENDENCY FLOW                                    │
└─────────────────────────────────────────────────────────────────────────────┘

External Package:
    agentflow @ git+https://github.com/lupantech/AgentFlow.git
         │
         ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  AgentFlow SDK (backend/agentflow_sdk/)                                     │
│  ├── solver.py         → Core Solver orchestrator                           │
│  ├── models/           → Planner, Executor, Verifier, Memory                │
│  ├── engine/           → Azure OpenAI, OpenAI, Anthropic, vLLM, etc.        │
│  └── tools/            → BaseTool + CRM Database Tool                       │
└────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  CRM Application (backend/app/)                                             │
│  ├── agentflow_crm.py  → Custom AgentFlowSolver for CRM                     │
│  ├── llm_engine.py     → Azure OpenAI engine wrapper                        │
│  ├── main.py           → FastAPI (uses create_agentflow_solver)             │
│  └── agents/*.py       → Specialized agents using LLM engine                │
└────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  Frontend (frontend/)  → React UI with chat interface                       │
└────────────────────────────────────────────────────────────────────────────┘
```

### Key Dependencies

| Category | Packages |
|----------|----------|
| **AgentFlow** | `agentflow @ git+https://github.com/lupantech/AgentFlow.git` |
| **Azure OpenAI** | `openai>=1.0.0`, `azure-identity>=1.15.0` |
| **Web Framework** | `fastapi>=0.109.0`, `uvicorn[standard]>=0.27.0`, `pydantic>=2.5.0` |
| **Database** | `sqlalchemy>=2.0.25`, `psycopg2-binary>=2.9.9`, `asyncpg>=0.29.0` |
| **ML/Data** | `numpy>=1.26.0`, `pandas>=2.1.0`, `scikit-learn>=1.4.0` |
| **AgentFlow SDK Internal** | `graphviz`, `flask`, `agentops`, `litellm`, `langgraph`, `langchain` |

### LLM Engine Support

The AgentFlow SDK supports multiple LLM backends:

| Engine | File | Status |
|--------|------|--------|
| Azure OpenAI | `engine/azure_openai.py` | ✅ Primary (GPT-5.2) |
| OpenAI | `engine/openai.py` | ✅ Supported |
| Anthropic | `engine/anthropic.py` | ✅ Supported |
| vLLM | `engine/vllm.py` | ✅ Supported |
| Together | `engine/together.py` | ✅ Supported |
| DeepSeek | `engine/deepseek.py` | ✅ Supported |
| Gemini | `engine/gemini.py` | ✅ Supported |
| Ollama | `engine/ollama.py` | ✅ Supported |
| LiteLLM | `engine/litellm.py` | ✅ Supported |

## 🔧 AgentFlow Components

### AgentFlow Solver (Main Entry Point)

The solver is initialized at application startup in `main.py`:

```python
from app.agentflow_crm import create_agentflow_solver

# Initialize solver with Planner → Executor → Verifier pipeline
solver = create_agentflow_solver(max_steps=10, verbose=True)

# Process natural language query
result = solver.solve("How many hot leads do we have?")
# Returns: {
#     "success": True,
#     "query": "How many hot leads do we have?",
#     "generated_sql": "SELECT COUNT(*) FROM leads WHERE lead_rating = 'Hot';",
#     "result_count": 15,
#     "results": [...],
#     "agentflow": True,
#     "components_used": ["Planner", "Executor", "Verifier", "Memory"]
# }
```

### CRM Database Tool

The custom CRM tool extends AgentFlow's `BaseTool`:

```python
from agentflow.tools.base import BaseTool

class CRMDatabaseTool(BaseTool):
    """Execute SQL SELECT queries against the CRM database."""
    
    require_llm_engine = False
    
    def __init__(self):
        super().__init__(
            tool_name="crm_database_query",
            tool_description="Execute SQL queries against CRM database",
            input_types={"query": "str - A valid PostgreSQL SELECT query"},
            output_type="list[dict] - Query results"
        )
    
    def execute(self, query: str) -> dict:
        # Security: Only SELECT queries allowed
        if not query.strip().upper().startswith("SELECT"):
            return {"success": False, "error": "Only SELECT queries allowed"}
        
        results = execute_query(query, {})
        return {"success": True, "results": results}
```

### Custom Tool Development

Create new tools by extending the `BaseTool` pattern:

```python
class MyCustomTool(BaseTool):
    require_llm_engine = True  # Set True if tool needs LLM
    
    def __init__(self, model_string=None):
        super().__init__(
            tool_name="my_custom_tool",
            tool_description="Description of what the tool does",
            input_types={"param1": "str", "param2": "int"},
            output_type="dict",
            demo_commands=["my_custom_tool(param1='value', param2=10)"]
        )
        self.model_string = model_string
    
    def execute(self, param1: str, param2: int) -> dict:
        # Your tool logic here
        return {"success": True, "result": ...}
```

### Memory Tracking

Memory tracks all actions for multi-step reasoning:

```python
from app.agentflow_crm import Memory, ActionRecord

memory = Memory()
memory.add_action(
    step=1,
    tool_name="crm_database_query",
    sub_goal="Get lead count",
    command="SELECT COUNT(*) FROM leads",
    result={"count": 150}
)

# Get execution history
actions = memory.get_actions()
context = memory.get_context_summary()
```

### Using the SDK Solver Directly

For advanced use cases with multiple tools:

```python
from agentflow.solver import construct_solver

solver = construct_solver(
    llm_engine_name="gpt-4o",
    enabled_tools=["Base_Generator_Tool", "Python_Coder_Tool", "Google_Search_Tool"],
    output_types="final,direct",
    max_steps=10,
    verbose=True
)

result = solver.solve("What is the capital of France?")
```

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [AgentFlow](https://github.com/lupantech/AgentFlow) - Agentic reasoning architecture (Planner→Executor→Verifier pattern)
- [Azure OpenAI](https://azure.microsoft.com/en-us/products/ai-services/openai-service) - LLM backend (GPT-5.2/O1 models)
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [React](https://react.dev/) - Frontend UI framework
- [LangChain](https://langchain.com/) - LLM orchestration (used in AgentFlow SDK)
- [LiteLLM](https://github.com/BerriAI/litellm) - Multi-provider LLM proxy

---

## 📊 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FULL SYSTEM ARCHITECTURE                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────┐     ┌──────────────────────────────────────────────────────────┐
│   Frontend  │     │                      Backend                              │
│   (React)   │     │                                                          │
│             │     │  ┌─────────────────────────────────────────────────────┐ │
│ ┌─────────┐ │     │  │                FastAPI (main.py)                    │ │
│ │  Chat   │ │────▶│  │  POST /api/agent/query                              │ │
│ │Interface│ │     │  └───────────────────┬─────────────────────────────────┘ │
│ └─────────┘ │     │                      │                                   │
│             │     │                      ▼                                   │
│ ┌─────────┐ │     │  ┌─────────────────────────────────────────────────────┐ │
│ │Dashboard│ │     │  │          AgentFlowSolver (agentflow_crm.py)         │ │
│ └─────────┘ │     │  │                                                     │ │
│             │     │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │ │
│ ┌─────────┐ │     │  │  │ Planner  │─▶│ Executor │─▶│ Verifier │          │ │
│ │Pipeline │ │     │  │  └────┬─────┘  └────┬─────┘  └────┬─────┘          │ │
│ │  View   │ │     │  │       │             │             │                │ │
│ └─────────┘ │     │  │       ▼             ▼             ▼                │ │
└─────────────┘     │  │  ┌──────────────────────────────────────┐          │ │
                    │  │  │              Memory                   │          │ │
                    │  │  └──────────────────────────────────────┘          │ │
                    │  └───────────────────┬─────────────────────────────────┘ │
                    │                      │                                   │
                    │                      ▼                                   │
                    │  ┌─────────────────────────────────────────────────────┐ │
                    │  │           CRMDatabaseTool                           │ │
                    │  │  • Executes SQL SELECT queries                      │ │
                    │  │  • Security: Only SELECT allowed                    │ │
                    │  └───────────────────┬─────────────────────────────────┘ │
                    │                      │                                   │
                    │                      ▼                                   │
                    │  ┌─────────────────────────────────────────────────────┐ │
                    │  │           LLM Engine (llm_engine.py)                │ │
                    │  │  • Azure OpenAI (GPT-5.2)                           │ │
                    │  │  • Fallback to pattern matching                     │ │
                    │  └─────────────────────────────────────────────────────┘ │
                    └──────────────────────────────────────────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────────────────┐
                    │                    PostgreSQL                             │
                    │  Tables: leads, contacts, accounts, opportunities,        │
                    │          activities, campaigns, users                     │
                    └──────────────────────────────────────────────────────────┘
```
