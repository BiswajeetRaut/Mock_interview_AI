# agents/technical_coding/graph.py
from langgraph.graph import StateGraph, END
from agents.technical_coding.state import CodeAgentState
from agents.technical_coding.node import generate_coding_question_node


def build_code_question_graph():
    g = StateGraph(CodeAgentState)

    g.add_node("generate_question", generate_coding_question_node)
    g.set_entry_point("generate_question")
    g.add_edge("generate_question", END)

    return g.compile()
