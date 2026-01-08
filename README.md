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

This application uses the [AgentFlow](https://github.com/lupantech/AgentFlow) pattern for agentic reasoning:

```
User Query → Planner → Executor → Verifier → Response
                ↓           ↓
           Memory ← CRM Database Tool
```

| Component | Purpose |
|-----------|---------|
| **Planner** | Analyzes queries, generates SQL |
| **Executor** | Runs database tools |
| **Verifier** | Validates results |
| **Memory** | Tracks execution history |

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
│   │   ├── agents/          # AI agents (legacy)
│   │   ├── tools/           # Database, ML, Calendar tools
│   │   ├── agentflow_crm.py # AgentFlow solver
│   │   ├── llm_engine.py    # Azure OpenAI integration
│   │   └── main.py          # FastAPI app
│   ├── agentflow_sdk/       # AgentFlow SDK
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Page components
│   │   └── services/        # API services
│   └── package.json
└── database/
    └── init_schema.sql      # Database schema
```

## 🔧 AgentFlow Components

### CRM Database Tool
```python
from app.agentflow_crm import create_agentflow_solver

solver = create_agentflow_solver(verbose=True)
result = solver.solve("How many leads do we have?")
# Returns: {"success": True, "result_count": 17, "agentflow": True}
```

### Custom Tool Development
Extend `CRMDatabaseTool` pattern:
```python
class MyCustomTool:
    def __init__(self):
        self.tool_name = "my_tool"
    
    def execute(self, **kwargs) -> dict:
        # Tool logic here
        return {"success": True, "result": ...}
```

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [AgentFlow](https://github.com/lupantech/AgentFlow) - Agentic architecture
- [Azure OpenAI](https://azure.microsoft.com/en-us/products/ai-services/openai-service) - LLM backend
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [React](https://react.dev/) - Frontend framework
