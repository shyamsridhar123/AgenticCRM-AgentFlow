"""
CRM Tools package initialization.
Exports all custom tools for AgentFlow integration.
"""

from app.tools.database_tool import DatabaseTool
from app.tools.email_tool import EmailTool
from app.tools.calendar_tool import CalendarTool
from app.tools.ml_tool import MLTool

__all__ = [
    "DatabaseTool",
    "EmailTool", 
    "CalendarTool",
    "MLTool"
]


# Tool metadata for AgentFlow registration
TOOL_METADATA = {
    "Database_Tool": {
        "name": "Database_Tool",
        "description": "Query and manage CRM database records including leads, contacts, companies, deals, and activities.",
        "usage": "Use this tool to search, filter, create, update, or delete CRM records.",
        "parameters": {
            "operation": "The database operation: 'query', 'insert', 'update', 'delete'",
            "table": "Target table: 'leads', 'contacts', 'companies', 'deals', 'activities'",
            "filters": "Optional filter conditions as key-value pairs",
            "data": "Data for insert/update operations",
            "limit": "Maximum number of records to return (default: 50)"
        }
    },
    "Email_Tool": {
        "name": "Email_Tool",
        "description": "Draft, send, and analyze email communications with CRM contacts.",
        "usage": "Use this tool to compose personalized emails, summarize threads, or schedule follow-ups.",
        "parameters": {
            "operation": "The email operation: 'draft', 'summarize', 'schedule_followup'",
            "contact_id": "The contact UUID to email",
            "context": "Additional context for personalization",
            "template_id": "Optional email template UUID"
        }
    },
    "Calendar_Tool": {
        "name": "Calendar_Tool",
        "description": "Schedule and manage meetings with CRM contacts.",
        "usage": "Use this tool to find available time slots, create meetings, and send calendar invites.",
        "parameters": {
            "operation": "The calendar operation: 'find_slots', 'create_meeting', 'reschedule', 'cancel'",
            "contact_id": "The contact UUID for the meeting",
            "duration_minutes": "Meeting duration in minutes",
            "meeting_type": "Type: 'discovery', 'demo', 'proposal', 'negotiation', 'onboarding'",
            "preferred_times": "Optional list of preferred time ranges"
        }
    },
    "ML_Tool": {
        "name": "ML_Tool",
        "description": "Machine learning predictions for lead scoring, deal forecasting, and pipeline analysis.",
        "usage": "Use this tool to score leads, predict deal outcomes, or analyze pipeline health.",
        "parameters": {
            "operation": "The ML operation: 'score_lead', 'predict_deal', 'analyze_pipeline'",
            "entity_id": "The entity UUID (lead, deal, etc.)",
            "features": "Optional additional features for prediction"
        }
    }
}
