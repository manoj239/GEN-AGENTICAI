from fastmcp import FastMCP

# MCP Server
mcp = FastMCP("EnterpriseAssistant")

# ------------------------------------------------
# Jira Tool
# ------------------------------------------------

@mcp.tool()
def get_jira_ticket(ticket_id: str) -> dict:
    """
    Retrieve Jira ticket information.
    """

    # Normally call Jira REST API here

    return {
        "ticket_id": ticket_id,
        "title": "High CPU Utilization",
        "status": "In Progress",
        "assignee": "DevOps Team"
    }

# ------------------------------------------------
# GitHub Tool
# ------------------------------------------------

@mcp.tool()
def get_pull_request(pr_id: int) -> dict:
    """
    Retrieve Pull Request details.
    """

    # Normally call GitHub API here

    return {
        "pr_id": pr_id,
        "repository": "agentic-ai-app",
        "status": "Open",
        "author": "developer1"
    }

# ------------------------------------------------
# Confluence Tool
# ------------------------------------------------

@mcp.tool()
def get_confluence_page(page_id: str) -> dict:
    """
    Retrieve Confluence page information.
    """

    # Normally call Confluence API here

    return {
        "page_id": page_id,
        "title": "CPU Stabilization Runbook",
        "space": "DEVOPS"
    }

# ------------------------------------------------
# Resource
# ------------------------------------------------

@mcp.resource("enterprise://systems")
def systems() -> str:
    return """
Available Enterprise Systems:

- Jira
- GitHub
- Confluence
"""

# ------------------------------------------------
# Prompt
# ------------------------------------------------

@mcp.prompt("enterprise-assistant")
def enterprise_prompt() -> dict:

    return {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an Enterprise AI Assistant.\n"
                    "You can interact with Jira, GitHub, "
                    "and Confluence using available tools.\n"
                    "Use tools whenever enterprise information "
                    "is required."
                )
            }
        ]
    }

# ------------------------------------------------
# Main
# ------------------------------------------------

if __name__ == "__main__":
    mcp.run()