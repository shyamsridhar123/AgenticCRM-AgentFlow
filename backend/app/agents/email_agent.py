"""
Email Drafting and Summarization Agent.
Adapted for existing CRM schema.
"""

from typing import Any, Dict, List, Optional
import json

from app.tools.email_tool import EmailTool
from app.tools.database_tool import DatabaseTool
from app.llm_engine import create_azure_engine
from app.database import execute_query, execute_write


class EmailAgent:
    """
    AI Agent for intelligent email composition.
    Uses existing schema: contacts, accounts.
    """
    
    EMAIL_TYPES = ["initial_outreach", "followup", "re_engagement", "proposal", "thank_you"]
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.email_tool = EmailTool(verbose=verbose)
        self.db_tool = DatabaseTool(verbose=verbose)
        self.llm = create_azure_engine(temperature=0.7)
        self.agent_type = "email"
    
    def draft_email(
        self,
        contact_id: str,
        email_type: str = "followup",
        opportunity_id: str = None,
        custom_context: str = ""
    ) -> Dict[str, Any]:
        """Draft a personalized email for a contact."""
        
        if self.verbose:
            print(f"✉️ EmailAgent: Drafting {email_type} email for contact {contact_id}")
        
        context = self._build_email_context(contact_id, opportunity_id, custom_context)
        
        result = self.email_tool.execute({
            "operation": "draft",
            "contact_id": contact_id,
            "email_type": email_type,
            "context": json.dumps(context)
        })
        
        if result.get("success"):
            alternatives = self._generate_subject_alternatives(
                result.get("email", {}).get("subject", ""),
                email_type
            )
            result["subject_alternatives"] = alternatives
            self._log_execution("draft", contact_id, result)
        
        return result
    
    def summarize_conversation(self, contact_id: str) -> Dict[str, Any]:
        """Summarize all email conversations with a contact."""
        
        if self.verbose:
            print(f"📋 EmailAgent: Summarizing conversations for contact {contact_id}")
        
        result = self.email_tool.execute({
            "operation": "summarize",
            "contact_id": contact_id
        })
        
        if result.get("success"):
            recommendation = self._recommend_next_email(result)
            result["next_email_recommendation"] = recommendation
        
        return result
    
    def generate_sequence(
        self,
        contact_id: str,
        sequence_type: str = "nurture",
        email_count: int = 5
    ) -> Dict[str, Any]:
        """Generate a complete email sequence for a contact."""
        
        if self.verbose:
            print(f"📧 EmailAgent: Generating {sequence_type} sequence")
        
        contact = self._get_contact_context(contact_id)
        if not contact:
            return {"success": False, "error": "Contact not found"}
        
        stages = ["intro", "value_prop", "social_proof", "urgency", "break_up"][:email_count]
        sequence = []
        
        for i, stage in enumerate(stages):
            email = self._generate_sequence_email(contact, stage, i + 1, email_count)
            sequence.append({
                "order": i + 1,
                "stage": stage,
                "delay_days": [0, 3, 5, 7, 10][i] if i < 5 else i * 3,
                "email": email
            })
        
        return {
            "success": True,
            "sequence_type": sequence_type,
            "contact_id": contact_id,
            "email_count": len(sequence),
            "sequence": sequence
        }
    
    def analyze_email_performance(self, days: int = 30) -> Dict[str, Any]:
        """Analyze email performance metrics."""
        
        query = f"""
            SELECT 
                DATE(sent_at) as date,
                COUNT(*) as sent,
                COUNT(opened_at) as opened,
                COUNT(clicked_at) as clicked
            FROM email_messages
            WHERE sent_at >= NOW() - INTERVAL '{days} days'
            GROUP BY DATE(sent_at)
            ORDER BY date DESC
        """
        daily_stats = execute_query(query, {})
        
        total_sent = sum(d.get("sent", 0) for d in daily_stats)
        total_opened = sum(d.get("opened", 0) for d in daily_stats)
        
        return {
            "success": True,
            "period_days": days,
            "summary": {
                "total_sent": total_sent,
                "open_rate": round((total_opened / total_sent * 100) if total_sent > 0 else 0, 1)
            },
            "daily_stats": daily_stats
        }
    
    def _build_email_context(self, contact_id: str, opportunity_id: Optional[str], custom: str) -> Dict:
        """Build context for email generation."""
        
        context = {"custom_instructions": custom}
        
        contact = self._get_contact_context(contact_id)
        if contact:
            context["contact"] = {
                "name": f"{contact.get('first_name', '')} {contact.get('last_name', '')}",
                "title": contact.get("title"),
                "company": contact.get("account_name"),
                "industry": contact.get("industry")
            }
        
        if opportunity_id:
            opp = execute_query(
                "SELECT * FROM opportunities WHERE opportunity_id = :id",
                {"id": opportunity_id}
            )
            if opp:
                context["opportunity"] = {
                    "name": opp[0].get("opportunity_name"),
                    "stage": opp[0].get("stage"),
                    "amount": opp[0].get("amount")
                }
        
        return context
    
    def _get_contact_context(self, contact_id: str) -> Optional[Dict]:
        """Get contact details."""
        
        query = """
            SELECT c.*, a.account_name, a.industry
            FROM contacts c
            LEFT JOIN accounts a ON c.account_id = a.account_id
            WHERE c.contact_id = :id
        """
        results = execute_query(query, {"id": contact_id})
        return results[0] if results else None
    
    def _generate_subject_alternatives(self, original: str, email_type: str) -> List[str]:
        """Generate alternative subject lines."""
        
        prompt = f"Generate 3 alternative subject lines for a {email_type} email. Original: {original}"
        response = self.llm.generate(prompt, max_tokens=100)
        return [l.strip() for l in response.split("\n") if l.strip()][:3]
    
    def _recommend_next_email(self, summary: Dict) -> Dict:
        """Recommend the next email type."""
        
        sentiment = summary.get("sentiment", "neutral")
        
        if sentiment == "positive":
            return {"type": "proposal", "reason": "Positive engagement suggests readiness"}
        elif sentiment == "negative":
            return {"type": "value_add", "reason": "Address concerns with value"}
        else:
            return {"type": "followup", "reason": "Maintain engagement"}
    
    def _generate_sequence_email(self, contact: Dict, stage: str, order: int, total: int) -> Dict:
        """Generate a single sequence email."""
        
        system_prompt = f"""Generate a {stage} email for a sales sequence.
Email {order} of {total}. Under 150 words. Return as JSON: subject, body"""

        prompt = f"""
Contact: {contact.get('first_name')} {contact.get('last_name')}
Company: {contact.get('account_name')}
"""

        response = self.llm.generate(prompt, system_prompt=system_prompt)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"subject": f"{stage.title()} Email", "body": response}
    
    def _log_execution(self, action: str, contact_id: str, result: Dict):
        """Log agent execution."""
        
        execute_write("""
            INSERT INTO agent_logs (
                agent_type, action, input_data, output_data,
                model_used, related_to_type, related_to_id, success
            ) VALUES (
                :agent_type, :action, :input, :output,
                'gpt-5.2-chat', 'Contact', CAST(:contact_id AS UUID), :success
            )
        """, {
            "agent_type": self.agent_type,
            "action": action,
            "input": json.dumps({"contact_id": contact_id}),
            "output": json.dumps({"email_drafted": True}),
            "contact_id": contact_id,
            "success": result.get("success", False)
        })
