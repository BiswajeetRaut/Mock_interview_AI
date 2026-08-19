"""
Interactive CLI interviewer powered by the session engine.

Run:
    python cli_interview.py

Optional:
    python cli_interview.py --company AMD --role "SDE Intern" --turns 6 --show-logs
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict

from services.session_engine import end_session, get_session, start_session, submit_answer


def _build_start_payload(args: argparse.Namespace) -> Dict[str, Any]:
    code_turns = max(0, args.code_turns)
    resume_turns = max(0, args.resume_turns)
    hr_turns = max(0, args.hr_turns)

    total_turns = args.turns
    if code_turns + resume_turns + hr_turns == 0:
        # default distribution
        code_turns, resume_turns, hr_turns = 3, 2, 1
    if total_turns <= 0:
        total_turns = code_turns + resume_turns + hr_turns

    return {
        "user_id": args.user_id,
        "candidate_name": args.name,
        "company": args.company,
        "role": args.role,
        "difficulty": args.difficulty,
        "language_preference": args.language,
        "total_turns_planned": total_turns,
        "turn_distribution": {
            "code": code_turns,
            "resume": resume_turns,
            "hr": hr_turns,
        },
        "resume_content": {
            "format": "text",
            "data": args.resume_text,
        },
    }


def _print_question(session: Dict[str, Any]) -> None:
    question = session.get("latest_question")
    if not question:
        return

    print("\n" + "=" * 72)
    print(
        f"Turn {session.get('turn_counter')} | Agent: {session.get('current_agent', '').upper()}"
    )
    print("-" * 72)
    print(question.get("question_text", ""))
    followups = question.get("followup_questions", [])
    if followups:
        print("\nPotential follow-ups:")
        for idx, item in enumerate(followups, start=1):
            print(f"  {idx}. {item}")
    print("=" * 72)


def _print_turn_evaluation(session: Dict[str, Any]) -> None:
    if not session.get("turns"):
        return
    last_turn = session["turns"][-1]
    eval_obj = last_turn.get("evaluation", {})

    print("\n📊 Evaluation")
    print(f"Question ID: {last_turn.get('question_id')}")
    print(
        f"Score: {eval_obj.get('total_score')}/{eval_obj.get('max_score')} ({eval_obj.get('percentage')}%)"
    )
    print(f"Verdict: {eval_obj.get('verdict')}")
    print(f"Summary: {eval_obj.get('feedback_summary')}")

    scores = eval_obj.get("scores", {})
    if scores:
        print("Dimensions:")
        for key, item in scores.items():
            print(f"  - {key}: {item.get('score')}/{item.get('max')} | {item.get('comment', '')}")

    weak = eval_obj.get("topics_demonstrated_weak", [])
    strong = eval_obj.get("topics_demonstrated_strong", [])
    if weak:
        print("Weak tags:", ", ".join(weak))
    if strong:
        print("Strong tags:", ", ".join(strong))


def _print_final_report(session: Dict[str, Any]) -> None:
    print("\n" + "#" * 72)
    print("INTERVIEW COMPLETE")
    print("#" * 72)
    print(f"Status: {session.get('status')}")
    print(f"Session: {session.get('session_id')}")
    print(f"Candidate: {session.get('candidate', {}).get('name')}")
    print(f"Company/Role: {session.get('interview_config', {}).get('company')} / {session.get('interview_config', {}).get('role')}")
    print(f"Total turns answered: {len(session.get('turns', []))}")
    print("Final scores:")
    print(json.dumps(session.get("final_scores", {}), indent=2))
    print("#" * 72)


def run_cli(args: argparse.Namespace) -> None:
    payload = _build_start_payload(args)
    session = start_session(payload, owner_uid="cli_dev_user")

    print("\n🚀 Mock Interview CLI Started")
    print(f"Session ID: {session['session_id']}")
    print(f"Planned turn distribution: {payload['turn_distribution']}")
    print(f"Total turns planned: {payload['total_turns_planned']}")

    while session.get("status") == "active" and session.get("latest_question"):
        _print_question(session)
        answer = input("\nYour answer (or type /end to finish early):\n> ").strip()
        if not answer:
            print("⚠️ Empty answer ignored. Please answer or use /end.")
            continue
        if answer.lower() == "/end":
            session = end_session(session["session_id"], "manual_end")
            break

        request_id = f"CLI_REQ_{session['turn_counter']}"
        session = submit_answer(
            session["session_id"],
            {
                "answer_text": answer,
                "request_id": request_id,
                "language": args.language,
            },
        )
        _print_turn_evaluation(session)

    # Pull the latest session snapshot from store (Redis/memory)
    latest = get_session(session["session_id"]) or session
    _print_final_report(latest)

    if args.show_logs:
        print("\n🧾 Debug trace")
        print(json.dumps(latest.get("debug_trace", []), indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a complete interview in CLI mode.")
    parser.add_argument("--user-id", default="cli_user")
    parser.add_argument("--name", default="CLI Candidate")
    parser.add_argument("--company", default="AMD")
    parser.add_argument("--role", default="SDE Intern")
    parser.add_argument("--difficulty", default="medium", choices=["easy", "medium", "hard"])
    parser.add_argument("--language", default="python")
    parser.add_argument("--resume-text", default="Skills: Python, C++, React")
    parser.add_argument("--turns", type=int, default=6)
    parser.add_argument("--code-turns", type=int, default=2)
    parser.add_argument("--resume-turns", type=int, default=2)
    parser.add_argument("--hr-turns", type=int, default=2)
    parser.add_argument(
        "--show-logs",
        action="store_true",
        help="Print full debug_trace logs at the end.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    run_cli(parse_args())
