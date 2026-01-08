"""
ML/Prediction Tool for Agentic CRM.
Uses GPT-5 Pro for sophisticated predictions.
Adapted for existing schema.
"""

from typing import Any, Dict, List
import json

from app.llm_engine import create_gpt5_engine
from app.database import execute_query, execute_write


class MLTool:
    """
    Custom AgentFlow tool for AI-powered predictions using GPT-5 Pro.
    """
    
    name = "ml_tool"
    description = """
    AI-powered predictions including:
    - Lead scoring with detailed breakdowns
    - Opportunity win probability
    - Pipeline forecasting
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.llm = create_gpt5_engine(temperature=0.2)
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute ML operation based on params."""
        
        operation = params.get("operation", "score_lead")
        
        if self.verbose:
            print(f"🤖 MLTool: Executing {operation}")
        
        operations = {
            "score_lead": self._score_lead,
            "predict_opportunity": self._predict_opportunity,
            "analyze_pipeline": self._analyze_pipeline,
        }
        
        handler = operations.get(operation)
        if not handler:
            return {"success": False, "error": f"Unknown operation: {operation}"}
        
        try:
            return handler(params)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _score_lead(self, params: Dict) -> Dict:
        """Score a lead using AI analysis."""
        lead_id = params.get("lead_id")
        
        # Get lead data
        query = """
            SELECT l.*,
                   (SELECT COUNT(*) FROM activities WHERE related_to_type = 'Lead' AND related_to_id = l.lead_id) as activity_count,
                   (SELECT MAX(created_at) FROM activities WHERE related_to_type = 'Lead' AND related_to_id = l.lead_id) as last_activity
            FROM leads l
            WHERE l.lead_id = :lead_id
        """
        results = execute_query(query, {"lead_id": lead_id})
        
        if not results:
            return {"success": False, "error": "Lead not found"}
        
        lead = results[0]
        
        # Calculate base score from rules
        score = self._calculate_base_score(lead)
        
        # Get AI reasoning
        ai_analysis = self._get_ai_lead_analysis(lead)
        
        # Adjust score based on AI
        final_score = min(100, max(0, score + ai_analysis.get("adjustment", 0)))
        
        # Determine qualification
        if final_score >= 70:
            qualification = "qualified"
        elif final_score >= 40:
            qualification = "needs_nurturing"
        else:
            qualification = "unqualified"
        
        # Update lead
        execute_write("""
            UPDATE leads 
            SET ai_score = :score, 
                ai_qualification = :qual,
                ai_score_updated_at = NOW()
            WHERE lead_id = :lead_id
        """, {"score": final_score, "qual": qualification, "lead_id": lead_id})
        
        return {
            "success": True,
            "lead_id": lead_id,
            "score": final_score,
            "qualification": qualification,
            "score_breakdown": {
                "base_score": score,
                "ai_adjustment": ai_analysis.get("adjustment", 0)
            },
            "ai_reasoning": ai_analysis.get("reasoning", "")
        }
    
    def _calculate_base_score(self, lead: Dict) -> int:
        """Calculate base score from lead attributes."""
        score = 30  # Starting score
        
        # Rating
        rating = lead.get("lead_rating", "")
        if rating == "Hot":
            score += 30
        elif rating == "Warm":
            score += 20
        elif rating == "Cold":
            score += 5
        
        # Company size indicators
        revenue = lead.get("annual_revenue") or 0
        if revenue > 10000000:
            score += 15
        elif revenue > 1000000:
            score += 10
        elif revenue > 100000:
            score += 5
        
        employees = lead.get("employee_count") or 0
        if employees > 1000:
            score += 10
        elif employees > 100:
            score += 5
        
        # Engagement
        activity_count = lead.get("activity_count") or 0
        score += min(15, activity_count * 3)
        
        # Has email
        if lead.get("email"):
            score += 5
        
        # Has phone
        if lead.get("phone") or lead.get("mobile"):
            score += 5
        
        return min(100, score)
    
    def _get_ai_lead_analysis(self, lead: Dict) -> Dict:
        """Get AI analysis for lead scoring."""
        
        system_prompt = """Analyze this lead and provide:
1. A score adjustment (-20 to +20)
2. Brief reasoning (1-2 sentences)

Return as JSON: {"adjustment": number, "reasoning": "text"}"""

        lead_summary = f"""
Lead: {lead.get('first_name', '')} {lead.get('last_name', '')}
Company: {lead.get('company_name', 'Unknown')}
Title: {lead.get('title', 'Unknown')}
Industry: {lead.get('industry', 'Unknown')}
Rating: {lead.get('lead_rating', 'None')}
Revenue: ${lead.get('annual_revenue', 0):,.0f}
Employees: {lead.get('employee_count', 0)}
Activities: {lead.get('activity_count', 0)}
Source: {lead.get('lead_source', 'Unknown')}
"""

        response = self.llm.generate(lead_summary, system_prompt=system_prompt)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"adjustment": 0, "reasoning": response}
    
    def _predict_opportunity(self, params: Dict) -> Dict:
        """Predict opportunity outcome."""
        opportunity_id = params.get("opportunity_id")
        
        query = """
            SELECT o.*, a.account_name, a.industry,
                   (SELECT COUNT(*) FROM activities WHERE related_to_type = 'Opportunity' AND related_to_id = o.opportunity_id) as activity_count
            FROM opportunities o
            LEFT JOIN accounts a ON o.account_id = a.account_id
            WHERE o.opportunity_id = :opportunity_id
        """
        results = execute_query(query, {"opportunity_id": opportunity_id})
        
        if not results:
            return {"success": False, "error": "Opportunity not found"}
        
        opp = results[0]
        
        system_prompt = """Analyze this opportunity and predict:
1. Win probability (0-100)
2. Risk factors (list)
3. Recommendation (1 sentence)

Return as JSON: {"probability": number, "risk_factors": [], "recommendation": "text"}"""

        opp_summary = f"""
Opportunity: {opp.get('opportunity_name')}
Stage: {opp.get('stage')}
Amount: ${opp.get('amount', 0):,.0f}
Current Probability: {opp.get('probability', 0)}%
Close Date: {opp.get('close_date')}
Account: {opp.get('account_name')} ({opp.get('industry', 'Unknown')})
Activities: {opp.get('activity_count', 0)}
Days Open: {(opp.get('created_at') and 'calculated') or 'unknown'}
"""

        response = self.llm.generate(opp_summary, system_prompt=system_prompt)
        
        try:
            prediction = json.loads(response)
        except json.JSONDecodeError:
            prediction = {"probability": opp.get("probability", 50), "risk_factors": [], "recommendation": response}
        
        return {
            "success": True,
            "opportunity_id": opportunity_id,
            "prediction": prediction
        }
    
    def _analyze_pipeline(self, params: Dict) -> Dict:
        """Analyze the entire sales pipeline."""
        period_days = params.get("period_days", 90)
        
        # Get pipeline summary
        query = """
            SELECT 
                stage,
                COUNT(*) as count,
                SUM(amount) as total_value,
                AVG(probability) as avg_probability
            FROM opportunities
            WHERE is_closed = FALSE
            GROUP BY stage
        """
        stages = execute_query(query, {})
        
        # Get at-risk opportunities
        at_risk_query = """
            SELECT opportunity_id, opportunity_name, stage, amount, close_date
            FROM opportunities
            WHERE is_closed = FALSE
            AND close_date < CURRENT_DATE
            ORDER BY amount DESC
            LIMIT 10
        """
        at_risk = execute_query(at_risk_query, {})
        
        # Calculate totals
        total_value = sum(s.get("total_value", 0) or 0 for s in stages)
        total_deals = sum(s.get("count", 0) for s in stages)
        
        # Get AI analysis
        system_prompt = """Analyze this pipeline and provide:
1. Overall health score (0-100)
2. Key insight (1 sentence)
3. Top recommendation (1 sentence)

Return as JSON: {"health_score": number, "insight": "text", "recommendation": "text"}"""

        summary = f"""
Pipeline Summary:
Total Value: ${total_value:,.0f}
Total Deals: {total_deals}
Stages: {json.dumps(stages, default=str)}
At-Risk Deals: {len(at_risk)}
"""

        response = self.llm.generate(summary, system_prompt=system_prompt)
        
        try:
            analysis = json.loads(response)
        except json.JSONDecodeError:
            analysis = {"health_score": 70, "insight": response, "recommendation": ""}
        
        return {
            "success": True,
            "period_days": period_days,
            "analysis": analysis,
            "stages": stages,
            "at_risk_count": len(at_risk),
            "total_value": total_value,
            "total_deals": total_deals
        }
