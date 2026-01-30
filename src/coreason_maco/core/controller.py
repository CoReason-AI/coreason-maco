import re
import json
import difflib
from typing import Any, Dict, AsyncIterator, List
from coreason_maco.core.registry import ServerRegistry

class WorkflowController:
    def __init__(self, services: ServerRegistry):
        self.services = services

    # --- 1. Fetch Valid Tool Names ---
    async def _get_valid_tool_names(self) -> List[str]:
        try:
            tools = await self.services.tool_registry.list_tools()
            names = []
            for t in tools:
                t_data = t.model_dump() if hasattr(t, "model_dump") else t
                if "function" in t_data: t_data = t_data["function"]
                names.append(t_data.get("name"))
            return names
        except:
            return []

    # --- 2. Smart Cleaner ---
    def _extract_tool_name(self, raw_text: str, valid_names: List[str]) -> str:
        clean = raw_text.strip()
        
        # A. JSON Parser (New)
        try:
            if "```" in clean: clean = clean.split("```")[1].replace("json", "").strip()
            if "{" in clean and "}" in clean:
                data = json.loads(clean)
                if "tool" in data: clean = data["tool"]
        except: pass

        # B. Standard Cleanup
        clean = clean.replace('"', '').replace("'", "").replace("Tool_ID:", "").replace("Result:", "").strip()
        
        # C. Matching
        if clean in valid_names: return clean
        for name in valid_names:
            if name in raw_text: return name
        matches = difflib.get_close_matches(clean, valid_names, n=1, cutoff=0.6)
        if matches: return matches[0]
            
        return None

    # --- 3. Variable Resolver ---
    async def _resolve_value(self, value: Any, context: Dict[str, Any]) -> Any:
        if isinstance(value, str) and "{{" in value:
            if "{{ available_tools }}" in value:
                try:
                    tools = await self.services.tool_registry.list_tools()
                    lines = []
                    for t in tools:
                        t_data = t.model_dump() if hasattr(t, "model_dump") else t
                        if "function" in t_data: t_data = t_data["function"]
                        name = t_data.get("name", "Unknown")
                        # Add docstring description if available
                        desc = t_data.get("description", "No description")
                        lines.append(f"- {name}: {desc}")
                    value = value.replace("{{ available_tools }}", "\n".join(lines))
                except Exception as e:
                    print(f"⚠️ Error fetching tools: {e}")
            
            def replace_match(match):
                key = match.group(1)
                return str(context.get(key, match.group(0)))
            return re.sub(r"\{\{\s*([\w\d_]+)(\.output)?\s*\}\}", replace_match, value)
        return value

    # --- 4. Config Recursion ---
    async def _resolve_config(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        resolved = {}
        for k, v in config.items():
            if isinstance(v, dict): resolved[k] = await self._resolve_config(v, context)
            elif isinstance(v, list): resolved[k] = [await self._resolve_config(i, context) if isinstance(i, dict) else await self._resolve_value(i, context) for i in v]
            else: resolved[k] = await self._resolve_value(v, context)
        return resolved

    # --- 5. Execution Loop ---
    async def execute_recipe(self, manifest: Dict[str, Any], inputs: Dict[str, Any], context: Any = None) -> AsyncIterator[Dict[str, Any]]:
        execution_data = inputs.copy()
        nodes = manifest.get("nodes", [])
        run_id = inputs.get("trace_id", "run-1")

        print(f"🚀 Starting Workflow: {len(nodes)} nodes")

        for node in nodes:
            node_id = node["id"]
            node_type = node["type"]
            raw_config = node.get("config", {})
            
            try:
                resolved_config = await self._resolve_config(raw_config, execution_data)
                output_val = None

                if node_type == "TOOL":
                    raw_output = resolved_config.get("tool_name", "")
                    valid_names = await self._get_valid_tool_names()
                    selected_tool = self._extract_tool_name(raw_output, valid_names)
                    
                    if not selected_tool:
                        error_msg = f"⛔ VALIDATION FAILED: Could not map '{raw_output[:30]}...' to any tool."
                        print(error_msg)
                        # ✅ FIX 1: Included run_id and node_id in error event
                        yield {
                            "event_type": "NODE_ERROR", 
                            "run_id": run_id, 
                            "node_id": node_id, 
                            "payload": {"error": error_msg}
                        }
                        break 
                    
                    print(f"▶️ Executing TOOL '{node_id}': {selected_tool}")
                    result = await self.services.tool_registry.execute(selected_tool, resolved_config.get("args", {}), user_context=context)
                    
                    if hasattr(result, 'content') and result.content:
                        output_val = result.content[0].text if hasattr(result.content[0], 'text') else str(result.content[0])
                    else:
                        output_val = str(result)

                elif node_type == "AGENT":
                    print(f"\n📝 [DEBUG PROMPT] FINAL PAYLOAD for {resolved_config.get('agent_name')}:")
                    print("-" * 50)
                    print(resolved_config.get("task"))
                    print("-" * 50)

                    output_val = await self.services.agent_registry.execute_agent(
                        agent_name=resolved_config.get("agent_name"),
                        task=resolved_config.get("task"),
                        context=resolved_config.get("context"),
                        llm_config=resolved_config.get("llm_config")
                    )

                if isinstance(output_val, str):
                    output_val = output_val.strip().replace('"', '').replace("'", "")
                
                execution_data[node_id] = output_val
                yield {"event_type": "NODE_DONE", "run_id": run_id, "node_id": node_id, "payload": {"result": output_val}}

            except Exception as e:
                print(f"❌ Error in Node {node_id}: {e}")
                # ✅ FIX 2: Included run_id and node_id in exception event
                yield {
                    "event_type": "NODE_ERROR", 
                    "run_id": run_id, 
                    "node_id": node_id, 
                    "payload": {"error": str(e)}
                }
                break
