# src/coreason_maco/core/controller.py

import re
from typing import Any, Dict, AsyncIterator
from coreason_maco.core.registry import ServerRegistry

class WorkflowController:
    def __init__(self, services: ServerRegistry):
        self.services = services

    # --- 1. NEW HELPER: Fetch and Format Tools ---
    async def _get_tool_list_string(self) -> str:
        """
        Dynamically fetches tools from the registry and formats them for the LLM.
        """
        try:
            # Depending on your Registry interface, you might need to adjust this call.
            # Assuming tool_registry has a method to get definitions.
            # If using RemoteMcpAdapter, it likely has list_tools()
            if hasattr(self.services.tool_registry, "list_tools"):
                tools = await self.services.tool_registry.list_tools()
            else:
                # Fallback or specific method for your specific registry implementation
                return "No tools available."

            lines = []
            for t in tools:
                # Handle both Pydantic models and Dicts
                t_data = t.model_dump() if hasattr(t, "model_dump") else t
                
                name = t_data.get("name")
                desc = t_data.get("description", "No description")
                lines.append(f"- {name}: {desc}")
            
            return "\n".join(lines)
        except Exception as e:
            print(f"⚠️ Failed to fetch tool list: {e}")
            return "Error fetching tool list."

    # --- 2. UPDATE: Make _resolve_config ASYNC ---
    # We need async because fetching tools might involve network calls (MCP)
    async def _resolve_value(self, value: Any, context: Dict[str, Any]) -> Any:
        if isinstance(value, str) and "{{" in value:
            
            # --- MAGIC VARIABLE: {{ available_tools }} ---
            if "{{ available_tools }}" in value:
                print("   🛠️ Injecting Dynamic Tool List...")
                tool_list = await self._get_tool_list_string()
                value = value.replace("{{ available_tools }}", tool_list)

            # Standard Variable Resolution (same as before)
            def replace_match(match):
                key = match.group(1)
                if key in context:
                    return str(context[key])
                return match.group(0)

            resolved_string = re.sub(r"\{\{\s*([\w\d_]+)(\.output)?\s*\}\}", replace_match, value)
            return resolved_string
        
        return value

    async def _resolve_config(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively resolves config (Now Async)."""
        resolved = {}
        for k, v in config.items():
            if isinstance(v, dict):
                resolved[k] = await self._resolve_config(v, context)
            elif isinstance(v, list):
                # Resolve list items
                items = []
                for i in v:
                    if isinstance(i, dict):
                        items.append(await self._resolve_config(i, context))
                    else:
                        items.append(await self._resolve_value(i, context))
                resolved[k] = items
            else:
                resolved[k] = await self._resolve_value(v, context)
        return resolved

    async def execute_recipe(self, manifest: Dict[str, Any], inputs: Dict[str, Any], context: Any = None) -> AsyncIterator[Dict[str, Any]]:
        execution_data = inputs.copy()
        run_id = inputs.get("trace_id", "default-run")
        nodes = manifest.get("nodes", [])

        print(f"🚀 Starting Workflow: {len(nodes)} nodes")

        for node in nodes:
            node_id = node["id"]
            node_type = node["type"]
            raw_config = node.get("config", {})

            # --- AWAIT THE RESOLUTION ---
            resolved_config = await self._resolve_config(raw_config, execution_data)
            output_val = None

            try:
                if node_type == "TOOL":
                    # ... (Same Tool Logic) ...
                    tool_name = resolved_config.get("tool_name")
                    print(f"▶️ Executing TOOL '{node_id}': {tool_name}")
                    result = await self.services.tool_registry.execute(
                        tool_name, 
                        resolved_config.get("args", {}), 
                        user_context=context
                    )
                    # ... extract content ...
                    if hasattr(result, 'content') and result.content:
                        output_val = result.content[0].text
                    else:
                        output_val = str(result)

                elif node_type == "AGENT":
                    agent_name = resolved_config.get("agent_name")
                    task_prompt = resolved_config.get("task")

                    # --- DEBUG PRINT: SEE EXACTLY WHAT CORTEX GETS ---
                    print(f"\n🧠 [DEBUG] Sending Prompt to Cortex ({agent_name}):\n{'-'*40}\n{task_prompt}\n{'-'*40}\n")
                    # -------------------------------------------------
                    print(f"🧠 Executing AGENT '{node_id}': {agent_name}")
                    
                    output_val = await self.services.agent_registry.execute_agent(
                        agent_name=agent_name,
                        task=resolved_config.get("task"),
                        context=resolved_config.get("context")
                    )

                # ... (Same Storage/Yield Logic) ...
                if isinstance(output_val, str):
                    output_val = output_val.strip().replace('"', '').replace("'", "")
                
                execution_data[node_id] = output_val
                
                yield {
                    "event_type": "NODE_DONE", 
                    "run_id": run_id, 
                    "node_id": node_id, 
                    "payload": {"result": output_val}
                }

            except Exception as e:
                print(f"❌ Error in Node {node_id}: {e}")
                yield {"event_type": "NODE_ERROR", "payload": {"error": str(e)}}
                break
