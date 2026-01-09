"""
AgentFlow CRM Solver - Proper implementation using AgentFlow SDK architecture.

This replaces the simplified NL2SQL implementation with the full
AgentFlow Planner → Executor → Verifier → Memory architecture.

Key improvements over the old implementation:
1. Real multi-step reasoning with visible traces
2. Proper tool selection from multiple tools
3. Iterative refinement when results don't make sense
4. Full reasoning traces returned to the UI
5. Uses AgentFlow SDK Memory class directly

The AgentFlow architecture (see /backend/agentflow_sdk/):
- Planner: Analyzes query, generates next steps, selects tools
- Executor: Generates tool commands, executes tools
- Verifier: Checks if the current context answers the query
- Memory: Tracks all actions and results for context (SDK class)
"""

import os
import sys
import time
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# Add SDK path for imports
sdk_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agentflow_sdk", "agentflow", "agentflow")
if sdk_path not in sys.path:
    sys.path.insert(0, sdk_path)

from app.database import execute_query
from app.llm_engine import get_llm_response

# Import SDK Memory class
try:
    from models.memory import Memory as SDKMemory
    SDK_MEMORY_AVAILABLE = True
except ImportError:
    SDK_MEMORY_AVAILABLE = False
    SDKMemory = None


# ============================================
# AGENTFLOW CORE COMPONENTS (using SDK where possible)
# ============================================

class Memory:
    """
    Memory component that tracks all actions and results.
    Extends SDK Memory with additional convenience methods.
    See: agentflow_sdk/agentflow/agentflow/models/memory.py
    """
    def __init__(self):
        # Use SDK Memory if available
        if SDK_MEMORY_AVAILABLE and SDKMemory:
            self._sdk_memory = SDKMemory()
        else:
            self._sdk_memory = None
        
        # Our extended tracking (list format for easier iteration)
        self.actions: List[Dict] = []
        self._query: Optional[str] = None
    
    def set_query(self, query: str) -> None:
        """Store the original query (SDK feature)."""
        self._query = query
        if self._sdk_memory:
            self._sdk_memory.set_query(query)
    
    def get_query(self) -> Optional[str]:
        """Get the stored query."""
        return self._query
    
    def add_action(self, step: int, tool_name: str, sub_goal: str, command: str, result: Any):
        """Add an action to memory."""
        # Add to our list (for easy iteration)
        self.actions.append({
            "step": step,
            "tool": tool_name,
            "sub_goal": sub_goal,
            "command": command,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
        
        # Also add to SDK memory (uses dict format internally)
        if self._sdk_memory:
            self._sdk_memory.add_action(step, tool_name, sub_goal, command, result)
    
    def get_actions(self) -> List[Dict]:
        """Get all actions as a list."""
        return self.actions
    
    def get_sdk_actions(self) -> Dict[str, Dict[str, Any]]:
        """Get actions in SDK format (dict keyed by step name)."""
        if self._sdk_memory:
            return self._sdk_memory.get_actions()
        # Fallback: convert our list to dict
        return {f"Action Step {a['step']}": a for a in self.actions}
    
    def add_file(self, file_name: str, description: Optional[str] = None) -> None:
        """Add a file to memory (SDK feature for multimodal)."""
        if self._sdk_memory:
            self._sdk_memory.add_file(file_name, description)
    
    def get_files(self) -> List[Dict[str, str]]:
        """Get attached files."""
        if self._sdk_memory:
            return self._sdk_memory.get_files()
        return []
    
    def clear(self):
        """Clear all memory."""
        self.actions = []
        self._query = None
        if SDK_MEMORY_AVAILABLE and SDKMemory:
            self._sdk_memory = SDKMemory()
    
    def get_context_string(self) -> str:
        """Format memory for LLM context."""
        if not self.actions:
            return "No previous actions."
        
        parts = []
        for action in self.actions:
            parts.append(f"Step {action['step']}: {action['tool']}")
            parts.append(f"  Goal: {action['sub_goal']}")
            parts.append(f"  Command: {action['command'][:100]}...")
            result_str = json.dumps(action['result'], default=str)[:200]
            parts.append(f"  Result: {result_str}...")
        return "\n".join(parts)


class Planner:
    """
    Planner component that analyzes queries and generates next steps.
    See: agentflow_sdk/agentflow/agentflow/models/planner.py
    """
    def __init__(self, toolbox_metadata: Dict, available_tools: List[str], verbose: bool = True):
        self.toolbox_metadata = toolbox_metadata
        self.available_tools = available_tools
        self.verbose = verbose
    
    def analyze_query(self, query: str, image_path: Optional[str] = None) -> str:
        """Analyze the user query to understand intent."""
        tools_desc = "\n".join([
            f"- {name}: {meta['tool_description']}"
            for name, meta in self.toolbox_metadata.items()
        ])
        
        prompt = f"""You are analyzing a CRM query to understand what the user wants.

Query: {query}

Available Tools:
{tools_desc}

Analyze this query:
1. What is the user trying to accomplish?
2. What data do they need?
3. Which tools would be most helpful?
4. What is the expected output format?

Assume reasonable defaults for any unspecified parameters:
- Time range: default to all time unless specified
- Status: include all statuses unless specified
- Limit: use sensible defaults (e.g., top 10, top 50)

Provide a concise analysis and proceed with the query:"""

        return get_llm_response(prompt, max_tokens=500)
    
    def is_query_ambiguous(self, query: str, analysis: str) -> Tuple[bool, str]:
        """Check if query is too vague to process and generate clarifying response.
        
        IMPORTANT: Be conservative - only flag truly vague queries that have no clear intent.
        Clear database queries like 'top 10 opportunities by amount' should NEVER be flagged.
        """
        # Only flag truly vague patterns with no actionable intent
        vague_patterns = [
            "what does this mean",
            "what is this",
            "explain this",
            "help me understand",
            "i don't get it",
            "what happened",
            "huh",
            "???"
        ]
        
        query_lower = query.lower().strip()
        
        # Only flag if the query is VERY short (under 5 words) AND matches a vague pattern
        # AND doesn't contain any CRM-related keywords
        crm_keywords = ['lead', 'contact', 'account', 'opportunity', 'deal', 'pipeline', 
                        'revenue', 'sales', 'activity', 'campaign', 'top', 'show', 'list',
                        'find', 'get', 'what', 'how many', 'total', 'count', 'amount']
        
        has_crm_keyword = any(kw in query_lower for kw in crm_keywords)
        is_short = len(query.split()) < 5
        matches_vague = any(pattern in query_lower for pattern in vague_patterns)
        
        # Only flag if it's vague, short, AND has no CRM keywords
        is_vague = matches_vague and is_short and not has_crm_keyword
        
        if is_vague:
            clarifying_response = self._generate_clarifying_response(query)
            return True, clarifying_response
        
        return False, ""
    
    def _generate_clarifying_response(self, query: str) -> str:
        """Generate a helpful response asking for clarification."""
        prompt = f"""The user asked a vague question that needs clarification: "{query}"

This is a CRM (Customer Relationship Management) system. Generate a helpful, friendly response that:
1. Acknowledges their question
2. Explains what information you need to help them
3. Provides 2-3 example questions they could ask

Available CRM capabilities:
- Query leads, contacts, accounts, opportunities, activities
- Get pipeline value and analytics
- Analyze conversion rates and win rates
- Search and filter CRM data

Keep the response concise and helpful:"""

        return get_llm_response(prompt, max_tokens=300)
    
    def generate_next_step(
        self, query: str, image_path: Optional[str], query_analysis: str,
        memory: Memory, step_count: int, max_steps: int, json_data: Dict
    ) -> str:
        """Generate the next step to take."""
        tools_desc = "\n".join([
            f"- {name}: {meta['tool_description']}\n  Demo: {meta.get('demo_commands', [])[:1]}"
            for name, meta in self.toolbox_metadata.items()
        ])
        
        memory_context = memory.get_context_string()
        
        prompt = f"""You are a CRM agent deciding the next action to take.

Original Query: {query}
Query Analysis: {query_analysis}

Previous Actions:
{memory_context}

Available Tools (YOU MUST CHOOSE ONE):
{tools_desc}

Current Step: {step_count}/{max_steps}

IMPORTANT RULES:
1. You MUST select one of the available tools listed above
2. For data questions, use CRM_Database_Query
3. For metrics/analytics, use CRM_Analytics  
4. For analysis/explanation of data already retrieved, use CRM_Reasoning
5. Do NOT output "None" or "No tool" - always pick a tool
6. If unsure, default to CRM_Database_Query with a simple query

Output in this EXACT format:
CONTEXT: <current situation and what we know>
SUB_GOAL: <specific goal for this step>
TOOL: <exact tool name: CRM_Database_Query OR CRM_Analytics OR CRM_Reasoning>"""

        return get_llm_response(prompt, max_tokens=400)
    
    def extract_context_subgoal_and_tool(self, next_step: str) -> Tuple[str, str, Optional[str]]:
        """Parse the next step response."""
        context = ""
        sub_goal = ""
        tool_name = None
        
        for line in next_step.split("\n"):
            line = line.strip()
            if line.startswith("CONTEXT:"):
                context = line[8:].strip()
            elif line.startswith("SUB_GOAL:"):
                sub_goal = line[9:].strip()
            elif line.startswith("TOOL:"):
                tool_name = line[5:].strip()
        
        # Handle "None" or empty tool - this means no tool is needed
        if tool_name and tool_name.lower() in ["none", "n/a", "no tool", "no_tool", ""]:
            tool_name = None
        
        # Validate tool name
        if tool_name and tool_name not in self.available_tools:
            # Try fuzzy match
            for available in self.available_tools:
                if available.lower() in tool_name.lower() or tool_name.lower() in available.lower():
                    tool_name = available
                    break
            else:
                tool_name = None
        
        return context, sub_goal, tool_name
    
    def generate_final_output(self, query: str, image_path: Optional[str], memory: Memory) -> str:
        """Generate the detailed final solution."""
        memory_context = memory.get_context_string()
        
        # Get actual results from memory
        all_results = []
        for action in memory.get_actions():
            if action.get('result', {}).get('success'):
                all_results.append(action['result'])
        
        prompt = f"""Based on the CRM query and results, provide a detailed analysis.

Original Query: {query}

Actions Taken:
{memory_context}

Results Summary:
{json.dumps(all_results, default=str, indent=2)[:2000]}

Provide a detailed, well-formatted response that:
1. Directly answers the user's question
2. Includes relevant numbers and data
3. Provides insights where appropriate
4. Uses clear formatting (bullet points, sections)"""

        return get_llm_response(prompt, max_tokens=1000)
    
    def generate_direct_output(self, query: str, image_path: Optional[str], memory: Memory) -> str:
        """Generate a concise direct answer."""
        all_results = []
        for action in memory.get_actions():
            if action.get('result', {}).get('success'):
                all_results.append(action['result'])
        
        prompt = f"""Give a brief, direct answer to this CRM query.

Query: {query}

Results:
{json.dumps(all_results, default=str, indent=2)[:1500]}

Provide a 1-3 sentence direct answer with key numbers:"""

        return get_llm_response(prompt, max_tokens=200)


class Verifier:
    """
    Verifier component that checks if we have enough information.
    See: agentflow_sdk/agentflow/agentflow/models/verifier.py
    """
    def __init__(self, toolbox_metadata: Dict, available_tools: List[str], verbose: bool = True):
        self.toolbox_metadata = toolbox_metadata
        self.available_tools = available_tools
        self.verbose = verbose
    
    def verificate_context(
        self, query: str, image_path: Optional[str], query_analysis: str,
        memory: Memory, step_count: int, json_data: Dict
    ) -> str:
        """Verify if we have enough information to answer the query."""
        memory_context = memory.get_context_string()
        action_count = len(memory.actions)
        
        prompt = f"""You are verifying if we have enough information to answer a CRM query.

Original Query: {query}

Actions Completed ({action_count} so far):
{memory_context}

STOP CRITERIA - Say STOP if ANY of these are true:
1. We retrieved data AND already did a CRM_Reasoning analysis on it
2. The query was a simple data lookup and we have the results
3. We've done 2+ steps and have meaningful data/analysis
4. We're repeating the same type of action (e.g., fetching same data again)

CONTINUE CRITERIA - Say CONTINUE only if:
1. We have NO data yet and need to fetch it
2. We have raw data but haven't analyzed it when analysis was requested

Current step: {step_count}

BE DECISIVE - if we have data + analysis, STOP. Don't loop forever.

Output:
ANALYSIS: <brief assessment>
CONCLUSION: STOP or CONTINUE"""

        return get_llm_response(prompt, max_tokens=300)
    
    def extract_conclusion(self, verification: str) -> Tuple[str, str]:
        """Extract the conclusion from verification."""
        analysis = ""
        conclusion = "CONTINUE"  # Default to continue
        
        for line in verification.split("\n"):
            line = line.strip()
            if line.startswith("ANALYSIS:"):
                analysis = line[9:].strip()
            elif line.startswith("CONCLUSION:"):
                conclusion_text = line[11:].strip().upper()
                if "STOP" in conclusion_text:
                    conclusion = "STOP"
                else:
                    conclusion = "CONTINUE"
        
        return analysis, conclusion


class Executor:
    """
    Executor component that generates and executes tool commands.
    See: agentflow_sdk/agentflow/agentflow/models/executor.py
    """
    def __init__(self, tools: Dict, verbose: bool = True):
        self.tools = tools
        self.verbose = verbose
    
    def generate_tool_command(
        self, query: str, image_path: Optional[str], context: str,
        sub_goal: str, tool_name: str, tool_metadata: Dict,
        step_count: int, json_data: Dict
    ) -> str:
        """Generate the command for a tool."""
        
        # Tool-specific instructions
        if tool_name == "CRM_Database_Query":
            command_instruction = """For CRM_Database_Query, provide ONLY the raw SQL SELECT statement.
Do NOT wrap it in a function call. Just output the SQL directly.
Example: SELECT * FROM opportunities ORDER BY amount DESC LIMIT 10"""
        elif tool_name == "CRM_Analytics":
            command_instruction = """For CRM_Analytics, provide ONLY the metric name.
Available metrics: pipeline_value, lead_conversion_rate, win_rate
Example: pipeline_value"""
        else:
            command_instruction = "Provide the command parameters directly."
        
        prompt = f"""Generate a command for the {tool_name} tool.

Original Query: {query}
Current Context: {context}
Sub-Goal: {sub_goal}

Tool Information:
- Name: {tool_metadata.get('tool_name')}
- Description: {tool_metadata.get('tool_description')}
- Schema/Metadata: {tool_metadata.get('user_metadata', {})}

IMPORTANT: {command_instruction}

Output in this format:
ANALYSIS: <analyze what data is needed>
EXPLANATION: <explain the command>
COMMAND: <the raw command - SQL for database queries, metric name for analytics>"""

        return get_llm_response(prompt, max_tokens=600)
    
    def extract_explanation_and_command(self, tool_command: str) -> Tuple[str, str, str]:
        """Extract analysis, explanation, and command from response."""
        analysis = ""
        explanation = ""
        command = ""
        
        lines = tool_command.split("\n")
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith("ANALYSIS:"):
                analysis = line[9:].strip()
            elif line.startswith("EXPLANATION:"):
                explanation = line[12:].strip()
            elif line.startswith("COMMAND:"):
                # Command might span multiple lines
                command = line[8:].strip()
                # Check for SQL that spans multiple lines
                for j in range(i+1, len(lines)):
                    next_line = lines[j].strip()
                    if next_line and not any(next_line.startswith(p) for p in ["ANALYSIS:", "EXPLANATION:", "COMMAND:"]):
                        command += " " + next_line
                    else:
                        break
        
        return analysis, explanation, command.strip()
    
    def execute_tool(self, tool_name: str, command: str) -> Dict:
        """Execute a tool with the given command."""
        if tool_name not in self.tools:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        
        tool = self.tools[tool_name]
        
        try:
            if tool_name == "CRM_Database_Query":
                # Extract SQL from various formats the LLM might generate
                sql = command.strip()
                
                # Remove markdown code blocks (```sql ... ``` or ``` ... ```)
                sql = re.sub(r'^```\w*\s*', '', sql, flags=re.MULTILINE)
                sql = re.sub(r'\s*```\s*$', '', sql, flags=re.MULTILINE)
                sql = re.sub(r'```', '', sql)  # Remove any remaining backticks
                
                # Extract SQL from function call format: CRM_Database_Query(query='...')
                func_match = re.search(r"query\s*=\s*['\"](.+?)['\"](?:\s*\))?", sql, re.DOTALL | re.IGNORECASE)
                if func_match:
                    sql = func_match.group(1)
                
                # Clean up escaped quotes
                sql = sql.replace("\\'", "'").replace('\\"', '"')
                sql = sql.strip()
                
                # If it still doesn't start with SELECT, try to find SELECT in the string
                if not sql.upper().startswith("SELECT"):
                    select_match = re.search(r'(SELECT\s+.+?)(?:;|$)', sql, re.DOTALL | re.IGNORECASE)
                    if select_match:
                        sql = select_match.group(1).strip()
                
                # Final validation
                if not sql.upper().startswith("SELECT"):
                    return {"success": False, "error": f"Invalid SQL (must start with SELECT): {sql[:100]}"}
                
                # Remove trailing semicolon for consistency
                sql = sql.rstrip(';').strip()
                
                return tool.execute(query=sql)
            
            elif tool_name == "CRM_Analytics":
                # Extract metric from command - handle function call format
                metric = command.strip().lower()
                
                # Remove markdown
                metric = re.sub(r'```\w*\s*', '', metric)
                metric = re.sub(r'\s*```', '', metric)
                
                # Try to extract from function call format
                func_match = re.search(r"metric\s*=\s*['\"](\w+)['\"]", command, re.IGNORECASE)
                if func_match:
                    metric = func_match.group(1).lower()
                
                return tool.execute(metric=metric)
            
            elif tool_name == "CRM_Reasoning":
                # Try to extract task and context from structured command
                # Format: CRM_Reasoning(task='summarize', context='...')
                task_match = re.search(r"task\s*=\s*['\"](\w+)['\"]", command, re.IGNORECASE)
                context_match = re.search(r"context\s*=\s*['\"](.+?)['\"](?:\s*\))?", command, re.DOTALL | re.IGNORECASE)
                
                task = task_match.group(1) if task_match else "analyze"
                
                # If no structured context, use the memory's last result as context
                if context_match:
                    context = context_match.group(1)
                else:
                    # Use the full command as context (for free-form prompts)
                    context = command.strip()
                    
                    # Also include any recent data from memory
                    if hasattr(self, 'memory') and self.memory.actions:
                        last_result = self.memory.actions[-1].get('result', {})
                        if last_result.get('data'):
                            # Include last query result as additional context
                            context = f"Previous data: {last_result['data']}\n\nTask: {context}"
                
                print(f"   🔧 CRM_Reasoning params: task={task}, context_len={len(context)}")
                return tool.execute(task=task, context=context)
            
            else:
                return {"success": False, "error": f"Unknown tool execution: {tool_name}"}
        
        except Exception as e:
            return {"success": False, "error": str(e), "command": command}


# ============================================
# CRM-SPECIFIC TOOLS
# ============================================

class CRMQueryTool:
    """SQL Query tool for CRM database."""
    
    tool_name = "CRM_Database_Query"
    require_llm_engine = False
    
    def __init__(self):
        self.tool_description = "Execute SQL SELECT queries against the CRM database"
        self.tool_version = "1.0.0"
        self.input_types = {"query": "str - A valid PostgreSQL SELECT query"}
        self.output_type = "dict - Query results with success status"
        self.demo_commands = [
            "CRM_Database_Query(query='SELECT * FROM leads LIMIT 10')",
            "CRM_Database_Query(query='SELECT COUNT(*) FROM opportunities WHERE stage = \\'Closed Won\\'')"
        ]
        self.user_metadata = {
            "schema": """
CRM Database Schema:
- leads: lead_id, first_name, last_name, company_name, email, lead_status, lead_rating, annual_revenue, ai_score, created_at
- contacts: contact_id, first_name, last_name, account_id, email, title, department
- accounts: account_id, account_name, industry, annual_revenue, employee_count
- opportunities: opportunity_id, opportunity_name, account_id, amount, stage, probability, close_date, is_closed, is_won
- activities: activity_id, activity_type, subject, status, related_to_type, related_to_id, created_at
"""
        }
    
    def get_metadata(self) -> Dict:
        return {
            "tool_name": self.tool_name,
            "tool_description": self.tool_description,
            "tool_version": self.tool_version,
            "input_types": self.input_types,
            "output_type": self.output_type,
            "demo_commands": self.demo_commands,
            "user_metadata": self.user_metadata,
            "require_llm_engine": self.require_llm_engine
        }
    
    def execute(self, query: str = None, **kwargs) -> Dict:
        if not query:
            return {"success": False, "error": "No query provided"}
        
        # Security check
        query_upper = query.strip().upper()
        if not query_upper.startswith("SELECT"):
            return {"success": False, "error": "Only SELECT queries allowed"}
        
        dangerous = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 'TRUNCATE']
        for kw in dangerous:
            if kw in query_upper:
                return {"success": False, "error": f"Dangerous keyword '{kw}' not allowed"}
        
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


class CRMAnalyticsTool:
    """Analytics and aggregation tool for CRM insights."""
    
    tool_name = "CRM_Analytics"
    require_llm_engine = False
    
    def __init__(self):
        self.tool_description = "Perform analytics and aggregations on CRM data"
        self.tool_version = "1.0.0"
        self.input_types = {
            "metric": "str - The metric to calculate (e.g., 'pipeline_value', 'lead_conversion_rate', 'deal_velocity')",
            "filters": "dict - Optional filters like date range, stage, etc."
        }
        self.output_type = "dict - Analytics results"
        self.demo_commands = [
            "CRM_Analytics(metric='pipeline_value', filters={'stage': 'Proposal'})",
            "CRM_Analytics(metric='lead_conversion_rate', filters={'days': 30})"
        ]
        self.user_metadata = {
            "available_metrics": [
                "pipeline_value - Total value of open opportunities",
                "lead_conversion_rate - Percentage of leads converted to opportunities",
                "deal_velocity - Average days to close deals",
                "win_rate - Percentage of closed-won vs closed-lost",
                "activity_count - Number of activities by type"
            ]
        }
    
    def get_metadata(self) -> Dict:
        return {
            "tool_name": self.tool_name,
            "tool_description": self.tool_description,
            "tool_version": self.tool_version,
            "input_types": self.input_types,
            "output_type": self.output_type,
            "demo_commands": self.demo_commands,
            "user_metadata": self.user_metadata,
            "require_llm_engine": self.require_llm_engine
        }
    
    def execute(self, metric: str = None, filters: Dict = None, **kwargs) -> Dict:
        filters = filters or {}
        
        try:
            if metric == "pipeline_value":
                query = "SELECT SUM(amount) as total_value, COUNT(*) as deal_count FROM opportunities WHERE is_closed = false"
                results = execute_query(query, {})
                return {
                    "success": True,
                    "metric": metric,
                    "value": results[0] if results else {"total_value": 0, "deal_count": 0}
                }
            
            elif metric == "lead_conversion_rate":
                query = """
                    SELECT 
                        COUNT(*) FILTER (WHERE lead_status = 'converted') as converted,
                        COUNT(*) as total
                    FROM leads
                """
                results = execute_query(query, {})
                if results and results[0]['total'] > 0:
                    rate = (results[0]['converted'] / results[0]['total']) * 100
                else:
                    rate = 0
                return {
                    "success": True,
                    "metric": metric,
                    "value": {"conversion_rate": round(rate, 2), **results[0]}
                }
            
            elif metric == "win_rate":
                query = """
                    SELECT 
                        COUNT(*) FILTER (WHERE is_won = true) as won,
                        COUNT(*) FILTER (WHERE is_closed = true) as closed
                    FROM opportunities
                """
                results = execute_query(query, {})
                if results and results[0]['closed'] > 0:
                    rate = (results[0]['won'] / results[0]['closed']) * 100
                else:
                    rate = 0
                return {
                    "success": True,
                    "metric": metric,
                    "value": {"win_rate": round(rate, 2), **results[0]}
                }
            
            else:
                return {"success": False, "error": f"Unknown metric: {metric}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}


class CRMReasoningTool:
    """LLM-powered reasoning tool for complex analysis - use AFTER getting data."""
    
    tool_name = "CRM_Reasoning"
    require_llm_engine = True
    
    def __init__(self):
        self.tool_description = """Use LLM reasoning to analyze, summarize, or explain CRM data.
IMPORTANT: This tool should be used AFTER fetching data with CRM_Database_Query or CRM_Analytics.
It analyzes data from previous steps - do NOT use this to ask clarifying questions to the user.
If the query is unclear, use the planner to craft a clarifying response directly."""
        self.tool_version = "1.0.0"
        self.input_types = {
            "task": "str - The reasoning task (summarize, recommend, analyze, explain)",
            "context": "str - The data or context to reason about (typically from previous query results)"
        }
        self.output_type = "str - Reasoned response"
        self.demo_commands = [
            "CRM_Reasoning(task='summarize', context='<data from previous query>')",
            "CRM_Reasoning(task='recommend', context='Lead with low engagement')"
        ]
    
    def get_metadata(self) -> Dict:
        return {
            "tool_name": self.tool_name,
            "tool_description": self.tool_description,
            "tool_version": self.tool_version,
            "input_types": self.input_types,
            "output_type": self.output_type,
            "demo_commands": self.demo_commands,
            "require_llm_engine": self.require_llm_engine
        }
    
    def execute(self, task: str = None, context: str = None, **kwargs) -> Dict:
        print(f"   🔧 CRM_Reasoning called: task={task}, context_len={len(context) if context else 0}")
        
        if not task or not context:
            print(f"   ⚠️ Missing required params: task={task is not None}, context={context is not None}")
            return {"success": False, "error": "Both task and context are required", "result_count": 0}
        
        prompts = {
            "summarize": f"Summarize the following CRM data concisely:\n\n{context}",
            "recommend": f"Based on this CRM data, provide actionable recommendations:\n\n{context}",
            "analyze": f"Analyze this CRM data and identify key insights and patterns:\n\n{context}",
            "explain": f"Explain what this CRM data means in business terms:\n\n{context}"
        }
        
        prompt = prompts.get(task, f"Task: {task}\n\nContext:\n{context}")
        print(f"   📝 Prompt type: {task}, length: {len(prompt)}")
        
        try:
            response = get_llm_response(prompt, max_tokens=800)
            print(f"   ✅ Got LLM response: {len(response)} chars")
            return {
                "success": True,
                "task": task,
                "reasoning": response,
                "result_count": 1
            }
        except Exception as e:
            print(f"   ❌ LLM Error: {e}")
            return {"success": False, "error": str(e), "result_count": 0}


# ============================================
# AGENTFLOW CRM SOLVER
# ============================================

class AgentFlowCRMSolver:
    """
    Full AgentFlow Solver for CRM queries.
    
    Uses the AgentFlow architecture:
    - Planner: Analyzes query, decides next actions, selects tools
    - Executor: Generates tool commands, executes tools
    - Verifier: Checks if we have enough info to answer
    - Memory: Tracks all actions and results for context
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
        
        # Initialize tools
        self.tools = {
            "CRM_Database_Query": CRMQueryTool(),
            "CRM_Analytics": CRMAnalyticsTool(),
            "CRM_Reasoning": CRMReasoningTool()
        }
        
        # Build toolbox metadata for the Planner
        self.toolbox_metadata = {
            name: tool.get_metadata() for name, tool in self.tools.items()
        }
        self.available_tools = list(self.tools.keys())
        
        # Initialize AgentFlow components
        self.memory = Memory()
        
        self.planner = Planner(
            toolbox_metadata=self.toolbox_metadata,
            available_tools=self.available_tools,
            verbose=verbose
        )
        
        self.verifier = Verifier(
            toolbox_metadata=self.toolbox_metadata,
            available_tools=self.available_tools,
            verbose=verbose
        )
        
        self.executor = Executor(
            tools=self.tools,
            verbose=verbose
        )
        
        if verbose:
            print("🚀 AgentFlow CRM Solver initialized")
            print(f"   Tools: {self.available_tools}")
            print(f"   Max Steps: {max_steps}")
            print(f"   Components: Planner, Executor, Verifier, Memory")
    
    def solve(self, query: str) -> Dict[str, Any]:
        """
        Solve a CRM query using the full AgentFlow architecture.
        
        Returns detailed reasoning traces along with results.
        """
        start_time = time.time()
        self.memory.clear()
        self.memory.set_query(query)  # Store query in SDK memory
        
        reasoning_steps = []
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"🔍 AgentFlow CRM Query: {query}")
            print(f"{'='*60}")
        
        # Step 1: Query Analysis (Planner)
        if self.verbose:
            print(f"\n📋 Step 0: Query Analysis")
        
        try:
            query_analysis = self.planner.analyze_query(query, None)
        except Exception as e:
            query_analysis = f"Query about: {query}. Error during analysis: {e}"
        
        reasoning_steps.append({
            "step": 0,
            "type": "analysis",
            "title": "Query Analysis",
            "content": query_analysis,
            "timestamp": datetime.now().isoformat()
        })
        
        if self.verbose:
            print(f"   Analysis: {query_analysis[:200]}...")
        
        # Check if query is too ambiguous to process
        is_ambiguous, clarifying_response = self.planner.is_query_ambiguous(query, query_analysis)
        
        if is_ambiguous:
            if self.verbose:
                print(f"\n⚠️ Query is ambiguous - returning clarifying response")
            
            execution_time = round(time.time() - start_time, 2)
            
            reasoning_steps.append({
                "step": 1,
                "type": "clarification",
                "title": "Clarification Needed",
                "content": clarifying_response,
                "timestamp": datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "query": query,
                "summary": clarifying_response,
                "detailed_solution": clarifying_response,
                "results": [],
                "result_count": 0,
                "sql_query": None,
                "reasoning_steps": reasoning_steps,
                "memory": [],
                "execution_time": execution_time,
                "steps": 1,
                "agentflow": True,
                "needs_clarification": True,
                "components_used": ["Planner"],
                "tools_available": self.available_tools
            }
        
        # Main execution loop
        step_count = 0
        final_result = None
        last_command = ""
        consecutive_no_tool = 0  # Track consecutive no-tool selections
        max_no_tool_attempts = 2  # Max attempts before giving up
        
        # Track what we've done to detect loops
        has_fetched_data = False
        has_done_reasoning = False
        last_tools = []  # Track last few tools used
        
        while step_count < self.max_steps and (time.time() - start_time) < self.max_time:
            step_count += 1
            
            # Step 2: Generate next action (Planner)
            if self.verbose:
                print(f"\n🎯 Step {step_count}: Planning")
            
            try:
                next_step = self.planner.generate_next_step(
                    query, None, query_analysis, self.memory,
                    step_count, self.max_steps, {}
                )
                
                context, sub_goal, tool_name = self.planner.extract_context_subgoal_and_tool(next_step)
            except Exception as e:
                context = f"Error: {e}"
                sub_goal = "Query database"
                tool_name = "CRM_Database_Query"
            
            reasoning_steps.append({
                "step": step_count,
                "type": "planning",
                "title": f"Action Planning - {tool_name}",
                "context": context,
                "sub_goal": sub_goal,
                "tool": tool_name,
                "timestamp": datetime.now().isoformat()
            })
            
            if self.verbose:
                print(f"   Tool: {tool_name}")
                print(f"   Sub-goal: {sub_goal}")
            
            if tool_name is None or tool_name not in self.tools:
                if self.verbose:
                    print(f"   ⚠️ Unknown tool: {tool_name}")
                
                consecutive_no_tool += 1
                
                # If we've failed to select a tool multiple times, break out
                if consecutive_no_tool >= max_no_tool_attempts:
                    if self.verbose:
                        print(f"   ❌ No valid tool selected after {consecutive_no_tool} attempts - generating fallback response")
                    
                    # Generate a helpful response using the sub_goal as context
                    fallback_response = self.planner._generate_clarifying_response(query)
                    
                    execution_time = round(time.time() - start_time, 2)
                    
                    reasoning_steps.append({
                        "step": step_count,
                        "type": "fallback",
                        "title": "Fallback Response",
                        "content": fallback_response,
                        "reason": f"Could not determine appropriate tool after {consecutive_no_tool} attempts",
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    return {
                        "success": True,
                        "query": query,
                        "summary": fallback_response,
                        "detailed_solution": fallback_response,
                        "results": [],
                        "result_count": 0,
                        "sql_query": None,
                        "reasoning_steps": reasoning_steps,
                        "memory": self.memory.get_actions(),
                        "execution_time": execution_time,
                        "steps": step_count,
                        "agentflow": True,
                        "needs_clarification": True,
                        "components_used": ["Planner"],
                        "tools_available": self.available_tools
                    }
                
                final_result = {"success": False, "error": f"Unknown tool: {tool_name}"}
                self.memory.add_action(step_count, str(tool_name), sub_goal, "", final_result)
                continue
            
            # Reset counter when we successfully select a tool
            consecutive_no_tool = 0
            
            # Step 3: Generate tool command (Executor)
            if self.verbose:
                print(f"\n📝 Step {step_count}: Command Generation")
            
            try:
                tool_command = self.executor.generate_tool_command(
                    query, None, context, sub_goal, tool_name,
                    self.toolbox_metadata[tool_name], step_count, {}
                )
                
                analysis, explanation, command = self.executor.extract_explanation_and_command(tool_command)
                last_command = command
            except Exception as e:
                analysis = f"Error: {e}"
                explanation = "Fallback query"
                command = "SELECT COUNT(*) FROM leads"
                last_command = command
            
            reasoning_steps.append({
                "step": step_count,
                "type": "command_generation",
                "title": f"Command Generation - {tool_name}",
                "analysis": analysis,
                "explanation": explanation,
                "command": command,
                "timestamp": datetime.now().isoformat()
            })
            
            if self.verbose:
                print(f"   Command: {command[:100]}...")
            
            # Step 4: Execute tool (Executor)
            if self.verbose:
                print(f"\n🛠️ Step {step_count}: Execution")
            
            result = self.executor.execute_tool(tool_name, command)
            final_result = result
            
            reasoning_steps.append({
                "step": step_count,
                "type": "execution",
                "title": f"Tool Execution - {tool_name}",
                "result": {
                    "success": result.get("success", False),
                    "result_count": result.get("result_count", 0),
                    "error": result.get("error")
                },
                "timestamp": datetime.now().isoformat()
            })
            
            if self.verbose:
                status = "✅" if result.get("success") else "❌"
                print(f"   {status} Result count: {result.get('result_count', 0)}")
            
            # Update memory
            self.memory.add_action(step_count, tool_name, sub_goal, command, result)
            
            # Track what we've done to detect loops
            if tool_name == "CRM_Database_Query" and result.get("success"):
                has_fetched_data = True
            if tool_name == "CRM_Reasoning" and result.get("success"):
                has_done_reasoning = True
            
            last_tools.append(tool_name)
            if len(last_tools) > 4:
                last_tools.pop(0)
            
            # Force stop if we have data + reasoning (the common pattern)
            if has_fetched_data and has_done_reasoning and step_count >= 2:
                if self.verbose:
                    print(f"\n✅ Auto-stop: Have data + analysis after {step_count} steps")
                break
            
            # Detect tool oscillation loop (DB -> Reasoning -> DB -> Reasoning...)
            if len(last_tools) >= 4:
                if last_tools == ["CRM_Database_Query", "CRM_Reasoning", "CRM_Database_Query", "CRM_Reasoning"]:
                    if self.verbose:
                        print(f"\n⚠️ Detected loop pattern, stopping")
                    break
            
            # Step 5: Verify if we should continue (Verifier)
            if self.verbose:
                print(f"\n🤖 Step {step_count}: Verification")
            
            try:
                stop_verification = self.verifier.verificate_context(
                    query, None, query_analysis, self.memory, step_count, {}
                )
                
                context_verification, conclusion = self.verifier.extract_conclusion(stop_verification)
            except Exception as e:
                context_verification = f"Error: {e}"
                conclusion = "STOP" if result.get("success") else "CONTINUE"
            
            reasoning_steps.append({
                "step": step_count,
                "type": "verification",
                "title": "Context Verification",
                "analysis": context_verification,
                "conclusion": conclusion,
                "timestamp": datetime.now().isoformat()
            })
            
            if self.verbose:
                emoji = "✅" if conclusion == "STOP" else "🔄"
                print(f"   Conclusion: {conclusion} {emoji}")
            
            if conclusion == "STOP":
                break
        
        # Generate final output (Planner)
        execution_time = round(time.time() - start_time, 2)
        
        if self.verbose:
            print(f"\n📝 Generating final output...")
        
        try:
            final_output = self.planner.generate_final_output(query, None, self.memory)
            direct_output = self.planner.generate_direct_output(query, None, self.memory)
        except Exception as e:
            final_output = f"Results from query: {str(final_result)}"
            direct_output = f"Query completed with {final_result.get('result_count', 0) if final_result else 0} results."
        
        reasoning_steps.append({
            "step": step_count + 1,
            "type": "final_output",
            "title": "Final Answer",
            "detailed_solution": final_output,
            "direct_answer": direct_output,
            "timestamp": datetime.now().isoformat()
        })
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"✨ AgentFlow Complete - {step_count} steps, {execution_time}s")
            print(f"{'='*60}")
        
        # Build response
        return {
            "success": final_result.get("success", False) if final_result else False,
            "query": query,
            "summary": direct_output,
            "detailed_solution": final_output,
            "results": final_result.get("results", []) if final_result else [],
            "result_count": final_result.get("result_count", 0) if final_result else 0,
            "sql_query": last_command if "SELECT" in last_command.upper() else None,
            "reasoning_steps": reasoning_steps,
            "memory": self.memory.get_actions(),
            "execution_time": execution_time,
            "steps": step_count,
            "agentflow": True,
            "components_used": ["Planner", "Executor", "Verifier", "Memory"],
            "tools_available": self.available_tools
        }


def create_agentflow_crm_solver(
    max_steps: int = 10,
    verbose: bool = True
) -> AgentFlowCRMSolver:
    """Factory function to create the CRM solver."""
    return AgentFlowCRMSolver(max_steps=max_steps, verbose=verbose)


# Test
if __name__ == "__main__":
    solver = create_agentflow_crm_solver(verbose=True)
    result = solver.solve("How many leads do we have and what is the pipeline value?")
    print(f"\n📊 Final Result:")
    print(json.dumps(result, indent=2, default=str))
