"""
Database Tool for Agentic CRM.
Adapted to work with existing CRM database schema.
"""

from typing import Any, Dict, List, Optional
import json
from datetime import datetime

from app.database import execute_query, execute_write


class DatabaseTool:
    """
    Custom AgentFlow tool for CRM database operations.
    Uses existing schema: leads, contacts, accounts, opportunities, activities.
    """
    
    name = "database_tool"
    description = """
    Performs database operations on CRM data including:
    - Query leads, contacts, accounts, opportunities
    - Update lead scores and status
    - Log activities and track interactions
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute database operation based on params."""
        
        operation = params.get("operation", "query")
        
        if self.verbose:
            print(f"🔧 DatabaseTool: Executing {operation}")
        
        operations = {
            "query": self._execute_query,
            "get_lead": self._get_lead,
            "get_contact": self._get_contact,
            "get_account": self._get_account,
            "get_opportunity": self._get_opportunity,
            "update_lead_score": self._update_lead_score,
            "update_lead_status": self._update_lead_status,
            "log_activity": self._log_activity,
            "get_lead_activities": self._get_lead_activities,
        }
        
        handler = operations.get(operation)
        if not handler:
            return {"success": False, "error": f"Unknown operation: {operation}"}
        
        try:
            return handler(params)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _execute_query(self, params: Dict) -> Dict:
        """Execute a raw SQL query."""
        sql = params.get("sql", "")
        query_params = params.get("params", {})
        
        results = execute_query(sql, query_params)
        return {
            "success": True,
            "count": len(results),
            "results": results
        }
    
    def _get_lead(self, params: Dict) -> Dict:
        """Get lead by ID with related data."""
        lead_id = params.get("lead_id")
        
        query = """
            SELECT 
                l.*,
                u.first_name as owner_first_name,
                u.last_name as owner_last_name
            FROM leads l
            LEFT JOIN users u ON l.owner_id = u.user_id
            WHERE l.lead_id = :lead_id
        """
        results = execute_query(query, {"lead_id": lead_id})
        
        if not results:
            return {"success": False, "error": "Lead not found"}
        
        return {"success": True, "lead": results[0]}
    
    def _get_contact(self, params: Dict) -> Dict:
        """Get contact by ID with account info."""
        contact_id = params.get("contact_id")
        
        query = """
            SELECT 
                c.*,
                a.account_name,
                a.industry,
                a.annual_revenue
            FROM contacts c
            LEFT JOIN accounts a ON c.account_id = a.account_id
            WHERE c.contact_id = :contact_id
        """
        results = execute_query(query, {"contact_id": contact_id})
        
        if not results:
            return {"success": False, "error": "Contact not found"}
        
        return {"success": True, "contact": results[0]}
    
    def _get_account(self, params: Dict) -> Dict:
        """Get account by ID."""
        account_id = params.get("account_id")
        
        query = "SELECT * FROM accounts WHERE account_id = :account_id"
        results = execute_query(query, {"account_id": account_id})
        
        if not results:
            return {"success": False, "error": "Account not found"}
        
        return {"success": True, "account": results[0]}
    
    def _get_opportunity(self, params: Dict) -> Dict:
        """Get opportunity with related data."""
        opportunity_id = params.get("opportunity_id")
        
        query = """
            SELECT 
                o.*,
                a.account_name,
                c.first_name as contact_first_name,
                c.last_name as contact_last_name,
                c.email as contact_email
            FROM opportunities o
            LEFT JOIN accounts a ON o.account_id = a.account_id
            LEFT JOIN contacts c ON o.primary_contact_id = c.contact_id
            WHERE o.opportunity_id = :opportunity_id
        """
        results = execute_query(query, {"opportunity_id": opportunity_id})
        
        if not results:
            return {"success": False, "error": "Opportunity not found"}
        
        return {"success": True, "opportunity": results[0]}
    
    def _update_lead_score(self, params: Dict) -> Dict:
        """Update AI score for a lead."""
        lead_id = params.get("lead_id")
        score = params.get("score", 0)
        qualification = params.get("qualification", "")
        
        sql = """
            UPDATE leads 
            SET ai_score = :score,
                ai_qualification = :qualification,
                ai_score_updated_at = NOW()
            WHERE lead_id = :lead_id
        """
        execute_write(sql, {
            "lead_id": lead_id,
            "score": score,
            "qualification": qualification
        })
        
        return {"success": True, "lead_id": lead_id, "score": score}
    
    def _update_lead_status(self, params: Dict) -> Dict:
        """Update lead status."""
        lead_id = params.get("lead_id")
        status = params.get("status")
        
        sql = "UPDATE leads SET lead_status = :status, updated_at = NOW() WHERE lead_id = :lead_id"
        execute_write(sql, {"lead_id": lead_id, "status": status})
        
        return {"success": True, "lead_id": lead_id, "status": status}
    
    def _log_activity(self, params: Dict) -> Dict:
        """Create an activity record."""
        
        sql = """
            INSERT INTO activities (
                activity_type, subject, description,
                related_to_type, related_to_id,
                due_date, status, ai_generated
            ) VALUES (
                :type, :subject, :description,
                :related_type, :related_id,
                :due_date, :status, :ai_generated
            )
            RETURNING activity_id
        """
        
        result = execute_query(sql, {
            "type": params.get("activity_type", "Task"),
            "subject": params.get("subject", ""),
            "description": params.get("description", ""),
            "related_type": params.get("related_to_type"),
            "related_id": params.get("related_to_id"),
            "due_date": params.get("due_date"),
            "status": params.get("status", "Open"),
            "ai_generated": params.get("ai_generated", False)
        })
        
        return {
            "success": True,
            "activity_id": str(result[0]["activity_id"]) if result else None
        }
    
    def _get_lead_activities(self, params: Dict) -> Dict:
        """Get activities for a lead."""
        lead_id = params.get("lead_id")
        
        query = """
            SELECT * FROM activities
            WHERE related_to_type = 'Lead' AND related_to_id = :lead_id
            ORDER BY created_at DESC
            LIMIT 20
        """
        results = execute_query(query, {"lead_id": lead_id})
        
        return {"success": True, "activities": results}
    
    # Convenience methods for common queries
    
    def get_qualified_leads(self, limit: int = 50) -> List[Dict]:
        """Get high-scoring leads ready for outreach."""
        query = """
            SELECT l.*, 
                   u.first_name as owner_first_name,
                   u.last_name as owner_last_name
            FROM leads l
            LEFT JOIN users u ON l.owner_id = u.user_id
            WHERE l.lead_status NOT IN ('Converted', 'Disqualified')
            AND (l.ai_score >= 70 OR l.lead_rating IN ('Hot', 'Warm'))
            ORDER BY l.ai_score DESC NULLS LAST, l.created_at DESC
            LIMIT :limit
        """
        return execute_query(query, {"limit": limit})
    
    def get_stale_leads(self, days: int = 7) -> List[Dict]:
        """Get leads without recent activity."""
        query = """
            SELECT l.*
            FROM leads l
            WHERE l.lead_status NOT IN ('Converted', 'Disqualified')
            AND (
                l.last_contacted_at < NOW() - INTERVAL ':days days'
                OR l.last_contacted_at IS NULL
            )
            ORDER BY l.ai_score DESC NULLS LAST
            LIMIT 50
        """
        return execute_query(query.replace(":days", str(days)), {})
    
    def get_open_opportunities(self, limit: int = 50) -> List[Dict]:
        """Get open opportunities with account info."""
        query = """
            SELECT 
                o.*,
                a.account_name,
                c.first_name || ' ' || c.last_name as contact_name,
                c.email as contact_email
            FROM opportunities o
            LEFT JOIN accounts a ON o.account_id = a.account_id
            LEFT JOIN contacts c ON o.primary_contact_id = c.contact_id
            WHERE o.is_closed = FALSE
            ORDER BY o.amount DESC NULLS LAST
            LIMIT :limit
        """
        return execute_query(query, {"limit": limit})
    
    def log_activity(
        self,
        activity_type: str,
        subject: str,
        related_to_type: str = None,
        related_to_id: str = None,
        description: str = "",
        ai_generated: bool = False
    ) -> Dict:
        """Helper to log an activity."""
        return self._log_activity({
            "activity_type": activity_type,
            "subject": subject,
            "related_to_type": related_to_type,
            "related_to_id": related_to_id,
            "description": description,
            "ai_generated": ai_generated
        })
