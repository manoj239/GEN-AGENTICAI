from typing_extensions import TypedDict, Literal
from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

# --------------------------------
# LLM
# --------------------------------

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key="YOUR_API_KEY"
)

# --------------------------------
# Structured Output
# --------------------------------

class Route(BaseModel):
    team: Literal["linux","network","database"] = Field(
        description="Team responsible for handling the incident")

router_llm = llm.with_structured_output(Route)

# --------------------------------
# State
# --------------------------------

class IncidentState(TypedDict):
    incident: str
    team: str
    response: str

# --------------------------------
# Linux Team
# --------------------------------

def linux_agent(state: IncidentState):

    msg = llm.invoke(
        f"""
        You are a Linux Support Engineer.

        Analyze the incident:

        {state['incident']}

        Provide:
        - Probable Cause
        - Checks to Perform
        - Resolution Steps
        """
    )

    return {"response": msg.content}

# --------------------------------
# Network Team
# --------------------------------

def network_agent(state: IncidentState):

    msg = llm.invoke(
        f"""
        You are a Network Engineer.

        Analyze the incident:

        {state['incident']}

        Provide:
        - Probable Cause
        - Network Checks
        - Resolution Steps
        """
    )

    return {"response": msg.content}

# --------------------------------
# Database Team
# --------------------------------

def database_agent(state: IncidentState):

    msg = llm.invoke(
        f"""
        You are a Database Administrator.

        Analyze the incident:

        {state['incident']}

        Provide:
        - Root Cause
        - Database Checks
        - Resolution Steps
        """
    )

    return {"response": msg.content}

# --------------------------------
# Router Agent
# --------------------------------

def router_node(state: IncidentState):

    decision = router_llm.invoke(
        [
            SystemMessage(
                content="""
                Classify the incident into one of the following teams:

                linux
                network
                database
                """
            ),
            HumanMessage(
                content=state["incident"]
            )
        ]
    )

    return {"team": decision.team}

# --------------------------------
# Routing Logic
# --------------------------------

def route_incident(state: IncidentState):

    if state["team"] == "linux":
        return "linux_agent"

    elif state["team"] == "network":
        return "network_agent"

    elif state["team"] == "database":
        return "database_agent"

# --------------------------------
# Build Graph
# --------------------------------

builder = StateGraph(IncidentState)

builder.add_node(
    "router",
    router_node
)

builder.add_node(
    "linux_agent",
    linux_agent
)

builder.add_node(
    "network_agent",
    network_agent
)

builder.add_node(
    "database_agent",
    database_agent
)

builder.add_edge(
    START,
    "router"
)

builder.add_conditional_edges(
    "router",
    route_incident,
    {
        "linux_agent": "linux_agent",
        "network_agent": "network_agent",
        "database_agent": "database_agent"
    }
)

builder.add_edge(
    "linux_agent",
    END
)

builder.add_edge(
    "network_agent",
    END
)

builder.add_edge(
    "database_agent",
    END
)

graph = builder.compile()

# --------------------------------
# Invoke
# --------------------------------

result = graph.invoke(
    {
        "incident":
        """
        Users are experiencing packet loss and
        cannot connect to the application.
        Multiple ping requests are timing out.
        """
    }
)

print(result["response"])

"""I built a LangGraph-based Intelligent Incident Routing Assistant for a 24×7 support 
environment. A Router Agent first analyzes incoming incidents and classifies them into Linux, 
Network, or Database categories using structured outputs. Based on the classification, LangGraph 
uses conditional routing to send the incident to the appropriate specialist agent. Each agent 
performs domain-specific diagnosis and generates troubleshooting recommendations. This reduces
manual ticket triage effort and helps route incidents to the correct team more efficiently."""