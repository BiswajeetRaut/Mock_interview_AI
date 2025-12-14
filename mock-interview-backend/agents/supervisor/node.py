"""Supervisor Node - Makes intelligent routing decisions for the interview.

The supervisor analyzes the current interview state and latest agent report,
then uses an LLM to decide which agent should go next and what action to take.
"""

import json
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from .prompt import SUPERVISOR_PROMPT
from .logic import update_state_from_report
from .state import InterviewState

# Load environment variables from .env file
load_dotenv()

# Initialize the LLM for supervisor decision-making
llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)


def supervisor_node(state: InterviewState) -> InterviewState:
    """Process interview state and make routing decision.

    Analyzes the current interview context and latest agent feedback,
    then uses an LLM to decide the next agent and action.

    Args:
        state: Current interview state

    Returns:
        Updated state with supervisor decision
    """
    report = state.get("latest_agent_report")

    prompt_input = {
        "state": {
            "current_round": state["current_round"],
            "difficulty": state["difficulty"],
            "target_signal": state["target_signal"],
            "weakness_map": state["weakness_map"],
            "time_remaining": state["time_remaining"]
        },
        "agent_report": report
    }

    response = llm.invoke(
        SUPERVISOR_PROMPT.format_messages(**prompt_input)).content
    print(f"📋 Supervisor Response: {response}")

    decision = json.loads(response)
    print(f"📊 Parsed Decision: {decision}")

    update_state_from_report(state, report)

    state["supervisor_decision"] = decision
    state["latest_agent_report"] = None

    return state
