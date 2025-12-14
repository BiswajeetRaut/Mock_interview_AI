"""Supervisor Graph - Orchestrates the interview workflow using LangGraph.

This module builds a state graph that manages the flow between different interview agents
(Technical, Resume, HR) controlled by a Supervisor agent that makes routing decisions.
"""

from langgraph.graph import StateGraph, END
from .state import InterviewState
from .node import supervisor_node


def router(state: InterviewState) -> str:
    """Routes to the next node based on supervisor decision.

    Args:
        state: Current interview state containing supervisor decision

    Returns:
        str: Next node name (TECHNICAL, RESUME, HR) or END to terminate
    """
    d = state["supervisor_decision"]

    # ✅ HARD STOP CONDITIONS
    if state["time_remaining"] <= 0:
        return END

    if d["action"] == "end_interview":
        return END

    return d["next_agent"].upper()


def build_graph(technical_node, resume_node, hr_node):
    """Builds and compiles the interview workflow graph.

    Creates a state graph with four nodes:
    - SUPERVISOR: Makes routing decisions
    - TECHNICAL: Technical interview agent
    - RESUME: Resume-based interview agent
    - HR: HR/behavioral interview agent

    Args:
        technical_node: Callable for technical agent
        resume_node: Callable for resume agent
        hr_node: Callable for HR agent

    Returns:
        Compiled graph ready for execution
    """
    graph = StateGraph(InterviewState)

    graph.add_node("SUPERVISOR", supervisor_node)
    graph.add_node("TECHNICAL", technical_node)
    graph.add_node("RESUME", resume_node)
    graph.add_node("HR", hr_node)

    graph.set_entry_point("SUPERVISOR")

    graph.add_edge("TECHNICAL", "SUPERVISOR")
    graph.add_edge("RESUME", "SUPERVISOR")
    graph.add_edge("HR", "SUPERVISOR")

    graph.add_conditional_edges(
        "SUPERVISOR",
        router,
        {
            "TECHNICAL": "TECHNICAL",
            "RESUME": "RESUME",
            "HR": "HR",
            END: END
        }
    )

    return graph.compile()
