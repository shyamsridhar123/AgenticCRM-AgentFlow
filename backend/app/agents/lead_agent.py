"""
Lead Scoring and Qualification Agent.
Adapted for existing CRM schema.
"""

from typing import Any, Dict, List, Optional
import json

from app.tools.database_tool import DatabaseTool
from app.tools.ml_tool import MLTool
from app.llm_engine import create_azure_engine
from app.database import execute_query, execute_write


class LeadScoringAgent:
    """
    AI Agent for lead scoring and qualification.
    Uses existing schema: leads table with lead_id, lead_status, lead_rating, etc.
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.db_tool = DatabaseTool(verbose=verbose)
        self.ml_tool = MLTool(verbose=verbose)
        self.llm = create_azure_engine(temperature=0.1)
        self.agent_type = "lead_scoring"
    
    def analyze_and_score(self, lead_id: str) -> Dict[str, Any]:
        """
        Comprehensive lead analysis and scoring.
        """
        if self.verbose:
            print(f"🎯 LeadScoringAgent: Analyzing lead {lead_id}")
        
        # Step 1: Gather lead context
        lead_data = self._gather_lead_context(lead_id)
        
        if not lead_data:
            return {"success": False, "error": "Lead not found"}
        
        # Step 2: Run ML scoring
        score_result = self.ml_tool.execute({
            "operation": "score_lead",
            "lead_id": lead_id
        })
        
        if not score_result.get("success"):
            return score_result
        
        # Step 3: Generate recommendations
        output = self._generate_recommendations(lead_data, score_result)
        
        # Log execution
        self._log_execution(lead_id, score_result, output)
        
        return output
    
    def batch_score_new_leads(self, limit: int = 50) -> Dict[str, Any]:
        """Score all unscored new leads."""
        
        query = """
            SELECT lead_id FROM leads
            WHERE lead_status = 'New' 
            AND (ai_score IS NULL OR ai_score = 0)
            ORDER BY created_at DESC
            LIMIT :limit
        """
        leads = execute_query(query, {"limit": limit})
        
        results = []
        qualified = []
        needs_nurturing = []
        
        for lead in leads:
            result = self.analyze_and_score(str(lead["lead_id"]))
            results.append(result)
            
            if result.get("qualification") == "qualified":
                qualified.append(str(lead["lead_id"]))
            elif result.get("qualification") == "needs_nurturing":
                needs_nurturing.append(str(lead["lead_id"]))
        
        return {
            "success": True,
            "total_scored": len(results),
            "qualified_leads": len(qualified),
            "needs_nurturing": len(needs_nurturing),
            "qualified_lead_ids": qualified,
            "results": results
        }
    
    def auto_route_qualified_leads(self) -> Dict[str, Any]:
        """Automatically assign qualified leads to sales reps."""
        
        query = """
            SELECT l.lead_id, l.ai_score, l.industry, l.annual_revenue
            FROM leads l
            WHERE (l.lead_rating = 'Hot' OR l.ai_score >= 70)
            AND l.owner_id IS NULL
            AND l.lead_status NOT IN ('Converted', 'Disqualified')
            ORDER BY l.ai_score DESC NULLS LAST
            LIMIT 20
        """
        leads = execute_query(query, {})
        
        # Get available users (sales reps)
        users = execute_query("""
            SELECT user_id FROM users WHERE is_active = TRUE LIMIT 5
        """, {})
        
        if not users:
            return {"success": False, "error": "No active users found"}
        
        user_ids = [u["user_id"] for u in users]
        assignments = []
        
        for i, lead in enumerate(leads):
            owner_id = user_ids[i % len(user_ids)]
            
            execute_write("""
                UPDATE leads 
                SET owner_id = :owner, lead_status = 'Contacted', updated_at = NOW() 
                WHERE lead_id = :id
            """, {"owner": owner_id, "id": lead["lead_id"]})
            
            assignments.append({
                "lead_id": str(lead["lead_id"]),
                "assigned_to": str(owner_id),
                "ai_score": lead["ai_score"]
            })
            
            # Log activity
            self.db_tool.log_activity(
                activity_type="Task",
                subject=f"Lead auto-assigned by AI",
                related_to_type="Lead",
                related_to_id=str(lead["lead_id"]),
                ai_generated=True
            )
        
        return {
            "success": True,
            "leads_routed": len(assignments),
            "assignments": assignments
        }
    
    def _gather_lead_context(self, lead_id: str) -> Optional[Dict]:
        """Gather comprehensive lead context."""
        
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
            return None
        
        lead = results[0]
        
        # Get activity history
        activities = execute_query("""
            SELECT activity_type, subject, status, created_at
            FROM activities 
            WHERE related_to_type = 'Lead' AND related_to_id = :lead_id
            ORDER BY created_at DESC LIMIT 10
        """, {"lead_id": lead_id})
        
        lead["activities"] = activities
        
        return lead
    
    def _generate_recommendations(self, lead_data: Dict, score_result: Dict) -> Dict[str, Any]:
        """Generate actionable recommendations."""
        
        score = score_result.get("score", 0)
        qualification = score_result.get("qualification", "unqualified")
        
        recommendations = []
        next_actions = []
        
        if qualification == "qualified":
            recommendations.append("Lead is sales-ready. Assign to rep immediately.")
            next_actions.append({
                "action": "assign_to_rep",
                "priority": "high",
                "deadline": "today"
            })
            
            if (lead_data.get("annual_revenue") or 0) > 1000000:
                next_actions.append({
                    "action": "schedule_discovery_call",
                    "priority": "high",
                    "deadline": "within_48_hours"
                })
        
        elif qualification == "needs_nurturing":
            recommendations.append("Lead shows potential but needs nurturing.")
            next_actions.append({
                "action": "add_to_nurture_campaign",
                "priority": "medium",
                "deadline": "within_week"
            })
        
        else:
            recommendations.append("Lead does not meet qualification criteria.")
        
        return {
            "success": True,
            "lead_id": str(lead_data.get("lead_id", "")),
            "score": score,
            "qualification": qualification,
            "score_breakdown": score_result.get("score_breakdown", {}),
            "ai_reasoning": score_result.get("ai_reasoning", ""),
            "recommendations": recommendations,
            "next_actions": next_actions
        }
    
    def _log_execution(self, lead_id: str, score_result: Dict, output: Dict):
        """Log agent execution."""
        
        execute_write("""
            INSERT INTO agent_logs (
                agent_type, action, input_data, output_data,
                model_used, related_to_type, related_to_id, success
            ) VALUES (
                :agent_type, 'analyze_and_score', :input, :output,
                'gpt-5.2-chat', 'Lead', CAST(:lead_id AS UUID), :success
            )
        """, {
            "agent_type": self.agent_type,
            "input": json.dumps({"lead_id": lead_id}),
            "output": json.dumps({"score": output.get("score"), "qualification": output.get("qualification")}),
            "lead_id": lead_id,
            "success": output.get("success", False)
        })
