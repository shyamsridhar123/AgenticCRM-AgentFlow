"""
Pipeline Prediction Agent.
Adapted for existing CRM schema.
"""

from typing import Any, Dict, List
from datetime import datetime
import json

from app.tools.ml_tool import MLTool
from app.llm_engine import create_gpt5_engine
from app.database import execute_query, execute_write


class PipelineAgent:
    """
    AI Agent for sales pipeline analysis and predictions.
    Uses existing schema: opportunities table.
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.ml_tool = MLTool(verbose=verbose)
        self.llm = create_gpt5_engine(temperature=0.2)
        self.agent_type = "pipeline"
    
    def generate_forecast(self, period_days: int = 90) -> Dict[str, Any]:
        """Generate comprehensive pipeline forecast."""
        
        if self.verbose:
            print(f"📊 PipelineAgent: Generating {period_days}-day forecast...")
        
        # Get current pipeline state
        pipeline_data = self._get_pipeline_data()
        
        # Run ML analysis
        analysis = self.ml_tool.execute({
            "operation": "analyze_pipeline",
            "period_days": period_days
        })
        
        # Generate forecast
        forecast = self._generate_detailed_forecast(pipeline_data, period_days)
        
        # Generate actions
        actions = self._generate_action_plan(pipeline_data, analysis)
        
        self._log_execution("forecast", {"period_days": period_days}, forecast)
        
        return {
            "success": True,
            "period_days": period_days,
            "pipeline_summary": pipeline_data,
            "forecast": forecast,
            "analysis": analysis.get("analysis", {}),
            "recommended_actions": actions
        }
    
    def identify_at_risk_deals(self) -> Dict[str, Any]:
        """Identify deals at risk of being lost."""
        
        if self.verbose:
            print("⚠️ PipelineAgent: Identifying at-risk deals...")
        
        query = """
            SELECT 
                o.*,
                a.account_name,
                c.first_name, c.last_name, c.email,
                EXTRACT(DAY FROM (NOW() - o.updated_at)) as days_stale,
                EXTRACT(DAY FROM (o.close_date - CURRENT_DATE)) as days_to_close,
                (SELECT COUNT(*) FROM activities WHERE related_to_type = 'Opportunity' AND related_to_id = o.opportunity_id) as activity_count
            FROM opportunities o
            LEFT JOIN accounts a ON o.account_id = a.account_id
            LEFT JOIN contacts c ON o.primary_contact_id = c.contact_id
            WHERE o.is_closed = FALSE
            ORDER BY o.amount DESC NULLS LAST
        """
        opportunities = execute_query(query, {})
        
        at_risk = []
        for opp in opportunities:
            risk_factors = self._calculate_risk_factors(opp)
            if risk_factors["risk_score"] >= 6:
                recommendation = self._generate_deal_recommendation(opp, risk_factors)
                at_risk.append({
                    "deal": opp,
                    "risk_factors": risk_factors,
                    "recommendation": recommendation
                })
        
        at_risk.sort(key=lambda x: x["risk_factors"]["risk_score"], reverse=True)
        
        return {
            "success": True,
            "total_deals_analyzed": len(opportunities),
            "at_risk_count": len(at_risk),
            "total_at_risk_value": sum(d["deal"].get("amount", 0) or 0 for d in at_risk),
            "at_risk_deals": at_risk[:20]
        }
    
    def get_pipeline_health_score(self) -> Dict[str, Any]:
        """Calculate overall pipeline health score."""
        
        metrics = self._get_pipeline_metrics()
        scores = {}
        
        # Deal velocity score - convert to float for arithmetic
        avg_age = float(metrics.get("avg_deal_age_days") or 30)
        scores["velocity"] = max(0, min(100, 100 - (avg_age - 14) * 2))
        
        # Coverage score
        coverage = float(metrics.get("pipeline_to_quota_ratio") or 1.0)
        scores["coverage"] = min(100, coverage * 33.33)
        
        # Activity score
        avg_activities = float(metrics.get("avg_activities_per_deal") or 0)
        scores["engagement"] = min(100, avg_activities * 10)
        
        # Win rate score
        win_rate = float(metrics.get("win_rate") or 0.2)
        scores["win_rate"] = win_rate * 100
        
        # Distribution score
        scores["distribution"] = self._calculate_distribution_score(metrics.get("stage_counts", {}))
        
        # Weighted overall
        weights = {"velocity": 0.2, "coverage": 0.25, "engagement": 0.2, "win_rate": 0.25, "distribution": 0.1}
        overall = sum(scores[k] * weights[k] for k in weights)
        
        interpretation = self._interpret_health_score(overall, scores)
        
        return {
            "success": True,
            "overall_score": round(overall, 1),
            "component_scores": scores,
            "interpretation": interpretation,
            "metrics": metrics
        }
    
    def _get_pipeline_data(self) -> Dict:
        """Get current pipeline state."""
        
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
        
        total_query = """
            SELECT 
                COUNT(*) as total_deals,
                SUM(amount) as total_value,
                SUM(amount * probability / 100) as weighted_value
            FROM opportunities
            WHERE is_closed = FALSE
        """
        totals = execute_query(total_query, {})
        
        return {
            "stages": stages,
            "totals": totals[0] if totals else {},
            "generated_at": datetime.now().isoformat()
        }
    
    def _get_pipeline_metrics(self) -> Dict:
        """Get comprehensive pipeline metrics."""
        
        query = """
            SELECT 
                COUNT(DISTINCT opportunity_id) as total_deals,
                AVG(EXTRACT(DAY FROM (NOW() - created_at))) as avg_deal_age_days,
                SUM(amount) as total_pipeline_value,
                AVG(amount) as avg_deal_size,
                AVG(probability) as avg_probability
            FROM opportunities
            WHERE is_closed = FALSE
        """
        metrics = execute_query(query, {})[0]
        
        # Win rate
        win_query = """
            SELECT 
                COUNT(CASE WHEN is_won = TRUE THEN 1 END)::float / 
                NULLIF(COUNT(*), 0) as win_rate
            FROM opportunities
            WHERE is_closed = TRUE
            AND created_at >= NOW() - INTERVAL '90 days'
        """
        win_rate = execute_query(win_query, {})
        metrics["win_rate"] = (win_rate[0].get("win_rate") or 0.2) if win_rate else 0.2
        
        # Activities per deal
        activity_query = """
            SELECT AVG(activity_count) as avg_activities_per_deal FROM (
                SELECT o.opportunity_id, COUNT(a.activity_id) as activity_count
                FROM opportunities o
                LEFT JOIN activities a ON a.related_to_type = 'Opportunity' AND a.related_to_id = o.opportunity_id
                WHERE o.is_closed = FALSE
                GROUP BY o.opportunity_id
            ) sub
        """
        activity_result = execute_query(activity_query, {})
        metrics["avg_activities_per_deal"] = (activity_result[0].get("avg_activities_per_deal") or 0) if activity_result else 0
        
        # Stage counts
        stage_query = """
            SELECT stage, COUNT(*) as count
            FROM opportunities
            WHERE is_closed = FALSE
            GROUP BY stage
        """
        stages = execute_query(stage_query, {})
        metrics["stage_counts"] = {s["stage"]: s["count"] for s in stages}
        
        # Pipeline to quota
        monthly_quota = 500000
        metrics["pipeline_to_quota_ratio"] = ((metrics.get("total_pipeline_value") or 0)) / monthly_quota
        
        return metrics
    
    def _calculate_risk_factors(self, opp: Dict) -> Dict:
        """Calculate risk factors for an opportunity."""
        
        risk_score = 0
        factors = []
        
        days_stale = opp.get("days_stale") or 0
        if days_stale > 14:
            risk_score += 3
            factors.append(f"No activity for {int(days_stale)} days")
        elif days_stale > 7:
            risk_score += 1
        
        days_to_close = opp.get("days_to_close")
        if days_to_close is not None and days_to_close < 0:
            risk_score += 4
            factors.append(f"Past close date by {abs(int(days_to_close))} days")
        elif days_to_close is not None and days_to_close < 7:
            risk_score += 2
            factors.append("Close date approaching")
        
        prob = opp.get("probability") or 50
        if prob < 30:
            risk_score += 2
            factors.append(f"Low probability ({prob}%)")
        
        activity_count = opp.get("activity_count") or 0
        if activity_count < 3:
            risk_score += 2
            factors.append("Minimal engagement")
        
        return {
            "risk_score": min(10, risk_score),
            "factors": factors,
            "severity": "critical" if risk_score >= 8 else "high" if risk_score >= 6 else "medium"
        }
    
    def _generate_deal_recommendation(self, opp: Dict, risk_factors: Dict) -> str:
        """Generate AI recommendation for at-risk deal."""
        
        prompt = f"""
Opportunity: {opp.get('opportunity_name')}
Stage: {opp.get('stage')}
Value: ${opp.get('amount', 0):,.0f}
Risk: {', '.join(risk_factors['factors'])}

Recommend ONE specific action to save this deal (1-2 sentences).
"""
        return self.llm.generate(prompt, max_tokens=100)
    
    def _generate_detailed_forecast(self, pipeline_data: Dict, period_days: int) -> Dict:
        """Generate revenue forecast."""
        
        stages = pipeline_data.get("stages", [])
        
        stage_weights = {
            "Prospecting": 0.1,
            "Qualification": 0.25,
            "Proposal": 0.5,
            "Negotiation": 0.75,
            "Closed Won": 1.0
        }
        
        periods = {"30_days": 0, "60_days": 0, "90_days": 0}
        
        for stage in stages:
            stage_name = stage.get("stage", "")
            value = float(stage.get("total_value") or 0)
            weight = stage_weights.get(stage_name, 0.2)
            
            periods["30_days"] += value * weight * 0.3
            periods["60_days"] += value * weight * 0.5
            periods["90_days"] += value * weight * 0.8
        
        return {
            "expected_revenue": periods,
            "confidence": "medium",
            "total_pipeline": pipeline_data.get("totals", {}).get("total_value", 0),
            "weighted_pipeline": pipeline_data.get("totals", {}).get("weighted_value", 0)
        }
    
    def _generate_action_plan(self, pipeline_data: Dict, analysis: Dict) -> List[Dict]:
        """Generate prioritized action plan."""
        
        actions = []
        totals = pipeline_data.get("totals", {})
        
        if (totals.get("total_deals") or 0) < 10:
            actions.append({
                "priority": "high",
                "action": "Increase lead generation",
                "reason": "Pipeline has insufficient deals"
            })
        
        return actions[:5]
    
    def _calculate_distribution_score(self, stage_counts: Dict) -> float:
        """Calculate pipeline distribution health."""
        
        ideal_ratios = {
            "Prospecting": 0.35,
            "Qualification": 0.30,
            "Proposal": 0.20,
            "Negotiation": 0.15
        }
        
        total = sum(stage_counts.values()) or 1
        actual_ratios = {k: v/total for k, v in stage_counts.items()}
        
        deviation = sum(abs(actual_ratios.get(k, 0) - v) for k, v in ideal_ratios.items())
        
        return max(0, 100 - deviation * 100)
    
    def _interpret_health_score(self, overall: float, components: Dict) -> str:
        """AI interpretation of health score."""
        
        if overall >= 80:
            return "Pipeline is healthy with strong indicators across all dimensions."
        elif overall >= 60:
            weakest = min(components, key=components.get)
            return f"Pipeline is moderately healthy. Focus on improving {weakest.replace('_', ' ')}."
        elif overall >= 40:
            return "Pipeline needs attention. Multiple areas require improvement."
        else:
            return "Pipeline health is critical. Immediate action required."
    
    def _log_execution(self, action: str, input_data: Dict, output_data: Dict):
        """Log agent execution."""
        
        execute_write("""
            INSERT INTO agent_logs (agent_type, action, input_data, output_data, model_used, success)
            VALUES (:agent_type, :action, :input, :output, 'gpt-5-pro', true)
        """, {
            "agent_type": self.agent_type,
            "action": action,
            "input": json.dumps(input_data),
            "output": json.dumps({"summary": "forecast_generated"})
        })
