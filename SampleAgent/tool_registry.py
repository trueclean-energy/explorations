from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Any, Callable, Optional
import os

class ToolCategory(Enum):
    DATA_PROCESSING = "data_processing"
    EXTERNAL_API = "external_api"
    FILE_OPERATION = "file_operation"
    CALCULATION = "calculation"

@dataclass
class Tool:
    name: str
    description: str
    category: ToolCategory
    function: Optional[Callable]
    parameters: Dict[str, Dict[str, Any]]
    required_params: List[str]

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate that all required parameters are present"""
        return all(param in params for param in self.required_params)

    def execute(self, **params) -> Any:
        """Execute the tool with given parameters"""
        if not self.validate_params(params):
            missing = [p for p in self.required_params if p not in params]
            raise ValueError(f"Missing required parameters: {missing}")
        
        if not self.function:
            raise ValueError(f"Tool {self.name} has no implementation")
        
        return self.function(**params)

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
    
    def register_tool(self, tool: Tool) -> None:
        """Register a new tool"""
        self.tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name"""
        return self.tools.get(name)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools with their metadata"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "category": tool.category.value,
                "parameters": tool.parameters,
                "required_params": tool.required_params
            }
            for tool in self.tools.values()
        ]

    def list_tools_by_category(self, category: ToolCategory) -> List[Dict[str, Any]]:
        """List tools filtered by category"""
        return [
            tool_info for tool_info in self.list_tools()
            if tool_info["category"] == category.value
        ] 