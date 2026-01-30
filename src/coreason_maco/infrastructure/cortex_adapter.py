import httpx
import json
from typing import Any, Dict, Optional, Union, List
from coreason_maco.core.registry import AgentRegistry

class RemoteCortexAdapter(AgentRegistry):
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=60.0)

    async def execute_agent(self, agent_name: str, task: str, context: Any = None) -> str:
        url = f"{self.base_url}/agent/execute"
        
        # --- CRITICAL FIX: The "Wrapper" Strategy ---
        # The Cortex Server strictly expects a Dictionary for 'context'.
        # The Search Tool returns a List. Sending a List (or String) causes Error 422.
        # SOLUTION: If context is not a dict, wrap it in one.
        
        safe_context = context
        
        # If it's None, send empty dict
        if context is None:
            safe_context = {}
            
        # If it's a List (Search Results) or String, wrap it!
        elif not isinstance(context, dict):
            # We wrap the data so it passes the server's validation check
            safe_context = {"wrapped_content": context}
        
        payload = {
            "agent_name": agent_name,
            "task": task,
            "context": safe_context 
        }
        
        try:
            resp = await self.client.post(url, json=payload)
            resp.raise_for_status()
            
            data = resp.json()
            return data.get("content", "")
            
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            print(f"❌ Cortex Service Failed: {e} | Details: {error_detail}")
            raise RuntimeError(f"Cortex failed: {error_detail}")
            
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            raise RuntimeError(f"Could not connect to Cortex: {e}")

    async def close(self):
        await self.client.aclose()
