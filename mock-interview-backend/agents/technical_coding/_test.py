# agents/technical_coding/_test.py

import json
from agents.technical_coding import code_question_graph


def pretty(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def build_supervisor_response(state_result: dict):
    return {
        "request_id": state_result.get("request_id"),
        "session_id": state_result.get("session_id"),
        "turn_id": state_result.get("turn_id"),
        "task": state_result.get("task"),
        "agent_type": state_result.get("agent_type", "code"),
        "question_pack": state_result.get("question_pack"),
        "error": state_result.get("error"),
    }


def main():
    payload = {
        "request_id": "REQ_CODE_GEN_001",
        "session_id": "S_9c9b1b3d",
        "turn_id": "T_004",
        "task": "generate_coding_question",
        "company": "AMD",
        "role": "SDE Intern",
        "difficulty": "medium",
        "language_preference": "C++",
        "coverage_context": {
            "already_asked_topics": ["arrays", "hashmap"],
            "avoid_topics": ["arrays"],
            "weakness_tags": ["time_complexity", "edge_cases"],
            "strength_tags": ["basic_logic"],
        },
        "constraints": {
            "question_type": "dsa",
            "must_include_followups": True,
            "max_time_minutes": 25,
            "needs_test_cases": True,
            "should_be_interview_realistic": True,
        },
    }

    result = code_question_graph.invoke(payload)

    print("\n================ RAW GRAPH STATE OUTPUT ================\n")
    pretty(result)

    print("\n================ FINAL SUPERVISOR RESPONSE ================\n")
    final_response = build_supervisor_response(result)
    pretty(final_response)

    if final_response.get("error"):
        print("\n❌ FAILED:", final_response["error"])
    else:
        print("\n✅ SUCCESS: Question pack generated!")


if __name__ == "__main__":
    main()
