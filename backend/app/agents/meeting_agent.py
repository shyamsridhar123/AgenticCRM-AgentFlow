"""
Meeting Scheduling Agent.
Adapted for existing CRM schema.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import json

from app.tools.calendar_tool import CalendarTool
from app.tools.database_tool import DatabaseTool
from app.llm_engine import create_azure_engine
from app.database import execute_query, execute_write


class MeetingAgent:
    """
    AI Agent for intelligent meeting scheduling.
    Uses existing schema: contacts, accounts, opportunities.
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.calendar_tool = CalendarTool(verbose=verbose)
        self.db_tool = DatabaseTool(verbose=verbose)
        self.llm = create_azure_engine(temperature=0.3)
        self.agent_type = "meeting"
    
    def schedule_meeting(
        self,
        contact_id: str,
        meeting_type: str = "discovery",
        opportunity_id: str = None,
        preferences: Dict = None
    ) -> Dict[str, Any]:
        """Intelligently schedule a meeting with a contact."""
        
        if self.verbose:
            print(f"📅 MeetingAgent: Scheduling {meeting_type} meeting for contact {contact_id}")
        
        contact = self._get_contact_context(contact_id)
        if not contact:
            return {"success": False, "error": "Contact not found"}
        
        # Suggest optimal time
        suggestion = self.calendar_tool.execute({
            "operation": "suggest_time",
            "contact_id": contact_id,
            "meeting_type": meeting_type
        })
        
        if not suggestion.get("success"):
            return suggestion
        
        suggested_slot = suggestion.get("suggested_slot", {})
        
        # Create meeting
        meeting_result = self.calendar_tool.execute({
            "operation": "create_meeting",
            "title": f"{meeting_type.title()} with {contact.get('first_name', '')} {contact.get('last_name', '')}",
            "contact_id": contact_id,
            "opportunity_id": opportunity_id,
            "meeting_type": meeting_type,
            "start_time": suggested_slot.get("start"),
            "ai_suggested": True
        })
        
        if not meeting_result.get("success"):
            return meeting_result
        
        prep = self._generate_meeting_prep(contact, meeting_type)
        self._log_execution(contact_id, meeting_type, meeting_result)
        
        return {
            "success": True,
            "meeting": meeting_result.get("meeting"),
            "contact": {
                "name": f"{contact.get('first_name', '')} {contact.get('last_name', '')}",
                "email": contact.get("email"),
                "company": contact.get("account_name")
            },
            "prep": prep,
            "alternative_slots": suggestion.get("all_slots", [])[:3]
        }
    
    def get_upcoming_meetings(self, days: int = 7) -> Dict[str, Any]:
        """Get upcoming meetings with AI prep notes."""
        
        result = self.calendar_tool.execute({
            "operation": "get_meetings",
            "days": days
        })
        
        meetings = result.get("meetings", [])
        
        enriched = []
        for meeting in meetings:
            prep = self._generate_quick_prep(meeting)
            enriched.append({**meeting, "quick_prep": prep})
        
        return {
            "success": True,
            "count": len(enriched),
            "meetings": enriched
        }
    
    def reschedule_with_suggestion(self, meeting_id: str, reason: str = "") -> Dict[str, Any]:
        """Reschedule a meeting with AI-suggested new time."""
        
        meeting = execute_query(
            "SELECT * FROM meetings WHERE id = :id",
            {"id": meeting_id}
        )
        
        if not meeting:
            return {"success": False, "error": "Meeting not found"}
        
        meeting = meeting[0]
        
        slots_result = self.calendar_tool.execute({
            "operation": "find_slots",
            "duration_minutes": 30,
            "days_ahead": 7
        })
        
        if not slots_result.get("slots"):
            return {"success": False, "error": "No available slots"}
        
        new_slot = slots_result["slots"][0]
        
        execute_write("""
            UPDATE meetings 
            SET start_time = :start, end_time = :end, updated_at = NOW()
            WHERE id = :id
        """, {
            "start": new_slot["start"],
            "end": new_slot["end"],
            "id": meeting_id
        })
        
        return {
            "success": True,
            "original_time": meeting.get("start_time"),
            "new_time": new_slot["start"],
            "reason": reason
        }
    
    def _get_contact_context(self, contact_id: str) -> Optional[Dict]:
        """Get contact with account info."""
        
        query = """
            SELECT 
                c.*,
                a.account_name, a.industry, a.annual_revenue,
                o.stage as opp_stage, o.amount as opp_amount
            FROM contacts c
            LEFT JOIN accounts a ON c.account_id = a.account_id
            LEFT JOIN opportunities o ON o.primary_contact_id = c.contact_id AND o.is_closed = FALSE
            WHERE c.contact_id = :contact_id
        """
        results = execute_query(query, {"contact_id": contact_id})
        return results[0] if results else None
    
    def _generate_meeting_prep(self, contact: Dict, meeting_type: str) -> Dict:
        """Generate AI meeting prep."""
        
        system_prompt = """Generate brief meeting preparation notes including:
1. Key talking points (3-4 bullet points)
2. Questions to ask
3. Desired outcome
Return as JSON."""

        prompt = f"""
Meeting Type: {meeting_type}
Contact: {contact.get('first_name')} {contact.get('last_name')}
Title: {contact.get('title')}
Company: {contact.get('account_name')} ({contact.get('industry')})
Opportunity Stage: {contact.get('opp_stage', 'N/A')}
Opportunity Value: ${contact.get('opp_amount', 0):,.0f}
"""

        response = self.llm.generate(prompt, system_prompt=system_prompt)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"notes": response}
    
    def _generate_quick_prep(self, meeting: Dict) -> str:
        """Quick one-liner prep."""
        company = meeting.get("account_name", "Unknown")
        meeting_type = meeting.get("meeting_type", "meeting")
        return f"{company} - {meeting_type.title()} call"
    
    def _log_execution(self, contact_id: str, meeting_type: str, result: Dict):
        """Log agent execution."""
        
        execute_write("""
            INSERT INTO agent_logs (
                agent_type, action, input_data, output_data,
                model_used, related_to_type, related_to_id, success
            ) VALUES (
                :agent_type, 'schedule_meeting', :input, :output,
                'gpt-5.2-chat', 'Contact', CAST(:contact_id AS UUID), :success
            )
        """, {
            "agent_type": self.agent_type,
            "input": json.dumps({"contact_id": contact_id, "meeting_type": meeting_type}),
            "output": json.dumps({"meeting_id": result.get("meeting", {}).get("id")}),
            "contact_id": contact_id,
            "success": result.get("success", False)
        })
