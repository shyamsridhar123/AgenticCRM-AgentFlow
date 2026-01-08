"""
Natural Language Query Agent.
Translates natural language questions into database queries.
Adapted for existing CRM schema.
"""

from typing import Any, Dict, List, Optional
import json
import re

from app.llm_engine import create_gpt5_engine
from app.database import execute_query, execute_write


class NLQueryAgent:
    """
    AI Agent for natural language database queries.
    Uses GPT-5 Pro for accurate SQL generation.
    """
    
    # Schema context for the LLM - matches existing database
    SCHEMA_CONTEXT = """
Available Tables and Columns:

leads: lead_id (UUID PK), first_name, last_name, company_name, title, email, phone, mobile,
       lead_source, lead_status (New/Contacted/Qualified/Disqualified/Converted), lead_rating (Hot/Warm/Cold),
       industry, annual_revenue, employee_count, owner_id, is_converted, ai_score (0-100), ai_qualification,
       created_at, updated_at

contacts: contact_id (UUID PK), first_name, last_name, full_name (computed), title, department,
          account_id (FK), email, phone_business, phone_mobile, lead_source, status, created_at

accounts: account_id (UUID PK), account_name, account_number, account_type, industry, annual_revenue,
          employee_count, website, phone, billing_city, billing_country, owner_id, status, created_at

opportunities: opportunity_id (UUID PK), opportunity_name, account_id (FK), primary_contact_id (FK),
               amount, probability (0-100), expected_revenue (computed), stage, type, lead_source,
               close_date, owner_id, is_closed, is_won, created_at

activities: activity_id (UUID PK), activity_type (Task/Call/Email/Meeting), subject, description,
            status (Open/Completed), priority, due_date, related_to_type (Lead/Contact/Opportunity/Account),
            related_to_id, owner_id, ai_generated, created_at

campaigns: campaign_id, campaign_name, type, status, start_date, end_date, budget, actual_cost

users: user_id, first_name, last_name, email, role, is_active

Key Relationships:
- leads.owner_id -> users.user_id
- contacts.account_id -> accounts.account_id  
- opportunities.account_id -> accounts.account_id
- opportunities.primary_contact_id -> contacts.contact_id
- activities uses polymorphic relation via related_to_type and related_to_id
"""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        # Use temperature=1.0 for O1/GPT-5 class models as they require it
        self.llm = create_gpt5_engine(temperature=1.0)
        self.agent_type = "nl_query"
    
    def query(self, natural_language_query: str, user_id: str = None) -> Dict[str, Any]:
        """
        Process a natural language query and return results.
        """
        
        if self.verbose:
            print(f"🔍 NLQueryAgent: Processing query: {natural_language_query}")
        
        # Step 1: Generate SQL from natural language
        sql_result = self._generate_sql(natural_language_query)
        
        if not sql_result.get("success"):
            return sql_result
        
        sql = sql_result.get("sql")
        
        # Step 2: Validate and sanitize SQL
        validation = self._validate_sql(sql)
        
        if not validation.get("safe"):
            return {
                "success": False,
                "error": "Query contains unsafe operations",
                "details": validation.get("issues", [])
            }
        
        # Step 3: Execute the query
        try:
            results = execute_query(sql, {})
            result_count = len(results)
        except Exception as e:
            self._log_query(natural_language_query, sql, None, False, str(e), user_id)
            return {
                "success": False,
                "error": f"Query execution failed: {str(e)}",
                "generated_sql": sql
            }
        
        # Step 4: Generate human-readable summary
        summary = self._generate_summary(natural_language_query, results)
        
        # Log successful query
        self._log_query(natural_language_query, sql, result_count, True, None, user_id)
        
        return {
            "success": True,
            "query": natural_language_query,
            "generated_sql": sql,
            "result_count": result_count,
            "results": results[:100],
            "summary": summary
        }
    
    def _generate_sql(self, query: str) -> Dict[str, Any]:
        """Generate SQL from natural language using GPT-5 Pro with fallback."""
        
        # First try LLM-based generation
        system_prompt = f"""You are an expert SQL query generator for a CRM database.
Convert the user's natural language question into a PostgreSQL SELECT query.

{self.SCHEMA_CONTEXT}

Rules:
1. ONLY generate SELECT queries - no INSERT, UPDATE, DELETE, DROP, etc.
2. Always use table aliases for clarity
3. Include appropriate JOINs when data spans multiple tables
4. Add reasonable LIMIT (default 50) unless user asks for all
5. Use ILIKE for text searches to be case-insensitive
6. For date ranges, use appropriate PostgreSQL date functions
7. Return ONLY the SQL query, no explanations
8. If the query is ambiguous or cannot be answered, return: UNABLE: <reason>
"""

        prompt = f"Convert to SQL: {query}"
        
        response = self.llm.generate(prompt, system_prompt=system_prompt)
        
        if self.verbose:
            print(f"🤖 LLM Response: {response[:200]}...")
        
        # Check if LLM failed or returned error
        if response is None or "[LLM Unavailable" in response or "Error" in response or response.strip().startswith("UNABLE:"):
            if self.verbose:
                print(f"⚠️ LLM failed, trying fallback for: {query}")
            # Try fallback pattern matching
            fallback_sql = self._fallback_sql_generation(query)
            if fallback_sql:
                if self.verbose:
                    print(f"✅ Fallback SQL: {fallback_sql}")
                return {"success": True, "sql": fallback_sql, "fallback": True}
            return {
                "success": False,
                "error": "LLM unavailable and no matching fallback pattern"
            }
        
        sql = self._clean_sql(response)
        
        if self.verbose:
            print(f"✅ Generated SQL: {sql}")
        
        return {"success": True, "sql": sql}
    
    def _fallback_sql_generation(self, query: str) -> Optional[str]:
        """Generate SQL using pattern matching when LLM is unavailable."""
        
        query_lower = query.lower()
        
        # Pattern: "show me all leads" or "list leads"
        if 'lead' in query_lower and ('show' in query_lower or 'list' in query_lower or 'all' in query_lower):
            if 'hot' in query_lower:
                return "SELECT * FROM leads WHERE lead_rating = 'Hot' ORDER BY created_at DESC LIMIT 50;"
            if 'qualified' in query_lower:
                return "SELECT * FROM leads WHERE lead_status = 'Qualified' ORDER BY created_at DESC LIMIT 50;"
            return "SELECT * FROM leads ORDER BY created_at DESC LIMIT 50;"
        
        # Pattern: "show opportunities" or "deals"
        if 'opportunit' in query_lower or 'deal' in query_lower:
            if 'top' in query_lower:
                return "SELECT * FROM opportunities WHERE is_closed = FALSE ORDER BY amount DESC NULLS LAST LIMIT 10;"
            return "SELECT * FROM opportunities WHERE is_closed = FALSE ORDER BY amount DESC NULLS LAST LIMIT 50;"
        
        # Pattern: "show contacts"
        if 'contact' in query_lower:
            return """SELECT c.*, a.account_name FROM contacts c 
                      LEFT JOIN accounts a ON c.account_id = a.account_id 
                      ORDER BY c.created_at DESC LIMIT 50;"""
        
        # Pattern: "show accounts"
        if 'account' in query_lower or 'compan' in query_lower:
            return "SELECT * FROM accounts ORDER BY annual_revenue DESC NULLS LAST LIMIT 50;"
        
        # Pattern: "pipeline" or "stage"
        if 'pipeline' in query_lower or 'stage' in query_lower:
            return """SELECT stage, COUNT(*) as count, SUM(amount) as total_value 
                      FROM opportunities WHERE is_closed = FALSE 
                      GROUP BY stage ORDER BY count DESC;"""
        
        # Pattern: "activities"
        if 'activit' in query_lower:
            return "SELECT * FROM activities ORDER BY created_at DESC LIMIT 50;"
        
        return None
    
    def _clean_sql(self, sql: str) -> str:
        """Clean and normalize the generated SQL."""
        sql = re.sub(r'```sql\s*', '', sql)
        sql = re.sub(r'```\s*', '', sql)
        sql = sql.strip()
        if not sql.endswith(';'):
            sql += ';'
        return sql
    
    def _validate_sql(self, sql: str) -> Dict[str, Any]:
        """Validate SQL for safety."""
        if not sql:
            return {"safe": False, "issues": ["No SQL provided"]}
        
        # Clean and normalize
        sql_clean = sql.strip()
        sql_upper = sql_clean.upper()
        issues = []
        
        if self.verbose:
            print(f"🔍 Validating SQL: {sql_clean[:100]}...")
        
        dangerous = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 
                    'TRUNCATE', 'EXEC', 'EXECUTE', 'GRANT', 'REVOKE']
        
        for keyword in dangerous:
            # Check for dangerous keywords with word boundaries
            if f" {keyword} " in f" {sql_upper} " or sql_upper.startswith(keyword):
                issues.append(f"Dangerous keyword found: {keyword}")
        
        # Check if it starts with SELECT (after removing common prefixes)
        sql_check = sql_upper.lstrip()
        if not sql_check.startswith('SELECT'):
            issues.append(f"Query must start with SELECT, got: {sql_check[:30]}...")
        
        if self.verbose and issues:
            print(f"⚠️ Validation issues: {issues}")
        
        return {"safe": len(issues) == 0, "issues": issues}
    
    def _generate_summary(self, query: str, results: List[Dict]) -> str:
        """Generate a human-readable summary."""
        
        if not results:
            return "No results found for your query."
        
        count = len(results)
        
        if count <= 10:
            system_prompt = """Summarize these CRM query results in 1-2 sentences. 
Be specific about key numbers and insights."""

            prompt = f"Question: {query}\nResults ({count} records):\n{json.dumps(results[:10], indent=2, default=str)}"
            return self.llm.generate(prompt, system_prompt=system_prompt, max_tokens=150)
        
        return f"Found {count} records matching your query. Showing first 100 results."
    
    def _log_query(self, query_text: str, sql: str, result_count: Optional[int],
                   success: bool, error: Optional[str], user_id: Optional[str]):
        """Log the query for analytics."""
        
        execute_write("""
            INSERT INTO nl_queries (query_text, generated_sql, result_count, user_id, success, error_message)
            VALUES (:query, :sql, :count, CAST(:user AS UUID), :success, :error)
        """, {
            "query": query_text,
            "sql": sql,
            "count": result_count,
            "user": user_id,
            "success": success,
            "error": error
        })
    
    def get_example_queries(self) -> List[str]:
        """Return example queries users can try."""
        return [
            "Show me all hot leads from this month",
            "What are the top 10 opportunities by amount?",
            "How many leads came from website source?",
            "List all open opportunities closing this quarter",
            "Find contacts from technology companies",
            "Show leads with ai_score above 70",
            "What's the total pipeline value by stage?",
            "List all activities created today",
            "Show accounts in the healthcare industry",
            "Find opportunities with probability over 50%"
        ]
    
    def get_query_history(self, limit: int = 20) -> List[Dict]:
        """Get recent query history."""
        query = """
            SELECT query_text, generated_sql, result_count, success, created_at
            FROM nl_queries
            ORDER BY created_at DESC
            LIMIT :limit
        """
        return execute_query(query, {"limit": limit})
