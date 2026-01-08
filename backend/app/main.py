"""
Agentic CRM - FastAPI Backend
Main application entry point with all API endpoints.
"""

from contextlib import asynccontextmanager
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from app.config import settings
from app.database import test_connection, get_db

# Import agents
from app.agents.lead_agent import LeadScoringAgent
from app.agents.followup_agent import FollowUpAgent
from app.agents.nl_query_agent import NLQueryAgent
from app.agents.meeting_agent import MeetingAgent
from app.agents.pipeline_agent import PipelineAgent
from app.agents.email_agent import EmailAgent
from app.agentflow_crm import create_agentflow_solver


# ============================================
# PYDANTIC MODELS
# ============================================

class NLQueryRequest(BaseModel):
    query: str = Field(..., description="Natural language query", min_length=3)
    user_id: Optional[str] = None


class LeadScoreRequest(BaseModel):
    lead_id: str = Field(..., description="Lead UUID to score")


class EmailDraftRequest(BaseModel):
    contact_id: str = Field(..., description="Contact UUID")
    email_type: str = Field(default="followup", description="Type of email")
    deal_id: Optional[str] = None
    custom_context: Optional[str] = ""


class ScheduleMeetingRequest(BaseModel):
    contact_id: str = Field(..., description="Contact UUID")
    meeting_type: str = Field(default="discovery")
    deal_id: Optional[str] = None
    preferences: Optional[dict] = None


class FollowUpTriggerRequest(BaseModel):
    lead_id: Optional[str] = None
    days_delay: int = Field(default=3, ge=1, le=30)
    context: Optional[str] = ""


class EmailSequenceRequest(BaseModel):
    contact_id: str
    sequence_type: str = Field(default="nurture")
    email_count: int = Field(default=5, ge=1, le=10)


# ============================================
# APPLICATION SETUP
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("🚀 Starting Agentic CRM Backend...")
    
    # Test database connection
    if test_connection():
        print("✅ Database connection successful")
    else:
        print("❌ Database connection failed - check your configuration")
    
    # Initialize agents
    app.state.lead_agent = LeadScoringAgent(verbose=settings.agentflow_verbose)
    app.state.followup_agent = FollowUpAgent(verbose=settings.agentflow_verbose)
    app.state.nl_query_agent = NLQueryAgent(verbose=settings.agentflow_verbose)
    app.state.meeting_agent = MeetingAgent(verbose=settings.agentflow_verbose)
    app.state.pipeline_agent = PipelineAgent(verbose=settings.agentflow_verbose)
    app.state.email_agent = EmailAgent(verbose=settings.agentflow_verbose)
    
    # Initialize AgentFlow solver for enhanced query processing
    app.state.agentflow_solver = create_agentflow_solver(
        max_steps=10, 
        verbose=settings.agentflow_verbose
    )
    
    print("✅ AI Agents initialized (with AgentFlow)")
    print("   Components: Planner, Executor, Verifier, Memory")
    print(f"🌐 Server running at http://{settings.app_host}:{settings.app_port}")
    
    yield
    
    # Shutdown
    print("👋 Shutting down Agentic CRM Backend...")


app = FastAPI(
    title="Agentic CRM API",
    description="AI-powered CRM with intelligent agents for lead scoring, follow-ups, and pipeline management",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# HEALTH & STATUS ENDPOINTS
# ============================================

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Agentic CRM API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    db_ok = test_connection()
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "timestamp": datetime.now().isoformat()
    }


# ============================================
# NATURAL LANGUAGE QUERY ENDPOINTS
# ============================================

@app.post("/api/agent/query", tags=["NL Query"])
async def natural_language_query(request: NLQueryRequest):
    """
    Execute a natural language query against the CRM database.
    
    Examples:
    - "Show me all qualified leads from this month"
    - "What are the top 10 deals by value?"
    - "Find all contacts from technology companies"
    """
    try:
        # Use AgentFlow solver (Planner→Executor→Verifier flow)
        solver = app.state.agentflow_solver
        result = solver.solve(request.query)
        
        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "query": request.query,
                "results": [],
                "result_count": 0,
                "summary": f"Query failed: {result.get('error', 'Unknown error')}",
                "agentflow": True
            }
        
        return result
    except Exception as e:
        print(f"❌ Query endpoint error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "query": request.query,
            "results": [],
            "result_count": 0,
            "summary": f"Error: {str(e)}"
        }


@app.get("/api/agent/query/examples", tags=["NL Query"])
async def get_query_examples():
    """Get example natural language queries."""
    agent = app.state.nl_query_agent
    return {"examples": agent.get_example_queries()}


@app.get("/api/agent/query/history", tags=["NL Query"])
async def get_query_history(limit: int = Query(default=20, le=100)):
    """Get recent query history."""
    agent = app.state.nl_query_agent
    return {"history": agent.get_query_history(limit)}


# ============================================
# LEAD SCORING ENDPOINTS
# ============================================

@app.post("/api/agent/score-lead", tags=["Lead Scoring"])
async def score_lead(request: LeadScoreRequest):
    """Score a specific lead using AI analysis."""
    agent = app.state.lead_agent
    result = agent.analyze_and_score(request.lead_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@app.post("/api/agent/score-leads/batch", tags=["Lead Scoring"])
async def batch_score_leads(limit: int = Query(default=50, le=100)):
    """Score all unscored new leads."""
    agent = app.state.lead_agent
    return agent.batch_score_new_leads(limit)


@app.post("/api/agent/route-leads", tags=["Lead Scoring"])
async def route_qualified_leads():
    """Auto-route qualified leads to sales reps."""
    agent = app.state.lead_agent
    return agent.auto_route_qualified_leads()


# ============================================
# EMAIL DRAFTING ENDPOINTS
# ============================================

@app.post("/api/agent/draft-email", tags=["Email"])
async def draft_email(request: EmailDraftRequest):
    """Generate a personalized email draft using AI."""
    agent = app.state.email_agent
    result = agent.draft_email(
        contact_id=request.contact_id,
        email_type=request.email_type,
        deal_id=request.deal_id,
        custom_context=request.custom_context or ""
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@app.post("/api/agent/email-sequence", tags=["Email"])
async def generate_email_sequence(request: EmailSequenceRequest):
    """Generate a complete email sequence."""
    agent = app.state.email_agent
    return agent.generate_sequence(
        contact_id=request.contact_id,
        sequence_type=request.sequence_type,
        email_count=request.email_count
    )


@app.get("/api/agent/email/summarize/{contact_id}", tags=["Email"])
async def summarize_email_thread(contact_id: str):
    """Summarize email conversations with a contact."""
    agent = app.state.email_agent
    return agent.summarize_conversation(contact_id)


@app.get("/api/agent/email/analytics", tags=["Email"])
async def email_analytics(days: int = Query(default=30, le=365)):
    """Get email performance analytics."""
    agent = app.state.email_agent
    return agent.analyze_email_performance(days)


# ============================================
# MEETING SCHEDULING ENDPOINTS
# ============================================

@app.post("/api/agent/schedule", tags=["Meetings"])
async def schedule_meeting(request: ScheduleMeetingRequest):
    """Schedule a meeting with AI-optimized timing."""
    agent = app.state.meeting_agent
    result = agent.schedule_meeting(
        contact_id=request.contact_id,
        meeting_type=request.meeting_type,
        deal_id=request.deal_id,
        preferences=request.preferences
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@app.get("/api/agent/meetings/upcoming", tags=["Meetings"])
async def get_upcoming_meetings(days: int = Query(default=7, le=30)):
    """Get upcoming meetings with AI prep notes."""
    agent = app.state.meeting_agent
    return agent.get_upcoming_meetings(days)


@app.post("/api/agent/meetings/{meeting_id}/reschedule", tags=["Meetings"])
async def reschedule_meeting(meeting_id: str, reason: str = ""):
    """Reschedule a meeting with AI-suggested new time."""
    agent = app.state.meeting_agent
    return agent.reschedule_with_suggestion(meeting_id, reason)


# ============================================
# PIPELINE & FORECASTING ENDPOINTS
# ============================================

@app.get("/api/pipeline/forecast", tags=["Pipeline"])
async def get_pipeline_forecast(period_days: int = Query(default=90, le=365)):
    """Get AI-powered pipeline forecast."""
    agent = app.state.pipeline_agent
    return agent.generate_forecast(period_days)


@app.get("/api/pipeline/at-risk", tags=["Pipeline"])
async def get_at_risk_deals():
    """Identify deals at risk of being lost."""
    agent = app.state.pipeline_agent
    return agent.identify_at_risk_deals()


@app.get("/api/pipeline/health", tags=["Pipeline"])
async def get_pipeline_health():
    """Get overall pipeline health score."""
    agent = app.state.pipeline_agent
    return agent.get_pipeline_health_score()


# ============================================
# FOLLOW-UP AUTOMATION ENDPOINTS
# ============================================

@app.post("/api/followup/trigger", tags=["Follow-up"])
async def trigger_followups():
    """Run the follow-up automation agent."""
    agent = app.state.followup_agent
    return agent.check_and_trigger_followups()


@app.get("/api/followup/analytics", tags=["Follow-up"])
async def followup_analytics(days: int = Query(default=30, le=90)):
    """Get follow-up performance analytics."""
    agent = app.state.followup_agent
    return agent.get_followup_analytics(days)


# ============================================
# RUN SERVER
# ============================================

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug
    )
