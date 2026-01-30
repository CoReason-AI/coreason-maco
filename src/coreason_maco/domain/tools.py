from abc import ABC, abstractmethod
from typing import Any, Dict

class ToolRegistry(ABC):
    """Abstract Base Class for a Tool Registry."""
    
    @abstractmethod
    async def execute(self, tool_name: str, arguments: Dict[str, Any], **kwargs: Any) -> Any:
        """
        Execute a tool.
        Renamed from 'execute_tool' to 'execute' to match Controller expectations.
        """
        pass
