import httpx
import json  # <-- Add this
from typing import Any, Dict, List, Optional
from coreason_maco.core.registry import ToolRegistry

class RemoteMcpAdapter(ToolRegistry):
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)

    async def execute(self, tool_name: str, arguments: Dict[str, Any], user_context: Any = None) -> Any:
        url = f"{self.base_url}/tools/execute"
        payload = {
            "tool_name": tool_name,
            "arguments": arguments,
            "context": user_context.model_dump() if hasattr(user_context, "model_dump") else user_context
        }
        
        print(f"📡 Maco -> MCP: POST {url} | Tool: {tool_name}")
        
        try:
            resp = await self.client.post(url, json=payload)
            resp.raise_for_status()
            
            # --- FIX: Parse the MCP Response Cleanly ---
            data = resp.json()
            
            # Extract actual text content if it exists (Standard MCP format)
            final_text = ""
            if "content" in data and isinstance(data["content"], list):
                for item in data["content"]:
                    if item.get("type") == "text":
                        final_text += item.get("text", "")
            
            # If standard extraction failed, use the raw JSON string
            if not final_text:
                final_text = json.dumps(data, indent=2)

            # Return a simple object that the Controller expects
            return type("McpResult", (), {"content": [type("Text", (), {"text": final_text})]})
            
        except httpx.HTTPStatusError as e:
            print(f"❌ Adapter Error: {e}")
            raise RuntimeError(f"Tool execution failed: {e}")
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            raise RuntimeError(f"Could not connect to MCP: {e}")

    async def list_tools(self) -> List[Dict[str, Any]]:
        # ... (Keep existing list_tools implementation) ...
        url = f"{self.base_url}/tools"
        print(f"📡 Maco -> MCP: GET {url} (Discovery)")
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
            tools = resp.json()
            print(f"   ✅ MCP returned {len(tools)} tools.")
            return tools
        except Exception as e:
            print(f"❌ Adapter Discovery Error: {e}")
            return []

    async def close(self):
        await self.client.aclose()
