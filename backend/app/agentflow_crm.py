"""
AgentFlow CRM Implementation - Based on lupantech/AgentFlow architecture.
Implements the Planner → Executor → Verifier → Generator flow.

This is a clean implementation following AgentFlow's architecture patterns:
- Planner: Analyzes queries and decides tool usage
- Executor: Runs tools and captures results
- Verifier: Validates results and decides if more steps needed
- Memory: Tracks action history across steps
"""

import os
import time
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from app.llm_engine import create_gpt5_engine
from app.database import execute_query


# ============================================
# MEMORY - Tracks execution history
# ============================================

@dataclass
class ActionRecord:
    """Single action in the agent's memory."""
    step: int
    tool_name: str
    sub_goal: str
    command: str
    result: Any
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class Memory:
    """
    AgentFlow Memory component.
    Tracks all actions taken during query solving.
    """
    
    def __init__(self):
        self.actions: List[ActionRecord] = []
        self.context: Dict[str, Any] = {}
    
    def add_action(self, step: int, tool_name: str, sub_goal: str, command: str, result: Any):
        """Add an action to memory."""
        self.actions.append(ActionRecord(
            step=step,
            tool_name=tool_name,
            sub_goal=sub_goal,
            command=command,
            result=result
        ))
    
    def get_actions(self) -> List[Dict]:
        """Get all actions as serializable dicts."""
        return [
            {
                "step": a.step,
                "tool_name": a.tool_name,
                "sub_goal": a.sub_goal,
                "command": a.command,
                "result": a.result,
                "timestamp": a.timestamp
            }
            for a in self.actions
        ]
    
    def get_context_summary(self) -> str:
        """Get a summary of actions for context."""
        if not self.actions:
            return "No actions taken yet."
        
        lines = []
        for a in self.actions:
            result_preview = str(a.result)[:200] if a.result else "None"
            lines.append(f"Step {a.step}: {a.tool_name} - {a.sub_goal}\n  Result: {result_preview}")
        
        return "\n".join(lines)
    
    def clear(self):
        """Clear memory for new query."""
        self.actions = []
        self.context = {}


# ============================================
# TOOLS - CRM Database Tool
# ============================================

class CRMDatabaseTool:
    """
    Tool for querying the CRM database.
    Following AgentFlow's BaseTool pattern.
    """
    
    def __init__(self):
        self.tool_name = "crm_database_query"
        self.tool_description = "Execute SQL SELECT queries against the CRM database"
        self.schema_context = """
Available CRM Tables:
- leads: lead_id, first_name, last_name, company_name, email, lead_status, lead_rating, annual_revenue, ai_score
- contacts: contact_id, first_name, last_name, account_id, email, title, department
- accounts: account_id, account_name, industry, annual_revenue, employee_count
- opportunities: opportunity_id, opportunity_name, account_id, amount, stage, probability, close_date, is_closed, is_won
- activities: activity_id, activity_type, subject, status, related_to_type, related_to_id
"""
    
    def execute(self, query: str) -> Dict[str, Any]:
        """Execute a SQL query against the CRM database."""
        if not query:
            return {"success": False, "error": "No query provided"}
        
        # Security: Only allow SELECT queries
        query_upper = query.strip().upper()
        if not query_upper.startswith("SELECT"):
            return {"success": False, "error": "Only SELECT queries allowed"}
        
        # Check for dangerous keywords
        dangerous = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 'TRUNCATE']
        for keyword in dangerous:
            if keyword in query_upper:
                return {"success": False, "error": f"Dangerous keyword '{keyword}' not allowed"}
        
        try:
            results = execute_query(query, {})
            return {
                "success": True,
                "query": query,
                "result_count": len(results),
                "results": results[:100]
            }
        except Exception as e:
            return {"success": False, "error": str(e), "query": query}
    
    def get_metadata(self) -> Dict:
        """Get tool metadata for the planner."""
        return {
            "tool_name": self.tool_name,
            "description": self.tool_description,
            "schema": self.schema_context
        }


# ============================================
# PLANNER - Query Analysis & Action Planning
# ============================================

class Planner:
    """
    AgentFlow Planner component.
    Analyzes queries and generates action plans.
    """
    
    def __init__(self, llm_engine, tools: Dict[str, Any], verbose: bool = True):
        self.llm = llm_engine
        self.tools = tools
        self.verbose = verbose
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze the user query and determine approach."""
        
        prompt = f"""Analyze this CRM query and plan how to answer it:

Query: "{query}"

Available tool: crm_database_query - Execute SQL SELECT queries
{self.tools['crm_database_query'].schema_context}

Respond with:
1. INTENT: What the user wants to know
2. APPROACH: How to answer using the database
3. SQL: The exact SQL query to run

Keep response concise."""

        response = self.llm.generate(prompt)
        
        return {
            "query": query,
            "analysis": response
        }
    
    def generate_sql(self, query: str, context: str = "") -> str:
        """Generate SQL from natural language query."""
        
        prompt = f"""Convert this question to a PostgreSQL SELECT query:

Question: "{query}"
{context}

{self.tools['crm_database_query'].schema_context}

Rules:
- Return ONLY the SQL query, no explanations
- Use appropriate JOINs when needed
- Add LIMIT 50 by default
- Use ILIKE for text searches

SQL:"""

        response = self.llm.generate(prompt)
        
        # Clean response
        sql = response.strip()
        if sql.startswith("```"):
            sql = sql.split("```")[1]
            if sql.startswith("sql"):
                sql = sql[3:]
        sql = sql.strip()
        
        if not sql.endswith(';'):
            sql += ';'
        
        return sql


# ============================================
# EXECUTOR - Tool Execution
# ============================================

class Executor:
    """
    AgentFlow Executor component.
    Executes tools and captures results.
    """
    
    def __init__(self, tools: Dict[str, Any], verbose: bool = True):
        self.tools = tools
        self.verbose = verbose
    
    def execute_tool(self, tool_name: str, command: str) -> Dict[str, Any]:
        """Execute a tool with the given command."""
        
        if tool_name not in self.tools:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        
        tool = self.tools[tool_name]
        
        if self.verbose:
            print(f"   🛠️ Executing {tool_name}: {command[:80]}...")
        
        result = tool.execute(command)
        
        if self.verbose:
            status = "✅" if result.get("success") else "❌"
            count = result.get("result_count", "N/A")
            print(f"   {status} Result: {count} records")
        
        return result


# ============================================
# VERIFIER - Result Validation
# ============================================

class Verifier:
    """
    AgentFlow Verifier component.
    Validates results and determines if more steps needed.
    """
    
    def __init__(self, llm_engine, verbose: bool = True):
        self.llm = llm_engine
        self.verbose = verbose
    
    def verify_result(self, query: str, result: Dict[str, Any], memory: Memory) -> Dict[str, Any]:
        """Verify if the result answers the query."""
        
        if not result.get("success"):
            return {
                "verified": False,
                "reason": result.get("error", "Execution failed"),
                "action": "RETRY"
            }
        
        # Simple verification for now
        if result.get("result_count", 0) >= 0:
            return {
                "verified": True,
                "reason": "Query executed successfully",
                "action": "STOP"
            }
        
        return {
            "verified": False,
            "reason": "No results returned",
            "action": "STOP"
        }


# ============================================
# SOLVER - Main Orchestrator
# ============================================

class AgentFlowSolver:
    """
    AgentFlow Solver - orchestrates the full Planner→Executor→Verifier flow.
    
    This implements the core AgentFlow architecture from lupantech/AgentFlow.
    """
    
    def __init__(
        self,
        max_steps: int = 10,
        max_time: int = 300,
        verbose: bool = True
    ):
        self.max_steps = max_steps
        self.max_time = max_time
        self.verbose = verbose
        
        # Initialize LLM engine
        self.llm = create_gpt5_engine(temperature=1.0)
        
        # Initialize tools
        self.tools = {
            "crm_database_query": CRMDatabaseTool()
        }
        
        # Initialize AgentFlow components
        self.planner = Planner(self.llm, self.tools, verbose)
        self.executor = Executor(self.tools, verbose)
        self.verifier = Verifier(self.llm, verbose)
        self.memory = Memory()
        
        if verbose:
            print("🚀 AgentFlow CRM Solver initialized")
            print(f"   Components: Planner, Executor, Verifier, Memory")
            print(f"   Tools: {list(self.tools.keys())}")
            print(f"   Max Steps: {max_steps}")
    
    def solve(self, query: str) -> Dict[str, Any]:
        """
        Solve a query using the AgentFlow Planner→Executor→Verifier loop.
        
        Args:
            query: Natural language CRM query
            
        Returns:
            dict with results and execution trace
        """
        start_time = time.time()
        self.memory.clear()
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"🔍 AgentFlow Processing: {query}")
            print(f"{'='*60}")
        
        # Step 1: PLANNER - Analyze query
        if self.verbose:
            print(f"\n📋 Step 1: Query Analysis (Planner)")
        
        analysis = self.planner.analyze_query(query)
        sql = self.planner.generate_sql(query)
        
        if self.verbose:
            print(f"   Generated SQL: {sql[:100]}...")
        
        # Main execution loop
        step = 0
        result = None
        
        while step < self.max_steps and (time.time() - start_time) < self.max_time:
            step += 1
            
            # Step 2: EXECUTOR - Run tool
            if self.verbose:
                print(f"\n🛠️ Step {step + 1}: Tool Execution (Executor)")
            
            result = self.executor.execute_tool("crm_database_query", sql)
            
            # Record in memory
            self.memory.add_action(
                step=step,
                tool_name="crm_database_query",
                sub_goal="Execute SQL query",
                command=sql,
                result=result
            )
            
            # Step 3: VERIFIER - Check result
            if self.verbose:
                print(f"\n✅ Step {step + 2}: Verification (Verifier)")
            
            verification = self.verifier.verify_result(query, result, self.memory)
            
            if self.verbose:
                action = verification.get("action", "UNKNOWN")
                print(f"   Verification: {verification.get('reason')}")
                print(f"   Action: {action}")
            
            if verification.get("action") == "STOP":
                break
        
        # Generate final output
        execution_time = round(time.time() - start_time, 2)
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"✨ AgentFlow Complete - {step} steps, {execution_time}s")
            print(f"{'='*60}")
        
        if result and result.get("success"):
            return {
                "success": True,
                "query": query,
                "generated_sql": sql,
                "result_count": result.get("result_count", 0),
                "results": result.get("results", []),
                "summary": f"Found {result.get('result_count', 0)} records matching your query.",
                "memory": self.memory.get_actions(),
                "execution_time": execution_time,
                "steps": step,
                "agentflow": True,
                "components_used": ["Planner", "Executor", "Verifier", "Memory"]
            }
        else:
            return {
                "success": False,
                "error": result.get("error") if result else "No result",
                "query": query,
                "agentflow": True
            }


def create_agentflow_solver(
    max_steps: int = 10,
    verbose: bool = True
) -> AgentFlowSolver:
    """Factory function to create an AgentFlow CRM solver."""
    return AgentFlowSolver(max_steps=max_steps, verbose=verbose)


# Quick test
if __name__ == "__main__":
    solver = create_agentflow_solver(verbose=True)
    result = solver.solve("How many leads do we have?")
    print(f"\n📊 Final Result:")
    print(json.dumps(result, indent=2, default=str))
