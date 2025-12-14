def hr_agent_node(state):
    state["latest_agent_report"] = {
        "domain": "HR",
        "signals_detected": ["communication"],
        "signals_missed": ["conflict_handling"]
    }
    state["time_remaining"] -= 5
    return state
