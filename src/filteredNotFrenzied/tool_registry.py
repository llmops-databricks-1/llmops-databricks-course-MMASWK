from typing import Any

from loguru import logger

from filteredNotFrenzied.mcp import ToolInfo


class ToolRegistry:
    """Registry for managing agent tools."""

    def __init__(self):
        self._tools: dict[str, ToolInfo] = {}

    def register(self, tool: ToolInfo) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
        logger.info(f"✓ Registered tool: {tool.name}")

    def get_tool(self, name: str) -> ToolInfo:
        """Get a tool by name."""
        if name not in self._tools:
            raise ValueError(f"Tool not found: {name}")
        return self._tools[name]

    def get_all_specs(self) -> list[dict]:
        """Get all tool specifications."""
        return [tool.spec for tool in self._tools.values()]

    def execute(self, name: str, args: dict) -> Any:  # noqa: ANN401
        """Execute a tool with arguments."""
        tool = self.get_tool(name)
        return tool.exec_fn(**args)

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def get_all_tools(self) -> list[ToolInfo]:
        """Get all tools as a list."""
        return list(self._tools.values())
