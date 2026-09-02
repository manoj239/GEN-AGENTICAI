from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI

# =====================================================
# LLM
# =====================================================

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key="YOUR_API_KEY"
)

# =====================================================
# GRAPH STATE
# =====================================================

class DeploymentState(TypedDict):
    deployment_request: str
    pipeline_status: str
    infrastructure_health: str
    incident_status: str
    final_recommendation: str

# =====================================================
# AGENT 1
# PIPELINE ANALYSIS
# =====================================================

def pipeline_analysis(state: DeploymentState):
    response = llm.invoke(
        f""" Analyze the deployment pipeline for the following request:

        {state['deployment_request']}

        Assume you have access to CI/CD information.

        Provide:
        - Build Status
        - Test Status
        - Deployment Readiness
        """
    )

    return {
        "pipeline_status": response.content
    }

# =====================================================
# AGENT 2
# INFRASTRUCTURE HEALTH
# =====================================================

def infrastructure_health(state: DeploymentState):

    response = llm.invoke(
        f"""
        Analyze infrastructure readiness
        for this deployment request:

        {state['deployment_request']}

        Review:
        - CPU
        - Memory
        - Disk
        - Service Health

        Provide recommendations.
        """
    )

    return {
        "infrastructure_health": response.content
    }

# =====================================================
# AGENT 3
# INCIDENT REVIEW
# =====================================================

def incident_review(state: DeploymentState):

    response = llm.invoke(
        f"""
        Review operational risks
        for this deployment request:

        {state['deployment_request']}

        Analyze:
        - Open Incidents
        - Major Alerts
        - Operational Risks
        """
    )

    return {
        "incident_status": response.content
    }

# =====================================================
# AGGREGATOR
# =====================================================

def deployment_recommendation(state: DeploymentState):

    report = f"""
PRODUCTION DEPLOYMENT ASSESSMENT

PIPELINE STATUS
---------------
{state["pipeline_status"]}

INFRASTRUCTURE HEALTH
---------------------
{state["infrastructure_health"]}

INCIDENT ANALYSIS
-----------------
{state["incident_status"]}

FINAL RECOMMENDATION
--------------------
Based on pipeline readiness,
infrastructure health,
and incident analysis,
determine whether deployment
should proceed.
"""

    recommendation = llm.invoke(report)

    return {
        "final_recommendation":
        recommendation.content
    }

# =====================================================
# BUILD GRAPH
# =====================================================

builder = StateGraph(DeploymentState)

builder.add_node("pipeline_analysis", pipeline_analysis)

builder.add_node("infrastructure_health", infrastructure_health)

builder.add_node("incident_review", incident_review)

builder.add_node("deployment_recommendation", deployment_recommendation)

# Fan-Out

builder.add_edge(START,"pipeline_analysis")

builder.add_edge(START,"infrastructure_health")

builder.add_edge(START,"incident_review")

# Fan-In

builder.add_edge("pipeline_analysis","deployment_recommendation")

builder.add_edge("infrastructure_health","deployment_recommendation")

builder.add_edge("incident_review","deployment_recommendation")

builder.add_edge("deployment_recommendation",END)

graph = builder.compile()

# =====================================================
# INVOKE
# =====================================================

result = graph.invoke(
    {
        "deployment_request":
        """
        Release Version: v2.5

        Production Deployment

        Application:
        Payment Service
        """
    }
)

print(result["final_recommendation"])

"""
In this LangGraph workflow, different agents perform specialized checks in parallel. The Pipeline
Analysis Agent verifies CI/CD readiness, the Infrastructure Health Agent validates server health,
and the Incident Analysis Agent checks open incidents and operational risks. Their outputs are
aggregated by a Deployment Recommendation Agent, which provides a final Go or No-Go decision for
production deployment.
"""
