"""
Test script to verify AgentFlow CRM integration.
"""

import sys
import os

# Set up paths correctly FIRST
backend_dir = os.path.dirname(os.path.abspath(__file__))
sdk_agentflow_dir = os.path.join(backend_dir, "agentflow_sdk", "agentflow")
sys.path.insert(0, sdk_agentflow_dir)
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("AgentFlow CRM Integration Test")
print("=" * 60)
print(f"Backend dir: {backend_dir}")
print(f"SDK agentflow dir: {sdk_agentflow_dir}")

# Test 1: Import AgentFlow components
print("\n1. Testing AgentFlow imports...")
try:
    from agentflow.solver import Solver, construct_solver
    from agentflow.models.planner import Planner
    from agentflow.models.executor import Executor
    from agentflow.models.verifier import Verifier
    from agentflow.models.memory import Memory
    print("   ✅ AgentFlow core imports successful")
    print(f"      - Solver: {Solver}")
    print(f"      - construct_solver: {construct_solver}")
except Exception as e:
    import traceback
    print(f"   ❌ AgentFlow import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

# Test 2: Import and test Azure OpenAI engine
print("\n2. Testing Azure OpenAI engine...")
try:
    from agentflow.engine.azure_openai import ChatAzureOpenAI
    engine = ChatAzureOpenAI(model_string="gpt-5.2-chat")
    response = engine.generate("Say 'AgentFlow works!' in exactly those words.")
    print(f"   ✅ Azure engine response: {response[:100] if isinstance(response, str) else response}")
except Exception as e:
    import traceback
    print(f"   ❌ Azure engine failed: {e}")
    traceback.print_exc()

# Test 3: Import CRM database tool
print("\n3. Testing CRM database tool...")
try:
    from agentflow.tools.crm_database.tool import CRMDatabaseTool
    
    tool = CRMDatabaseTool()
    print(f"   ✅ CRM tool created: {tool.tool_name}")
    
    # Test execute
    result = tool.execute(query="SELECT COUNT(*) as lead_count FROM leads")
    print(f"   Query result: {result}")
except Exception as e:
    import traceback
    print(f"   ❌ CRM tool failed: {e}")
    traceback.print_exc()

# Test 4: Full solver test
print("\n4. Testing AgentFlow solver with a query...")
try:
    # Use construct_solver with Azure OpenAI deployment
    solver = construct_solver(
        llm_engine_name="gpt-5.2-chat",  # Azure OpenAI deployment
        enabled_tools=["Base_Generator_Tool"],
        output_types="direct",
        max_steps=3,
        verbose=True
    )
    print(f"   ✅ Solver constructed successfully!")
    print(f"      - Planner: {type(solver.planner).__name__}")
    print(f"      - Executor: {type(solver.executor).__name__}")
    print(f"      - Verifier: {type(solver.verifier).__name__}")
    
except Exception as e:
    import traceback
    print(f"   ❌ Solver construction failed: {e}")
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test Complete - AgentFlow Integration Status")
print("=" * 60)
