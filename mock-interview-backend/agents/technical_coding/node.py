def technical_agent_node(state):
    state["latest_agent_report"] = {
        "domain": "DSA",
        "signals_detected": ["problem_solving"],
        "signals_missed": ["optimization"]
    }
    state["time_remaining"] -= 5
    return state
