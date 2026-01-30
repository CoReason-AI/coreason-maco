import httpx
import json
from typing import Any, Dict, Optional, Union, List
from coreason_maco.core.registry import AgentRegistry

class RemoteCortexAdapter(AgentRegistry):
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=60.0)

    # ✅ FIX: Added 'llm_config' to the signature
    async def execute_agent(self, agent_name: str, task: str, context: Any = None, llm_config: Dict[str, Any] = None) -> str:
        url = f"{self.base_url}/agent/execute"
        
        # --- Wrapper Logic for Context ---
        safe_context = context
        if context is None:
            safe_context = {}
        elif not isinstance(context, dict):
            safe_context = {"wrapped_content": context}
        
        payload = {
            "agent_name": agent_name,
            "task": task,
            "context": safe_context,
            "llm_config": llm_config  # ✅ Pass the config to Cortex
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
