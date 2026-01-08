"""
Automated Follow-Up Agent.
Adapted for existing CRM schema.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import json

from app.tools.database_tool import DatabaseTool
from app.tools.email_tool import EmailTool
from app.llm_engine import create_azure_engine
from app.database import execute_query, execute_write


class FollowUpAgent:
    """
    AI Agent for automated follow-up orchestration.
    Uses existing schema: leads, opportunities, activities.
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.db_tool = DatabaseTool(verbose=verbose)
        self.email_tool = EmailTool(verbose=verbose)
        self.llm = create_azure_engine(temperature=0.3)
        self.agent_type = "followup"
    
    def check_and_trigger_followups(self) -> Dict[str, Any]:
        """Main agent loop: Check for leads/deals needing follow-up."""
        
        if self.verbose:
            print("📧 FollowUpAgent: Scanning for follow-up opportunities...")
        
        results = {
            "overdue_leads": [],
            "stale_opportunities": [],
            "scheduled_followups": [],
            "emails_drafted": []
        }
        
        overdue = self._get_overdue_followups()
        results["overdue_leads"] = overdue
        
        stale = self._get_stale_opportunities()
        results["stale_opportunities"] = stale
        
        for lead in overdue[:10]:
            action = self._process_overdue_lead(lead)
            if action:
                results["scheduled_followups"].append(action)
        
        for opp in stale[:10]:
            action = self._process_stale_opportunity(opp)
            if action:
                results["emails_drafted"].append(action)
        
        self._log_execution(results)
        
        return {
            "success": True,
            "summary": {
                "overdue_leads_found": len(overdue),
                "stale_opportunities_found": len(stale),
                "followups_scheduled": len(results["scheduled_followups"]),
                "emails_drafted": len(results["emails_drafted"])
            },
            "details": results
        }
    
    def _get_overdue_followups(self) -> List[Dict]:
        """Get leads with overdue follow-ups."""
        
        query = """
            SELECT 
                l.lead_id, l.lead_status, l.ai_score, l.lead_rating,
                l.first_name, l.last_name, l.email, l.company_name,
                l.last_contacted_at, l.next_followup_at,
                EXTRACT(DAY FROM (NOW() - COALESCE(l.last_contacted_at, l.created_at))) as days_since_contact
            FROM leads l
            WHERE l.lead_status IN ('New', 'Contacted', 'Qualified')
            AND l.is_converted = FALSE
            AND (
                l.next_followup_at < NOW()
                OR (l.next_followup_at IS NULL AND l.last_contacted_at < NOW() - INTERVAL '7 days')
                OR (l.last_contacted_at IS NULL AND l.created_at < NOW() - INTERVAL '3 days')
            )
            ORDER BY l.ai_score DESC NULLS LAST
            LIMIT 50
        """
        return execute_query(query, {})
    
    def _get_stale_opportunities(self) -> List[Dict]:
        """Get opportunities without recent activity."""
        
        query = """
            SELECT 
                o.opportunity_id, o.opportunity_name, o.stage, o.amount, o.probability,
                o.close_date,
                a.account_name,
                c.first_name, c.last_name, c.email,
                (SELECT MAX(created_at) FROM activities 
                 WHERE related_to_type = 'Opportunity' AND related_to_id = o.opportunity_id) as last_activity,
                EXTRACT(DAY FROM (NOW() - COALESCE(
                    (SELECT MAX(created_at) FROM activities 
                     WHERE related_to_type = 'Opportunity' AND related_to_id = o.opportunity_id),
                    o.created_at
                ))) as days_stale
            FROM opportunities o
            LEFT JOIN accounts a ON o.account_id = a.account_id
            LEFT JOIN contacts c ON o.primary_contact_id = c.contact_id
            WHERE o.is_closed = FALSE
            AND EXTRACT(DAY FROM (NOW() - o.updated_at)) > 7
            ORDER BY o.amount DESC NULLS LAST
            LIMIT 50
        """
        return execute_query(query, {})
    
    def _process_overdue_lead(self, lead: Dict) -> Optional[Dict]:
        """Process an overdue lead and schedule follow-up."""
        
        days_since = lead.get("days_since_contact") or 0
        
        if days_since <= 3:
            followup_type = "soft_check_in"
            delay_hours = 24
        elif days_since <= 7:
            followup_type = "value_add"
            delay_hours = 12
        elif days_since <= 14:
            followup_type = "re_engagement"
            delay_hours = 6
        else:
            followup_type = "break_up"
            delay_hours = 1
        
        strategy = self._generate_followup_strategy(lead, followup_type)
        scheduled_time = datetime.now() + timedelta(hours=delay_hours)
        
        execute_write("""
            UPDATE leads 
            SET next_followup_at = :time, updated_at = NOW()
            WHERE lead_id = :id
        """, {"time": scheduled_time, "id": lead["lead_id"]})
        
        # Log activity
        execute_write("""
            INSERT INTO activities (
                activity_type, subject, description, 
                related_to_type, related_to_id,
                due_date, status, ai_generated
            ) VALUES (
                'Task', :subject, :description, 
                'Lead', :lead_id,
                :due_date, 'Open', TRUE
            )
        """, {
            "subject": f"Follow-up: {followup_type.replace('_', ' ').title()}",
            "description": strategy.get("action_plan", ""),
            "lead_id": lead["lead_id"],
            "due_date": scheduled_time
        })
        
        return {
            "lead_id": str(lead["lead_id"]),
            "contact": f"{lead.get('first_name', '')} {lead.get('last_name', '')}",
            "followup_type": followup_type,
            "scheduled_for": scheduled_time.isoformat(),
            "strategy": strategy
        }
    
    def _process_stale_opportunity(self, opp: Dict) -> Optional[Dict]:
        """Process a stale opportunity and draft re-engagement email."""
        
        draft_result = self.email_tool.execute({
            "operation": "draft",
            "contact_id": None,
            "email_type": "re_engagement",
            "context": f"""
Opportunity: {opp.get('opportunity_name')}
Stage: {opp.get('stage')}
Value: ${opp.get('amount', 0):,.0f}
Days stale: {opp.get('days_stale', 0)}
Company: {opp.get('account_name')}
Contact: {opp.get('first_name')} {opp.get('last_name')}
"""
        })
        
        if draft_result.get("success"):
            execute_write("""
                INSERT INTO activities (
                    activity_type, subject, description, 
                    related_to_type, related_to_id,
                    status, ai_generated
                ) VALUES (
                    'Email', :subject, :body, 
                    'Opportunity', :opp_id,
                    'Open', TRUE
                )
            """, {
                "subject": draft_result.get("email", {}).get("subject", "Follow-up"),
                "body": draft_result.get("email", {}).get("body", "")[:500],
                "opp_id": opp["opportunity_id"]
            })
        
        return {
            "opportunity_id": str(opp["opportunity_id"]),
            "opportunity_name": opp.get("opportunity_name"),
            "days_stale": opp.get("days_stale"),
            "email_drafted": draft_result.get("success", False),
            "email_subject": draft_result.get("email", {}).get("subject", "")
        }
    
    def _generate_followup_strategy(self, lead: Dict, followup_type: str) -> Dict:
        """Generate AI-powered follow-up strategy."""
        
        system_prompt = """You are a sales engagement strategist. 
Generate a brief strategy including key talking points, value proposition, and call-to-action.
Keep response under 150 words. Return as JSON with keys: talking_points, value_prop, cta, action_plan"""

        prompt = f"""
Lead: {lead.get('first_name')} {lead.get('last_name')}
Company: {lead.get('company_name')}
Score: {lead.get('ai_score')}
Rating: {lead.get('lead_rating')}
Days since contact: {lead.get('days_since_contact')}
Follow-up Type: {followup_type}
"""

        response = self.llm.generate(prompt, system_prompt=system_prompt)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"action_plan": response, "value_prop": response, "cta": "Schedule a call"}
    
    def get_followup_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get follow-up performance analytics."""
        
        query = f"""
            SELECT 
                DATE(due_date) as date,
                COUNT(*) as total_scheduled,
                COUNT(CASE WHEN status = 'Completed' THEN 1 END) as completed,
                COUNT(CASE WHEN ai_generated = TRUE THEN 1 END) as ai_generated
            FROM activities
            WHERE activity_type IN ('Email', 'Task', 'Call')
            AND due_date >= NOW() - INTERVAL '{days} days'
            GROUP BY DATE(due_date)
            ORDER BY date DESC
        """
        daily_stats = execute_query(query, {})
        
        return {
            "success": True,
            "period_days": days,
            "daily_stats": daily_stats,
            "summary": {
                "total_scheduled": sum(d.get("total_scheduled", 0) for d in daily_stats),
                "completed": sum(d.get("completed", 0) for d in daily_stats),
                "ai_generated": sum(d.get("ai_generated", 0) for d in daily_stats)
            }
        }
    
    def _log_execution(self, results: Dict):
        """Log agent execution."""
        
        execute_write("""
            INSERT INTO agent_logs (agent_type, action, output_data, model_used, success)
            VALUES (:agent_type, 'check_and_trigger', :output, 'gpt-5.2-chat', TRUE)
        """, {
            "agent_type": self.agent_type,
            "output": json.dumps(results.get("summary", {}))
        })
