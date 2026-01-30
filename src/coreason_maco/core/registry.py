from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

# 1. Interface for Tool Execution
class ToolRegistry(ABC):
    @abstractmethod
    async def execute(self, tool_name: str, arguments: Dict[str, Any], user_context: Any = None) -> Any:
        pass

# 2. Interface for Agent Execution (Cortex)
class AgentRegistry(ABC):
    @abstractmethod
    async def execute_agent(self, agent_name: str, task: str, context: Dict[str, Any] = None) -> Any:
        pass

# 3. Interface for the Main Registry (Container)
class ServerRegistry(ABC):
    @property
    @abstractmethod
    def tool_registry(self) -> ToolRegistry:
        pass

    @property
    @abstractmethod
    def agent_registry(self) -> AgentRegistry:
        pass
    
    @property
    def audit_logger(self):
        return None
