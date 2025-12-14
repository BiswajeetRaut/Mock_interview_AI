"""Interview State Update Logic - Processes agent reports to track candidate performance.

This module contains helper functions that update the interview state based on
feedback from individual interview agents.
"""


def update_state_from_report(state, report):
    """Update weakness and strength maps based on agent report.

    Processes a report from an interview agent and updates the state's
    weakness_map and strength_map with detected signals and missed opportunities.

    Args:
        state: Current interview state (modified in-place)
        report: Dict containing agent feedback with 'domain', 'signals_detected',
               and 'signals_missed' keys
    """
    if not report:
        return

    domain = report.get("domain")

    for missed in report.get("signals_missed", []):
        state["weakness_map"].setdefault(domain, [])
        if missed not in state["weakness_map"][domain]:
            state["weakness_map"][domain].append(missed)

    for detected in report.get("signals_detected", []):
        state["strength_map"].setdefault(domain, [])
        if detected not in state["strength_map"][domain]:
            state["strength_map"][domain].append(detected)
