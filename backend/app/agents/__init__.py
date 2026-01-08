"""
CRM Agents package initialization.
Exports all AI agents for the agentic CRM.
"""

from app.agents.lead_agent import LeadScoringAgent
from app.agents.followup_agent import FollowUpAgent
from app.agents.nl_query_agent import NLQueryAgent
from app.agents.meeting_agent import MeetingAgent
from app.agents.pipeline_agent import PipelineAgent
from app.agents.email_agent import EmailAgent

__all__ = [
    "LeadScoringAgent",
    "FollowUpAgent",
    "NLQueryAgent",
    "MeetingAgent",
    "PipelineAgent",
    "EmailAgent"
]
