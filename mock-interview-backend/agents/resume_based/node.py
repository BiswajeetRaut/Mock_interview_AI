def resume_agent_node(state):
    state["latest_agent_report"] = {
        "domain": "RESUME",
        "signals_detected": ["ownership"],
        "signals_missed": ["tradeoffs"]
    }
    state["time_remaining"] -= 5
    return state
