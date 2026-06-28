from typing import List, Dict, Any

class MCPClient:
    """
    Client for interacting with local MCP (Model Context Protocol) servers.
    """
    def __init__(self, server_url: str):
        self.server_url = server_url

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]):
        # TODO: Implement MCP tool call
        pass

class ToolRegistry:
    """
    Registry of available local security tools.
    """
    def __init__(self):
        self.tools = {
            "mitre_lookup": "Lookup MITRE ATT&CK techniques",
            "sigma_validator": "Validate Sigma rules",
            "whois_lookup": "Local WHOIS cache lookup"
        }

    def get_available_tools(self) -> Dict[str, str]:
        return self.tools
