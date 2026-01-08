"""
Calendar/Meeting Tool for Agentic CRM.
Adapted for existing schema.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import json

from app.llm_engine import create_azure_engine
from app.database import execute_query, execute_write


class CalendarTool:
    """
    Custom AgentFlow tool for meeting scheduling.
    """
    
    name = "calendar_tool"
    description = """
    Meeting scheduling operations including:
    - Finding available time slots
    - Creating and managing meetings
    - AI-suggested meeting times
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.llm = create_azure_engine(temperature=0.3)
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute calendar operation."""
        
        operation = params.get("operation", "find_slots")
        
        if self.verbose:
            print(f"📅 CalendarTool: Executing {operation}")
        
        operations = {
            "find_slots": self._find_slots,
            "create_meeting": self._create_meeting,
            "suggest_time": self._suggest_time,
            "get_meetings": self._get_meetings,
            "cancel_meeting": self._cancel_meeting,
        }
        
        handler = operations.get(operation)
        if not handler:
            return {"success": False, "error": f"Unknown operation: {operation}"}
        
        try:
            return handler(params)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _find_slots(self, params: Dict) -> Dict:
        """Find available meeting slots."""
        duration_minutes = params.get("duration_minutes", 30)
        days_ahead = params.get("days_ahead", 7)
        
        # Get existing meetings
        query = """
            SELECT start_time, end_time FROM meetings
            WHERE start_time >= NOW()
            AND start_time < NOW() + INTERVAL ':days days'
            AND status != 'cancelled'
            ORDER BY start_time
        """
        existing = execute_query(query.replace(":days", str(days_ahead)), {})
        
        # Generate available slots (9 AM - 5 PM business hours)
        slots = []
        now = datetime.now()
        
        for day_offset in range(1, days_ahead + 1):
            date = now.date() + timedelta(days=day_offset)
            
            # Skip weekends
            if date.weekday() >= 5:
                continue
            
            for hour in range(9, 17):
                slot_start = datetime.combine(date, datetime.min.time().replace(hour=hour))
                slot_end = slot_start + timedelta(minutes=duration_minutes)
                
                # Check if slot conflicts with existing meetings
                conflicts = False
                for meeting in existing:
                    m_start = meeting.get("start_time")
                    m_end = meeting.get("end_time")
                    if m_start and m_end:
                        if slot_start < m_end and slot_end > m_start:
                            conflicts = True
                            break
                
                if not conflicts:
                    slots.append({
                        "start": slot_start.isoformat(),
                        "end": slot_end.isoformat(),
                        "date": date.strftime("%A, %B %d"),
                        "time": slot_start.strftime("%I:%M %p")
                    })
        
        return {
            "success": True,
            "slots": slots[:20],  # Limit results
            "duration_minutes": duration_minutes
        }
    
    def _create_meeting(self, params: Dict) -> Dict:
        """Create a new meeting."""
        
        title = params.get("title", "Meeting")
        meeting_type = params.get("meeting_type", "general")
        start_time = params.get("start_time")
        contact_id = params.get("contact_id")
        opportunity_id = params.get("opportunity_id")
        duration_minutes = params.get("duration_minutes", 30)
        
        if not start_time:
            return {"success": False, "error": "start_time is required"}
        
        # Parse start time if string
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        # Create meeting
        sql = """
            INSERT INTO meetings (
                title, meeting_type, start_time, end_time,
                contact_id, opportunity_id, status, ai_suggested
            ) VALUES (
                :title, :type, :start, :end,
                :contact_id, :opportunity_id, 'scheduled', :ai_suggested
            )
            RETURNING id
        """
        
        result = execute_query(sql, {
            "title": title,
            "type": meeting_type,
            "start": start_time,
            "end": end_time,
            "contact_id": contact_id,
            "opportunity_id": opportunity_id,
            "ai_suggested": params.get("ai_suggested", False)
        })
        
        meeting_id = str(result[0]["id"]) if result else None
        
        return {
            "success": True,
            "meeting": {
                "id": meeting_id,
                "title": title,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }
        }
    
    def _suggest_time(self, params: Dict) -> Dict:
        """AI-suggested optimal meeting time."""
        contact_id = params.get("contact_id")
        meeting_type = params.get("meeting_type", "discovery")
        
        # Get contact context
        contact = None
        if contact_id:
            query = """
                SELECT c.*, a.account_name, a.industry
                FROM contacts c
                LEFT JOIN accounts a ON c.account_id = a.account_id
                WHERE c.contact_id = :contact_id
            """
            results = execute_query(query, {"contact_id": contact_id})
            if results:
                contact = results[0]
        
        # Find available slots
        slots_result = self._find_slots({"duration_minutes": 30, "days_ahead": 7})
        slots = slots_result.get("slots", [])[:5]
        
        if not slots:
            return {"success": False, "error": "No available slots found"}
        
        # AI suggests best time
        system_prompt = """Based on best practices, rank these meeting slots from best to worst.
Consider: early morning (9-10 AM) is often best for important meetings, 
avoid lunch hours, Tuesday-Thursday are usually optimal.
Return JSON: {"best_slot_index": 0, "reasoning": "text"}"""

        slot_summary = json.dumps([{"date": s["date"], "time": s["time"]} for s in slots])
        response = self.llm.generate(slot_summary, system_prompt=system_prompt)
        
        try:
            suggestion = json.loads(response)
            best_index = suggestion.get("best_slot_index", 0)
        except:
            best_index = 0
        
        best_slot = slots[min(best_index, len(slots) - 1)]
        
        return {
            "success": True,
            "suggested_slot": best_slot,
            "all_slots": slots,
            "meeting_type": meeting_type
        }
    
    def _get_meetings(self, params: Dict) -> Dict:
        """Get upcoming meetings."""
        days = params.get("days", 7)
        
        query = """
            SELECT 
                m.*,
                c.first_name, c.last_name, c.email,
                a.account_name
            FROM meetings m
            LEFT JOIN contacts c ON m.contact_id = c.contact_id
            LEFT JOIN accounts a ON c.account_id = a.account_id
            WHERE m.start_time >= NOW()
            AND m.start_time < NOW() + INTERVAL ':days days'
            AND m.status != 'cancelled'
            ORDER BY m.start_time
        """
        meetings = execute_query(query.replace(":days", str(days)), {})
        
        return {
            "success": True,
            "meetings": meetings
        }
    
    def _cancel_meeting(self, params: Dict) -> Dict:
        """Cancel a meeting."""
        meeting_id = params.get("meeting_id")
        
        sql = "UPDATE meetings SET status = 'cancelled', updated_at = NOW() WHERE id = :id"
        execute_write(sql, {"id": meeting_id})
        
        return {"success": True, "meeting_id": meeting_id}
