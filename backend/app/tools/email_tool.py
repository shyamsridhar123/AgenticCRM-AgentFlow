"""
Email Tool for Agentic CRM.
Adapted for existing schema.
"""

from typing import Any, Dict, List, Optional
import json
from datetime import datetime

from app.llm_engine import create_azure_engine
from app.database import execute_query, execute_write


class EmailTool:
    """
    Custom AgentFlow tool for AI-powered email operations.
    """
    
    name = "email_tool"
    description = """
    Email operations including:
    - Draft personalized emails using AI
    - Summarize email threads
    - Schedule automated follow-ups
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.llm = create_azure_engine(temperature=0.7)
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute email operation."""
        
        operation = params.get("operation", "draft")
        
        if self.verbose:
            print(f"✉️ EmailTool: Executing {operation}")
        
        operations = {
            "draft": self._draft_email,
            "summarize": self._summarize_thread,
        }
        
        handler = operations.get(operation)
        if not handler:
            return {"success": False, "error": f"Unknown operation: {operation}"}
        
        try:
            return handler(params)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _draft_email(self, params: Dict) -> Dict:
        """Draft a personalized email using AI."""
        
        contact_id = params.get("contact_id")
        email_type = params.get("email_type", "followup")
        context = params.get("context", "")
        
        # Get contact info if provided
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
        
        # Build prompt
        system_prompt = f"""You are a professional sales email writer.
Write a {email_type} email that is:
- Professional but personable
- Concise (under 150 words)
- Has a clear call-to-action
- Avoids spam triggers

Return JSON with keys: subject, body"""

        prompt = f"""
Email Type: {email_type}
Contact: {contact.get('first_name', 'there') if contact else 'there'} {contact.get('last_name', '') if contact else ''}
Company: {contact.get('account_name', 'Unknown') if contact else 'Unknown'}
Title: {contact.get('title', '') if contact else ''}
Industry: {contact.get('industry', '') if contact else ''}

Additional Context:
{context}
"""

        response = self.llm.generate(prompt, system_prompt=system_prompt)
        
        try:
            email = json.loads(response)
        except json.JSONDecodeError:
            # Parse response manually
            lines = response.strip().split('\n')
            subject = lines[0] if lines else f"{email_type.title()} Email"
            body = '\n'.join(lines[1:]) if len(lines) > 1 else response
            email = {"subject": subject, "body": body}
        
        return {
            "success": True,
            "email": {
                "subject": email.get("subject", ""),
                "body": email.get("body", ""),
                "to": contact.get("email", "") if contact else "",
                "contact_name": f"{contact.get('first_name', '')} {contact.get('last_name', '')}" if contact else ""
            },
            "email_type": email_type
        }
    
    def _summarize_thread(self, params: Dict) -> Dict:
        """Summarize email conversation with a contact."""
        
        contact_id = params.get("contact_id")
        
        if not contact_id:
            return {"success": False, "error": "contact_id required"}
        
        # Get email messages
        query = """
            SELECT em.* FROM email_messages em
            JOIN email_threads et ON em.thread_id = et.id
            WHERE et.contact_id = :contact_id
            ORDER BY em.sent_at DESC
            LIMIT 20
        """
        messages = execute_query(query, {"contact_id": contact_id})
        
        if not messages:
            return {
                "success": True,
                "summary": "No email history found for this contact.",
                "message_count": 0
            }
        
        # Summarize with AI
        system_prompt = """Summarize this email thread including:
1. Key topics discussed
2. Current status/sentiment
3. Next steps mentioned
Return JSON with keys: summary, key_topics, sentiment, next_steps"""

        thread_text = "\n\n---\n\n".join([
            f"From: {m.get('from_email')}\nSubject: {m.get('subject')}\n{m.get('body_text', '')}"
            for m in messages[:10]
        ])
        
        response = self.llm.generate(thread_text, system_prompt=system_prompt)
        
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            result = {"summary": response}
        
        return {
            "success": True,
            "message_count": len(messages),
            "summary": result.get("summary", response),
            "key_topics": result.get("key_topics", []),
            "sentiment": result.get("sentiment", "neutral"),
            "next_steps": result.get("next_steps", [])
        }
