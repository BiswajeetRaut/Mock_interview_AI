"""
CLI test runner for Supervisor Agent (LangGraph).
Run with:
    python test_supervisor_cli.py
"""

from agents.manegerial.node import hr_agent_node
from agents.resume_based.node import resume_agent_node
from agents.technical_coding.node import technical_agent_node
from agents.supervisor.state import InterviewState
from agents.supervisor.graph import build_graph
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def pretty_print_state(state: InterviewState, step: int):
    print("\n" + "=" * 60)
    print(f"STEP {step}")
    print("=" * 60)
    print("Current Round     :", state["current_round"])
    print("Target Signal     :", state["target_signal"])
    print("Time Remaining    :", state["time_remaining"])
    print("Weakness Map      :", state["weakness_map"])
    print("Strength Map      :", state["strength_map"])
    print("Supervisor Decision:")
    print(state.get("supervisor_decision"))
    print("=" * 60)


def main():
    app = build_graph(
        technical_agent_node,
        resume_agent_node,
        hr_agent_node
    )

    initial_state: InterviewState = {
        "session_id": "CLI_TEST_001",
        "current_round": "technical",
        "difficulty": "medium",
        "target_signal": "optimization",
        "company_style": "Google",
        "weakness_map": {},
        "strength_map": {},
        "time_remaining": 30,
        "latest_agent_report": None,
        "supervisor_decision": None,
        "final_scores": None
    }

    print("\n🚀 Starting Supervisor CLI Test\n")

    final_state = app.invoke(
        initial_state,
        config={"recursion_limit": 20}
    )

    print("\n✅ FINAL STATE")
    print("=" * 60)
    print("Time Remaining:", final_state["time_remaining"])
    print("Weakness Map  :", final_state["weakness_map"])
    print("Strength Map :", final_state["strength_map"])
    print("Last Decision:", final_state["supervisor_decision"])


if __name__ == "__main__":
    main()
