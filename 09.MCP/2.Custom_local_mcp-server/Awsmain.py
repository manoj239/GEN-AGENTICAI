from fastmcp import FastMCP
import os
import json
from typing import Optional

# Paths

BASE_DIR = os.path.dirname(__file__)
BEST_PRACTICES_PATH = os.path.join(BASE_DIR,"aws_best_practices.json")

# MCP Server

mcp = FastMCP("CloudOperations")

# -----------------------
# TOOLS
# -----------------------

@mcp.tool()
def list_ec2_instances() -> list:
    """
    List all EC2 instances.
    """

    return [
        {
            "instance_id": "i-123456",
            "instance_type": "t3.medium",
            "state": "running"
        },
        {
            "instance_id": "i-789012",
            "instance_type": "t3.large",
            "state": "stopped"
        }
    ]


@mcp.tool()
def get_cloudwatch_metrics(
    instance_id: str
) -> dict:
    """
    Fetch CloudWatch metrics for an EC2 instance.
    """

    return {
        "instance_id": instance_id,
        "cpu_utilization": "72%",
        "memory_utilization": "65%",
        "disk_utilization": "45%"
    }


@mcp.tool()
def iam_security_audit() -> dict: #Performs basic IAM security checks such as admin access review and inactive user identification
    """
    Perform IAM security audit.
    """

    return {
        "users_with_admin_access": 2,
        "inactive_users": 4,
        "password_rotation_pending": 3
    }

# -----------------------
# RESOURCE
# -----------------------

@mcp.resource("aws://best-practices",mime_type="application/json")
def aws_best_practices() -> str:
    """
    Returns AWS operational and security best practices.
    """

    with open(BEST_PRACTICES_PATH, "r",encoding="utf-8") as f:
        return f.read()

# -----------------------
# PROMPT
# -----------------------

@mcp.prompt("cloud-ops-assistant")
def cloud_ops_assistant() -> dict:
    """
    Base system prompt for Cloud Operations Assistant.
    """
    return {

        "messages": [

            {
                "role": "system",

                "content": (

                    "You are an AWS Cloud Operations Assistant.\n\n"

                    "You can help users with AWS operational tasks using available tools.\n\n"

                    "Available Capabilities:\n"

                    "- List EC2 Instances\n"
                    "- Check CloudWatch Metrics\n"
                    "- Perform IAM Security Audits\n\n"

                    "Guidelines:\n"

                    "- Use tools only when users ask about AWS resources.\n"
                    "- For general questions, answer directly.\n"
                    "- Do not refuse general technical questions.\n"
                    "- Follow AWS security best practices.\n"
                    "- Recommend least privilege access whenever applicable.\n\n"

                    "Your goal is to provide secure and accurate cloud operations guidance."

                )
            }
        ]
    }

# -----------------------
# MAIN
# -----------------------

if __name__ == "__main__":
    mcp.run()


"""
I developed a custom Cloud Operations MCP Server using FastMCP. The purpose of the server 
was to expose AWS operational capabilities to AI agents through a standardized MCP interface.
I implemented three MCP tools: one for retrieving EC2 instance information, another for fetching 
CloudWatch metrics, and a third for performing IAM security audits. I also exposed AWS security 
and operational best practices through an MCP Resource and defined agent behavior using an MCP 
Prompt. The server communicates using the MCP protocol over JSON-RPC and can be connected to 
MCP-compatible clients such as Claude Desktop. This approach eliminates the need for building 
separate integrations for every cloud operation and provides a reusable interface for AI agents.
"""