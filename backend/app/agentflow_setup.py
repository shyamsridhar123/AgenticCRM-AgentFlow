"""
AgentFlow Path Setup - ensures correct import paths for the SDK.
Import this module before any AgentFlow imports.
"""

import sys
import os

def setup_agentflow_paths():
    """Add AgentFlow SDK paths to sys.path for proper imports."""
    
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sdk_agentflow_dir = os.path.join(backend_dir, "agentflow_sdk", "agentflow")
    
    # Add agentflow directory so 'from agentflow.models...' works
    if sdk_agentflow_dir not in sys.path:
        sys.path.insert(0, sdk_agentflow_dir)
    
    # Also add backend dir for app imports
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    
    return sdk_agentflow_dir

# Auto-setup on import
AGENTFLOW_PATH = setup_agentflow_paths()
