from __future__ import annotations

import base64
from datetime import datetime, timezone
from io import BytesIO
import json
import os
import re
from urllib.request import Request, urlopen
import uuid
from typing import Any, Dict, List, Optional
from agents.manegerial.node import generate_hr_question
from agents.resume_based.node import generate_resume_question
from agents.supervisor.node import plan_session_next_step
from agents.technical_coding.node import generate_coding_question
from agents.shared import build_llm, safe_json_parse

try:
    from pypdf import PdfReader
except ImportError:  # optional dependency in local dev
    PdfReader = None

try:
    from redis import Redis
except ImportError:  # optional dependency in local dev
    Redis = None


SESSION_STORE: Dict[str, Dict[str, Any]] = {}
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "7200"))
REDIS_URL = os.getenv("REDIS_URL", "").strip()

_REDIS_CLIENT = Redis.from_url(REDIS_URL, decode_responses=True) if Redis and REDIS_URL else None

AGENT_ORDER: List[str] = ["code", "resume", "hr"]
ROUND_LABELS = {
    "code": "technical problem-solving",
    "resume": "your past experience",
    "hr": "behavioral and collaboration topics",
}
ROUND_TYPE_LABELS = {
    "tech-dsa": "data structures and algorithms",
    "system-design": "system design",
    "managerial": "behavioral and managerial discussion",
    "resume-based": "your past experience",
}
ROUND_TYPE_TO_AGENT = {
    "tech-dsa": "code",
    "system-design": "code",
    "managerial": "hr",
    "resume-based": "resume",
}
ROUND_TYPE_ALIASES = {
    "tech-resume": "resume-based",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _session_key(session_id: str) -> str:
    return f"session:{session_id}"


def _persist_session(session: Dict[str, Any]) -> None:
    session_id = session["session_id"]
    if _REDIS_CLIENT:
        _REDIS_CLIENT.set(_session_key(session_id), json.dumps(session), ex=SESSION_TTL_SECONDS)
        return
    SESSION_STORE[session_id] = session


def _fetch_session(session_id: str) -> Optional[Dict[str, Any]]:
    if _REDIS_CLIENT:
        raw = _REDIS_CLIENT.get(_session_key(session_id))
        return json.loads(raw) if raw else None
    return SESSION_STORE.get(session_id)


def _parse_resume_text(text: str) -> Dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    skill_tokens: List[str] = []
    for line in lines:
        if "skill" in line.lower():
            skill_tokens.extend([token.strip() for token in line.split(":")[-1].split(",")])
    return {
        "skills": [token for token in skill_tokens if token][:8],
        "experience_years": 0,
        "projects": [],
        "education": [],
        "claimed_strengths": [],
    }


def _extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    if not pdf_bytes or PdfReader is None:
        return ""
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages).strip()
    except Exception:
        return ""


def _extract_resume_text(resume_content: Dict[str, Any]) -> str:
    if not isinstance(resume_content, dict):
        return ""
    content_format = (resume_content.get("format") or "text").strip().lower()
    raw_data = resume_content.get("data") or ""
    if not raw_data:
        return ""

    if content_format == "text":
        return str(raw_data).strip()

    if content_format == "pdf_base64":
        try:
            pdf_bytes = base64.b64decode(raw_data, validate=False)
        except Exception:
            return ""
        return _extract_text_from_pdf_bytes(pdf_bytes)

    if content_format == "url":
        try:
            request = Request(
                str(raw_data),
                headers={"User-Agent": "MockInterviewAI/1.0 (+resume-ingestion)"},
            )
            with urlopen(request, timeout=8) as response:
                data = response.read()
                content_type = (response.headers.get("Content-Type") or "").lower()
            if "pdf" in content_type or str(raw_data).lower().endswith(".pdf"):
                return _extract_text_from_pdf_bytes(data)
            decoded = data.decode("utf-8", errors="ignore")
            return decoded.strip()
        except Exception:
            return ""

    return str(raw_data).strip()


def _parse_resume_with_llm(resume_text: str) -> Dict[str, Any]:
    llm = build_llm()
    if llm is None or not resume_text.strip():
        return {}

    prompt = f"""
You are extracting structured resume details for an interview assistant.
Return valid JSON only with this schema:
{{
  "skills": ["..."],
  "experience_years": 0,
  "projects": ["..."],
  "education": ["..."],
  "claimed_strengths": ["..."],
  "topics": ["..."],
  "summary": "..."
}}

Rules:
- Infer concise interview-relevant topics from the resume (max 12 topics).
- Keep each list short and de-duplicated.
- "experience_years" should be an integer if inferable, else 0.
- No markdown, no commentary.

Resume text:
{resume_text[:12000]}
""".strip()

    try:
        response = llm.invoke(prompt)
        parsed = safe_json_parse(response.content if hasattr(response, "content") else str(response))
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        return {}
    return {}


def _merge_resume_parsed(parsed_resume: Dict[str, Any], llm_resume: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(parsed_resume or {})
    for key in ["skills", "projects", "education", "claimed_strengths", "topics"]:
        values = llm_resume.get(key) if isinstance(llm_resume, dict) else None
        if isinstance(values, list):
            cleaned = [str(item).strip() for item in values if str(item).strip()]
            if cleaned:
                merged[key] = cleaned[:12]

    exp_years = llm_resume.get("experience_years") if isinstance(llm_resume, dict) else None
    if isinstance(exp_years, (int, float)) and exp_years >= 0:
        merged["experience_years"] = int(exp_years)
    elif isinstance(exp_years, str):
        match = re.search(r"\d+", exp_years)
        if match:
            merged["experience_years"] = int(match.group())

    summary = llm_resume.get("summary") if isinstance(llm_resume, dict) else None
    if isinstance(summary, str) and summary.strip():
        merged["summary"] = summary.strip()

    return merged


def _log_event(session: Dict[str, Any], event: str, data: Dict[str, Any]) -> None:
    logs = session.setdefault("debug_trace", [])
    logs.append(
        {
            "timestamp": _now_iso(),
            "event": event,
            "turn_counter": session.get("turn_counter"),
            "data": data,
        }
    )


def _pick_non_repeated(pool: List[Dict[str, Any]], asked_topics: List[str], topic_key: str) -> Dict[str, Any]:
    asked_set = set([topic for topic in asked_topics if topic])
    for item in pool:
        topic_value = item.get(topic_key)
        if isinstance(topic_value, list):
            primary = topic_value[0] if topic_value else None
        else:
            primary = topic_value
        if primary not in asked_set:
            return item
    return pool[len(asked_topics) % len(pool)]


def _pick_preferred_item(
    pool: List[Dict[str, Any]],
    asked_topics: List[str],
    topic_key: str,
    preferred_topics: Optional[List[str]] = None,
) -> Dict[str, Any]:
    preferred = [topic.lower() for topic in (preferred_topics or [])]
    if preferred:
        for item in pool:
            topic_value = item.get(topic_key)
            topic_values = topic_value if isinstance(topic_value, list) else [topic_value]
            normalized_values = [str(value).lower() for value in topic_values if value]
            question_text = str(item.get("question_text", "")).lower()
            if any(
                pref in question_text
                or any(pref in value or value in pref for value in normalized_values)
                for pref in preferred
            ):
                return item
    return _pick_non_repeated(pool, asked_topics, topic_key)


def _normalize_round_type(round_type: str) -> str:
    return ROUND_TYPE_ALIASES.get(round_type, round_type)


def _normalize_topics_map(topics: Dict[str, Any]) -> Dict[str, List[str]]:
    normalized: Dict[str, List[str]] = {}
    for round_type, values in (topics or {}).items():
        normalized_round_type = _normalize_round_type(round_type)
        if isinstance(values, list):
            normalized[normalized_round_type] = [str(value) for value in values if str(value).strip()]
        else:
            normalized[normalized_round_type] = []
    return normalized


def _build_round_sequence(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    selected_types = [
        _normalize_round_type(round_type)
        for round_type in payload.get("selected_types", [])
        if _normalize_round_type(round_type) in ROUND_TYPE_TO_AGENT
    ]
    topics_map = _normalize_topics_map(payload.get("topics", {}))

    if not selected_types:
        selected_types = [round_type for round_type in topics_map.keys() if round_type in ROUND_TYPE_TO_AGENT]

    if not selected_types:
        distribution = payload.get("turn_distribution", {})
        for agent_type in AGENT_ORDER:
            if int(distribution.get(agent_type, 0)) <= 0:
                continue
            default_round_type = {
                "code": "tech-dsa",
                "resume": "resume-based",
                "hr": "managerial",
            }[agent_type]
            selected_types.append(default_round_type)

    if not selected_types:
        selected_types = ["tech-dsa"]

    return [
        {
            "round_type": round_type,
            "agent_type": ROUND_TYPE_TO_AGENT[round_type],
            "topics": topics_map.get(round_type, []),
        }
        for round_type in selected_types
    ]


def _build_turn_plan(turn_distribution: Dict[str, int], total_turns: int) -> List[str]:
    remaining = {
        "code": max(0, int(turn_distribution.get("code", 0))),
        "resume": max(0, int(turn_distribution.get("resume", 0))),
        "hr": max(0, int(turn_distribution.get("hr", 0))),
    }
    plan: List[str] = []
    while len(plan) < total_turns and sum(remaining.values()) > 0:
        for agent in AGENT_ORDER:
            if remaining[agent] > 0 and len(plan) < total_turns:
                plan.append(agent)
                remaining[agent] -= 1
    # Fallback if distribution sum is lower than requested turns
    while len(plan) < total_turns:
        plan.append(AGENT_ORDER[len(plan) % len(AGENT_ORDER)])
    return plan


def _expand_round_sequence(round_sequence: List[Dict[str, Any]], total_turns: int) -> List[Dict[str, Any]]:
    if not round_sequence:
        round_sequence = [{"round_type": "tech-dsa", "agent_type": "code", "topics": []}]

    expanded: List[Dict[str, Any]] = []
    idx = 0
    while len(expanded) < total_turns:
        spec = round_sequence[idx % len(round_sequence)]
        expanded.append(
            {
                "round_type": spec["round_type"],
                "agent_type": spec["agent_type"],
                "topics": list(spec.get("topics", [])),
            }
        )
        idx += 1
    return expanded


def _turn_spec(session: Dict[str, Any], turn_counter: int) -> Dict[str, Any]:
    turn_plan = session.get("turn_plan", [])
    if not turn_plan:
        return {"round_type": "tech-dsa", "agent_type": "code", "topics": []}
    index = max(0, min(turn_counter - 1, len(turn_plan) - 1))
    return turn_plan[index]


def _generate_code_question(role: str, company: str, difficulty: str) -> Dict[str, Any]:
    return {
        "agent_type": "code",
        "difficulty": difficulty,
        "input_output_format": {"input": "varies by problem", "output": "varies by problem"},
        "constraints": ["1 <= n <= 1e5"],
        "rubric": {
            "dimensions": [
                {"key": "correctness", "max_score": 5},
                {"key": "complexity", "max_score": 5},
                {"key": "edge_cases", "max_score": 5},
                {"key": "code_quality", "max_score": 5},
            ],
            "max_total": 20,
        },
        "catalog": [
            {
                "topic_tags": ["arrays", "sliding_window"],
                "question_text": f"Given an integer array nums, return the minimum length subarray with sum >= target for a {role} interview at {company}.",
                "examples": [
                    {
                        "input": {"nums": [2, 3, 1, 2, 4, 3], "target": 7},
                        "output": "2",
                        "explanation": "Subarray [4,3] has the minimum length 2 with sum >= 7.",
                    }
                ],
                "test_cases": [
                    {"input": {"nums": [2, 3, 1, 2, 4, 3], "target": 7}, "expected_output": "2"},
                    {"input": {"nums": [1, 1, 1, 1, 1], "target": 11}, "expected_output": "0"},
                ],
                "expected_solution_outline": ["sliding window", "expand right", "shrink left when sum >= target"],
                "time_space_targets": {"expected_time": "O(n)", "expected_space": "O(1)"},
                "followup_questions": [
                    "Why is this valid only for positive integers?",
                    "How would your solution change with negative numbers?",
                ],
            },
            {
                "topic_tags": ["hashmap", "prefix_sum"],
                "question_text": f"Find if a subarray with sum k exists in nums using an approach expected at {company}.",
                "examples": [
                    {
                        "input": {"nums": [1, 2, 3], "k": 5},
                        "output": "true",
                        "explanation": "Subarray [2,3] sums to 5.",
                    }
                ],
                "test_cases": [
                    {"input": {"nums": [1, 2, 3], "k": 5}, "expected_output": "true"},
                    {"input": {"nums": [1, 2, 3], "k": 7}, "expected_output": "false"},
                ],
                "expected_solution_outline": ["prefix sum", "hashmap lookup"],
                "time_space_targets": {"expected_time": "O(n)", "expected_space": "O(n)"},
                "followup_questions": [
                    "How do you handle repeated prefix sums?",
                    "Can this be optimized for memory?",
                ],
            },
            {
                "topic_tags": ["two_pointers", "strings"],
                "question_text": f"Given a string, find the longest substring without repeating characters and explain trade-offs.",
                "examples": [
                    {
                        "input": {"s": "abcabcbb"},
                        "output": "3",
                        "explanation": "Longest substring without repeating chars is 'abc', length 3.",
                    }
                ],
                "test_cases": [
                    {"input": {"s": "abcabcbb"}, "expected_output": "3"},
                    {"input": {"s": "bbbbb"}, "expected_output": "1"},
                ],
                "expected_solution_outline": ["two pointers", "character index map"],
                "time_space_targets": {"expected_time": "O(n)", "expected_space": "O(1)/O(k)"},
                "followup_questions": [
                    "What changes for unicode input?",
                    "How would you return the substring itself?",
                ],
            },
            {
                "topic_tags": ["intervals", "sorting"],
                "question_text": "Merge overlapping intervals and discuss why sorting first is needed.",
                "examples": [
                    {
                        "input": {"intervals": [[1, 3], [2, 6], [8, 10], [15, 18]]},
                        "output": "[[1,6],[8,10],[15,18]]",
                        "explanation": "After sorting by start, merge [1,3] and [2,6].",
                    }
                ],
                "test_cases": [
                    {"input": {"intervals": [[1, 3], [2, 6], [8, 10], [15, 18]]}, "expected_output": "[[1,6],[8,10],[15,18]]"},
                    {"input": {"intervals": [[1, 4], [4, 5]]}, "expected_output": "[[1,5]]"},
                ],
                "expected_solution_outline": ["sort by start", "merge sweep"],
                "time_space_targets": {"expected_time": "O(n log n)", "expected_space": "O(n)"},
                "followup_questions": [
                    "Can you do this in-place?",
                    "How do you prove correctness?",
                ],
            },
        ],
    }


def _generate_resume_question() -> Dict[str, Any]:
    return {
        "agent_type": "resume",
        "expected_framework": "STAR",
        "rubric": {
            "dimensions": [
                {"key": "situation_clarity", "max_score": 5},
                {"key": "action_ownership", "max_score": 5},
                {"key": "result_quantified", "max_score": 5},
                {"key": "honesty_depth", "max_score": 5},
            ],
            "max_total": 20,
        },
        "catalog": [
            {
                "topic_tag": "project_challenges",
                "question_text": "Tell me about a real project challenge from your resume and walk through Situation, Task, Action, and Result.",
                "followup_questions": [
                    "What would you do differently next time?",
                    "What metric proved success?",
                ],
            },
            {
                "topic_tag": "teamwork",
                "question_text": "Describe a time you had a team disagreement and how you resolved it.",
                "followup_questions": [
                    "What did you learn about communication?",
                    "How did your solution impact delivery?",
                ],
            },
            {
                "topic_tag": "ownership",
                "question_text": "Tell me about a feature where you took end-to-end ownership.",
                "followup_questions": [
                    "How did you prioritize trade-offs?",
                    "What metrics did you monitor post-release?",
                ],
            },
        ],
    }


def _generate_hr_question() -> Dict[str, Any]:
    return {
        "agent_type": "hr",
        "rubric": {
            "dimensions": [
                {"key": "self_awareness", "max_score": 5},
                {"key": "communication", "max_score": 5},
                {"key": "proactiveness", "max_score": 5},
                {"key": "outcome_focus", "max_score": 5},
            ],
            "max_total": 20,
        },
        "catalog": [
            {
                "topic_tag": "adaptability",
                "question_text": "Describe a situation where project requirements changed suddenly. How did you adapt?",
                "followup_questions": [
                    "How did your communication style help in this situation?",
                    "What did you learn that changed your approach afterwards?",
                ],
            },
            {
                "topic_tag": "conflict_resolution",
                "question_text": "Tell me about a conflict with a teammate and how you resolved it.",
                "followup_questions": [
                    "What would you handle differently now?",
                    "How did you prevent recurring conflict?",
                ],
            },
            {
                "topic_tag": "culture_fit",
                "question_text": "What kind of team culture helps you do your best work, and why?",
                "followup_questions": [
                    "How do you adapt when culture differs from preference?",
                    "Give one example from past internships or projects.",
                ],
            },
        ],
    }


def _generate_question(
    agent_type: str,
    role: str,
    company: str,
    difficulty: str,
    asked_topics: List[str],
    preferred_topics: Optional[List[str]] = None,
) -> Dict[str, Any]:
    if agent_type == "code":
        base = _generate_code_question(role, company, difficulty)
        selected = _pick_preferred_item(base["catalog"], asked_topics, "topic_tags", preferred_topics)
        return {
            "question_id": f"Q_CODE_{uuid.uuid4().hex[:6]}",
            "core_question_text": selected["question_text"],
            **{k: v for k, v in base.items() if k != "catalog"},
            **selected,
        }
    if agent_type == "resume":
        base = _generate_resume_question()
        selected = _pick_preferred_item(base["catalog"], asked_topics, "topic_tag", preferred_topics)
        return {
            "question_id": f"Q_RES_{uuid.uuid4().hex[:6]}",
            "core_question_text": selected["question_text"],
            **{k: v for k, v in base.items() if k != "catalog"},
            **selected,
        }
    base = _generate_hr_question()
    selected = _pick_preferred_item(base["catalog"], asked_topics, "topic_tag", preferred_topics)
    return {
        "question_id": f"Q_HR_{uuid.uuid4().hex[:6]}",
        "core_question_text": selected["question_text"],
        **{k: v for k, v in base.items() if k != "catalog"},
        **selected,
    }


def _generate_system_design_question(role: str, company: str, preferred_topics: Optional[List[str]] = None) -> Dict[str, Any]:
    topic_hint = preferred_topics[0] if preferred_topics else "scalable notification delivery"
    return {
        "question_id": f"Q_SYS_{uuid.uuid4().hex[:6]}",
        "agent_type": "code",
        "round_type": "system-design",
        "difficulty": "medium",
        "topic_tags": [topic_hint.lower().replace(" ", "_"), "system_design"],
        "question_text": f"Design a {topic_hint} system for a {role} interview at {company}. Walk through requirements, APIs, data model, scaling bottlenecks, caching, and trade-offs.",
        "core_question_text": f"Design a {topic_hint} system for a {role} interview at {company}. Walk through requirements, APIs, data model, scaling bottlenecks, caching, and trade-offs.",
        "input_output_format": {"input": "product requirements and traffic assumptions", "output": "high-level and detailed system design"},
        "constraints": ["Discuss scale assumptions", "Cover trade-offs", "Address bottlenecks and failure modes"],
        "rubric": {
            "dimensions": [
                {"key": "requirements_clarity", "max_score": 5},
                {"key": "architecture_quality", "max_score": 5},
                {"key": "scaling_tradeoffs", "max_score": 5},
                {"key": "communication", "max_score": 5},
            ],
            "max_total": 20,
        },
        "followup_questions": [
            "What would become the first bottleneck as traffic grows 10x?",
            "How would you change the design for stronger consistency guarantees?",
        ],
    }


def _resume_summary(session: Dict[str, Any]) -> str:
    parsed_resume = session.get("candidate", {}).get("resume_parsed", {})
    skills = ", ".join(parsed_resume.get("skills", [])[:6]) or "No explicit skills listed"
    projects = ", ".join(parsed_resume.get("projects", [])[:3]) or "No projects captured"
    topics = ", ".join(parsed_resume.get("topics", [])[:6]) or "No resume topics inferred"
    llm_summary = parsed_resume.get("summary") or ""
    base = (
        f"Skills: {skills}. Projects: {projects}. "
        f"Experience years: {parsed_resume.get('experience_years', 0)}. "
        f"Interview topics: {topics}."
    )
    return f"{base} Summary: {llm_summary}".strip()


def _generate_question_from_agent(
    session: Dict[str, Any],
    agent_type: Optional[str] = None,
    round_spec: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    round_spec = round_spec or _turn_spec(session, session.get("turn_counter", 1))
    agent_type = agent_type or round_spec.get("agent_type", "code")
    round_type = round_spec.get("round_type", "tech-dsa")
    selected_topics = round_spec.get("topics", [])
    coverage = session.get("coverage_context", {})
    role = session["interview_config"]["role"]
    company = session["interview_config"]["company"]
    experience = session["interview_config"].get("experience", 0)
    job_description = session["interview_config"].get("jd", "")
    difficulty = session["interview_config"]["difficulty"]

    try:
        if agent_type == "code":
            question_pack = generate_coding_question({
                "request_id": f"REQ_{uuid.uuid4().hex[:8]}",
                "session_id": session["session_id"],
                "turn_id": session.get("pending_turn_id"),
                "task": "generate_coding_question",
                "company": company,
                "role": role,
                "experience": experience,
                "job_description": job_description,
                "difficulty": difficulty,
                "round_type": round_type,
                "language_preference": session["interview_config"].get("language_preference", "python"),
                "coverage_context": coverage,
                "constraints": {
                    "question_type": "system_design" if round_type == "system-design" else "dsa",
                    "must_include_followups": True,
                    "max_time_minutes": 25,
                    "needs_test_cases": True,
                    "should_be_interview_realistic": True,
                    "selected_topics": selected_topics,
                },
            })
        elif agent_type == "resume":
            question_pack = generate_resume_question({
                "company": company,
                "role": role,
                "experience": experience,
                "coverage_context": coverage,
                "resume_summary": _resume_summary(session),
                "job_description": job_description,
                "preferred_topics": selected_topics,
            })
        else:
            question_pack = generate_hr_question({
                "company": company,
                "role": role,
                "experience": experience,
                "coverage_context": coverage,
                "job_description": job_description,
                "preferred_topics": selected_topics,
            })

        if question_pack:
            question_pack.setdefault("agent_type", agent_type)
            question_pack.setdefault("round_type", round_type)
            question_pack.setdefault("selected_topics", selected_topics)
            question_pack.setdefault("core_question_text", question_pack.get("question_text", ""))
            question_pack.setdefault("followup_questions", [])
            if agent_type == "code":
                examples = question_pack.get("examples", []) or []
                if "test_cases" not in question_pack and examples:
                    question_pack["test_cases"] = [
                        {
                            "input": example.get("input"),
                            "expected_output": example.get("output"),
                        }
                        for example in examples
                        if example.get("output") is not None
                    ]
            return question_pack
    except Exception:
        pass

    if agent_type == "code" and round_type == "system-design":
        return _generate_system_design_question(role, company, selected_topics)

    return _generate_question(
        agent_type,
        role,
        company,
        difficulty,
        coverage.get("already_asked_topics", []),
        preferred_topics=selected_topics,
    )


def _round_label(agent_type: str) -> str:
    return ROUND_LABELS.get(agent_type, "the interview")


def _round_type_label(round_type: str, agent_type: str) -> str:
    return ROUND_TYPE_LABELS.get(round_type, _round_label(agent_type))


def _candidate_first_name(session: Dict[str, Any]) -> str:
    name = (session.get("candidate", {}).get("name") or "there").strip()
    return name.split()[0] if name else "there"


def _candidate_signaled_stuck(answer_text: str) -> bool:
    normalized = " ".join((answer_text or "").lower().split())
    if not normalized:
        return True

    stuck_phrases = [
        "i don't know",
        "i dont know",
        "do not know",
        "not sure",
        "no idea",
        "i have no idea",
        "i'm not sure",
        "im not sure",
        "can't remember",
        "cannot remember",
        "don't remember",
        "do not remember",
        "blanking",
        "skip this",
        "pass on this",
        "move on",
    ]
    return any(phrase in normalized for phrase in stuck_phrases)


def _decorate_question_text(
    session: Dict[str, Any],
    question_pack: Dict[str, Any],
    intro_style: str,
    supervisor_decision: Optional[Dict[str, Any]] = None,
    previous_agent: Optional[str] = None,
    evaluation: Optional[Dict[str, Any]] = None,
    answer_text: str = "",
) -> Dict[str, Any]:
    core_question = question_pack.get("core_question_text") or question_pack.get("question_text", "")
    agent_type = question_pack.get("agent_type", session.get("current_agent", "code"))
    round_type = question_pack.get("round_type", session.get("current_round_type", "tech-dsa"))
    candidate_first_name = _candidate_first_name(session)
    company = session.get("interview_config", {}).get("company", "the company")
    role = session.get("interview_config", {}).get("role", "this role")
    transition_target = _round_type_label(round_type, agent_type)

    if intro_style == "opening":
        prefix = (
            f"Hi {candidate_first_name}, thanks for joining today. "
            f"I'd like to keep this conversational and aligned to a {role} interview at {company}. "
            f"let's begin with {transition_target}. "
        )
    elif supervisor_decision:
        acknowledgement = (supervisor_decision.get("acknowledgement") or "").strip()
        transition = (supervisor_decision.get("transition") or "").strip()
        prefix = " ".join(part for part in [acknowledgement, transition] if part).strip()
        if prefix:
            prefix = f"{prefix} "
    else:
        word_count = len(answer_text.split())
        score_pct = (evaluation or {}).get("percentage", 0)
        if word_count < 20:
            acknowledgement = "Thanks. I want to hear a bit more depth from you. "
        elif score_pct >= 85:
            acknowledgement = "Nice, that was a strong explanation. "
        elif score_pct >= 65:
            acknowledgement = "Thanks, that was helpful. "
        else:
            acknowledgement = "I see the direction you were taking. "

        if previous_agent and previous_agent != agent_type:
            transition = f"Let's switch gears a bit and move into {transition_target}. "
        else:
            transition = f"Let's stay with {transition_target} for the next one. "
        prefix = acknowledgement + transition

    decorated = dict(question_pack)
    decorated["question_text"] = f"{prefix}{core_question}".strip()
    return decorated


def _should_ask_followup(
    question_pack: Dict[str, Any],
    answer_text: str,
    evaluation: Dict[str, Any],
) -> bool:
    if _candidate_signaled_stuck(answer_text):
        return False
    if question_pack.get("is_followup"):
        return False
    followups = question_pack.get("followup_questions", [])
    if not followups:
        return False

    word_count = len(answer_text.split())
    score_pct = evaluation.get("percentage", 0)
    weak_signals = evaluation.get("topics_demonstrated_weak", [])
    return word_count < 35 or score_pct < 65 or bool(weak_signals)


def _build_followup_question(
    session: Dict[str, Any],
    previous_question_pack: Dict[str, Any],
    evaluation: Dict[str, Any],
    answer_text: str,
    supervisor_decision: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    followup_questions = previous_question_pack.get("followup_questions", [])
    followup_text = followup_questions[0] if followup_questions else previous_question_pack.get("core_question_text", "")
    if len(answer_text.split()) < 20:
        followup_text = f"Can you make that more concrete? {followup_text}"

    followup_pack = dict(previous_question_pack)
    followup_pack["question_id"] = f"Q_FUP_{uuid.uuid4().hex[:6]}"
    followup_pack["core_question_text"] = followup_text
    followup_pack["question_text"] = followup_text
    followup_pack["is_followup"] = True
    followup_pack["parent_question_id"] = previous_question_pack.get("question_id")
    followup_pack["followup_questions"] = followup_questions[1:]

    return _decorate_question_text(
        session,
        followup_pack,
        intro_style="followup",
        supervisor_decision=supervisor_decision,
        previous_agent=previous_question_pack.get("agent_type"),
        evaluation=evaluation,
        answer_text=answer_text,
    )


def _score_from_answer(answer_text: str, max_score: int) -> int:
    words = len(answer_text.split())
    if words >= 120:
        return max_score
    if words >= 80:
        return max(1, max_score - 1)
    if words >= 40:
        return max(1, max_score - 2)
    if words >= 20:
        return max(1, max_score - 3)
    return 1


def _evaluate_answer(agent_type: str, answer_text: str, question_pack: Dict[str, Any]) -> Dict[str, Any]:
    rubric_dims = question_pack.get("rubric", {}).get("dimensions", [])
    scores: Dict[str, Dict[str, Any]] = {}
    total = 0
    max_total = 0
    for dim in rubric_dims:
        key = dim["key"]
        max_score = int(dim.get("max_score", 5))
        score = _score_from_answer(answer_text, max_score)
        scores[key] = {
            "score": score,
            "max": max_score,
            "comment": f"{key.replace('_', ' ').title()} evaluated for {agent_type} answer.",
        }
        total += score
        max_total += max_score

    percentage = round((total / max_total) * 100) if max_total else 0
    weak_tags = [key for key, item in scores.items() if item["score"] <= max(1, item["max"] // 2)]
    strong_tags = [key for key, item in scores.items() if item["score"] >= item["max"] - 1]
    verdict = "excellent" if percentage >= 85 else "good" if percentage >= 70 else "average" if percentage >= 50 else "poor"

    return {
        "scores": scores,
        "total_score": total,
        "max_score": max_total,
        "percentage": percentage,
        "verdict": verdict,
        "feedback_summary": f"{agent_type.upper()} rubric evaluation completed.",
        "suggested_improvements": [f"Improve {tag.replace('_', ' ')}." for tag in weak_tags[:3]],
        "topics_demonstrated_weak": weak_tags,
        "topics_demonstrated_strong": strong_tags,
    }


def _compute_final_scores(session: Dict[str, Any]) -> Dict[str, Any]:
    grouped: Dict[str, List[int]] = {"code": [], "resume": [], "hr": []}
    for turn in session["turns"]:
        grouped[turn["agent_type"]].append(turn["evaluation"]["percentage"])

    domain_scores: Dict[str, Any] = {}
    all_scores: List[int] = []
    for key in ["code", "resume", "hr"]:
        if grouped[key]:
            avg = round(sum(grouped[key]) / len(grouped[key]), 2)
            domain_scores[key] = {
                "score": avg,
                "turns_evaluated": len(grouped[key]),
                "verdict": "strong" if avg >= 80 else "good" if avg >= 65 else "needs_improvement",
            }
            all_scores.extend(grouped[key])
        else:
            domain_scores[key] = {"score": None, "turns_evaluated": 0, "verdict": None}

    overall = round(sum(all_scores) / len(all_scores), 2) if all_scores else None
    domain_scores["overall"] = overall
    return domain_scores


def _next_agent(session: Dict[str, Any], next_turn_counter: int) -> str:
    return _turn_spec(session, next_turn_counter).get("agent_type", "code")


def _resolve_next_turn_spec(
    session: Dict[str, Any],
    next_turn_counter: int,
    requested_agent: Optional[str] = None,
) -> Dict[str, Any]:
    planned_spec = _turn_spec(session, next_turn_counter)
    if not requested_agent or planned_spec.get("agent_type") == requested_agent:
        return planned_spec

    for spec in session.get("turn_plan", [])[max(0, next_turn_counter - 1):]:
        if spec.get("agent_type") == requested_agent:
            return spec

    round_type = {
        "code": "tech-dsa",
        "resume": "resume-based",
        "hr": "managerial",
    }.get(requested_agent, "tech-dsa")
    preferred_topics = session.get("interview_config", {}).get("topics", {}).get(round_type, [])
    return {
        "round_type": round_type,
        "agent_type": requested_agent or "code",
        "topics": preferred_topics,
    }


def start_session(payload: Dict[str, Any]) -> Dict[str, Any]:
    session_id = f"S_{uuid.uuid4().hex[:8]}"
    resume_content = payload.get("resume_content", {}) or {}
    resume_text = _extract_resume_text(resume_content)
    parsed_resume = _parse_resume_text(resume_text)
    llm_resume = _parse_resume_with_llm(resume_text)
    parsed_resume = _merge_resume_parsed(parsed_resume, llm_resume)
    created_at = _now_iso()

    payload_topics = _normalize_topics_map(payload.get("topics", {}))
    inferred_resume_topics = parsed_resume.get("topics", []) if isinstance(parsed_resume, dict) else []
    if inferred_resume_topics:
        existing_resume_topics = payload_topics.get("resume-based", [])
        merged_topics: List[str] = []
        seen = set()
        for topic in [*existing_resume_topics, *inferred_resume_topics]:
            normalized = str(topic).strip()
            if not normalized:
                continue
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            merged_topics.append(normalized)
        payload_topics["resume-based"] = merged_topics[:12]

    payload_with_resume_topics = dict(payload)
    payload_with_resume_topics["topics"] = payload_topics

    round_sequence = _build_round_sequence(payload_with_resume_topics)
    turn_plan = _expand_round_sequence(round_sequence, payload["total_turns_planned"])
    first_turn_spec = turn_plan[0] if turn_plan else {"round_type": "tech-dsa", "agent_type": "code", "topics": []}
    first_agent = first_turn_spec["agent_type"]
    session = {
        "session_id": session_id,
        "created_at": created_at,
        "status": "active",
        "candidate": {
            "user_id": payload["user_id"],
            "name": payload["candidate_name"],
            "resume_parsed": parsed_resume,
            "resume": payload.get("resume"),
        },
        "interview_config": {
            "company": payload["company"],
            "role": payload["role"],
            "experience": payload.get("experience", 0),
            "jd": payload.get("jd"),
            "difficulty": payload["difficulty"],
            "language_preference": payload["language_preference"],
            "total_turns_planned": payload["total_turns_planned"],
            "turn_distribution": payload["turn_distribution"],
            "selected_types": payload.get("selected_types", []),
            "topics": payload_topics,
        },
        "round_sequence": round_sequence,
        "turn_plan": turn_plan,
        "turn_counter": 1,
        "current_agent": first_agent,
        "current_round_type": first_turn_spec["round_type"],
        "current_turn_spec": first_turn_spec,
        "coverage_context": {
            "already_asked_topics": [],
            "avoid_topics": [],
            "weakness_tags": [],
            "strength_tags": [],
        },
        "turns": [],
        "final_scores": {
            "code": {"score": None, "turns_evaluated": 0, "verdict": None},
            "resume": {"score": None, "turns_evaluated": 0, "verdict": None},
            "hr": {"score": None, "turns_evaluated": 0, "verdict": None},
            "overall": None,
        },
        "pending_turn_id": f"T_{1:03d}",
        "latest_question": None,
        "locked": False,
        "request_cache": {},
        "debug_trace": [],
    }
    session["latest_question"] = _decorate_question_text(
        session,
        _generate_question_from_agent(session, first_agent, first_turn_spec),
        intro_style="opening",
    )
    _log_event(
        session,
        "session_started",
        {
            "session_id": session_id,
            "turn_plan": turn_plan,
            "inferred_resume_topics": inferred_resume_topics,
            "first_question": session["latest_question"],
        },
    )
    _persist_session(session)
    return session


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    return _fetch_session(session_id)


def submit_answer(session_id: str, answer_payload: Dict[str, Any]) -> Dict[str, Any]:
    session = _fetch_session(session_id)
    if not session:
        raise ValueError("Session not found")
    if session["status"] != "active":
        raise ValueError("Session is not active")
    if session["locked"]:
        raise RuntimeError("Session is locked while evaluating another answer")

    request_id = answer_payload.get("request_id")
    if request_id and request_id in session["request_cache"]:
        return session

    session["locked"] = True
    try:
        current_turn_spec = session.get("current_turn_spec") or _turn_spec(session, session.get("turn_counter", 1))
        agent_type = current_turn_spec.get("agent_type", session["current_agent"])
        question_pack = session["latest_question"] or _generate_question_from_agent(session, agent_type, current_turn_spec)
        _log_event(
            session,
            "answer_received",
            {
                "agent_type": agent_type,
                "turn_id": session["pending_turn_id"],
                "question_id": question_pack["question_id"],
                "request_id": request_id,
                "answer_preview": answer_payload["answer_text"][:120],
            },
        )
        evaluation = _evaluate_answer(agent_type, answer_payload["answer_text"], question_pack)
        _log_event(
            session,
            "evaluation_completed",
            {
                "question_id": question_pack["question_id"],
                "agent_type": agent_type,
                "evaluation": evaluation,
                "followups": question_pack.get("followup_questions", []),
            },
        )
        turn = {
            "turn_id": session["pending_turn_id"],
            "agent_type": agent_type,
            "round_type": current_turn_spec.get("round_type"),
            "question_id": question_pack["question_id"],
            "question_text": question_pack["question_text"],
            "question_pack": question_pack,
            "user_answer_transcript": answer_payload["answer_text"],
            "evaluation": evaluation,
            "completed_at": _now_iso(),
        }
        session["turns"].append(turn)
        primary_topic = question_pack.get("topic_tag")
        if not primary_topic:
            tags = question_pack.get("topic_tags", [])
            primary_topic = tags[0] if tags else ""
        session["coverage_context"]["already_asked_topics"].append(primary_topic)

        if evaluation["topics_demonstrated_weak"]:
            session["coverage_context"]["weakness_tags"].extend(
                evaluation["topics_demonstrated_weak"]
            )
        if evaluation["topics_demonstrated_strong"]:
            session["coverage_context"]["strength_tags"].extend(
                evaluation["topics_demonstrated_strong"]
            )

        if session["turn_counter"] >= session["interview_config"]["total_turns_planned"]:
            session["status"] = "completed"
            session["final_scores"] = _compute_final_scores(session)
            session["latest_question"] = None
            session["pending_turn_id"] = None
            if request_id:
                session["request_cache"][request_id] = turn["turn_id"]
            _log_event(
                session,
                "session_completed",
                {"final_scores": session["final_scores"], "total_turns": len(session["turns"])},
            )
            _persist_session(session)
            return session

        supervisor_decision = plan_session_next_step(session, turn, evaluation)
        if _candidate_signaled_stuck(answer_payload["answer_text"]) and supervisor_decision["action"] == "follow_up":
            fallback_next_agent = _next_agent(session, session["turn_counter"] + 1)
            supervisor_decision = {
                "action": "ask_question" if fallback_next_agent == agent_type else "switch_round",
                "next_agent": fallback_next_agent,
                "focus": "move_on",
                "acknowledgement": "That's okay.",
                "transition": (
                    "Let's leave that one and try a different question."
                    if fallback_next_agent == agent_type
                    else f"Let's move on and switch into {_round_label(fallback_next_agent)}."
                ),
                "reason": "Session safeguard prevented repeated follow-up after candidate said they were stuck.",
            }
        elif supervisor_decision["action"] == "follow_up" and not _should_ask_followup(
            question_pack,
            answer_payload["answer_text"],
            evaluation,
        ):
            fallback_next_agent = _next_agent(session, session["turn_counter"] + 1)
            supervisor_decision = {
                "action": "ask_question" if fallback_next_agent == agent_type else "switch_round",
                "next_agent": fallback_next_agent,
                "focus": "coverage",
                "acknowledgement": "Thanks, that helps.",
                "transition": (
                    "Let's take a fresh question in this area."
                    if fallback_next_agent == agent_type
                    else f"Let's switch gears and move into {_round_label(fallback_next_agent)}."
                ),
                "reason": "Session safeguard prevented repeated follow-up chaining on the same question thread.",
            }
        session.setdefault("supervisor_history", []).append(
            {
                "turn_id": turn["turn_id"],
                "decision": supervisor_decision,
                "timestamp": _now_iso(),
            }
        )

        if supervisor_decision["action"] == "end_interview":
            session["status"] = "completed"
            session["final_scores"] = _compute_final_scores(session)
            session["latest_question"] = None
            session["pending_turn_id"] = None
            if request_id:
                session["request_cache"][request_id] = turn["turn_id"]
            _log_event(
                session,
                "session_completed",
                {
                    "final_scores": session["final_scores"],
                    "total_turns": len(session["turns"]),
                    "reason": supervisor_decision.get("reason"),
                },
            )
            _persist_session(session)
            return session

        session["turn_counter"] += 1
        session["pending_turn_id"] = f"T_{session['turn_counter']:03d}"

        if supervisor_decision["action"] == "follow_up":
            session["current_agent"] = agent_type
            session["current_round_type"] = current_turn_spec.get("round_type", session.get("current_round_type"))
            session["current_turn_spec"] = {
                "round_type": current_turn_spec.get("round_type", session.get("current_round_type", "tech-dsa")),
                "agent_type": agent_type,
                "topics": list(current_turn_spec.get("topics", [])),
            }
            session["latest_question"] = _build_followup_question(
                session,
                question_pack,
                evaluation,
                answer_payload["answer_text"],
                supervisor_decision=supervisor_decision,
            )
        else:
            next_turn_spec = _resolve_next_turn_spec(
                session,
                session["turn_counter"],
                supervisor_decision.get("next_agent"),
            )
            session["current_agent"] = next_turn_spec["agent_type"]
            session["current_round_type"] = next_turn_spec["round_type"]
            session["current_turn_spec"] = next_turn_spec
            session["latest_question"] = _decorate_question_text(
                session,
                _generate_question_from_agent(session, session["current_agent"], next_turn_spec),
                intro_style="transition",
                supervisor_decision=supervisor_decision,
                previous_agent=agent_type,
                evaluation=evaluation,
                answer_text=answer_payload["answer_text"],
            )
        _log_event(
            session,
            "next_question_generated",
            {
                "next_agent": session["current_agent"],
                "next_turn_id": session["pending_turn_id"],
                "supervisor_decision": supervisor_decision,
                "question": session["latest_question"],
            },
        )
        if request_id:
            session["request_cache"][request_id] = turn["turn_id"]
        _persist_session(session)
        return session
    finally:
        session["locked"] = False
        _persist_session(session)


def end_session(session_id: str, reason: str) -> Dict[str, Any]:
    session = _fetch_session(session_id)
    if not session:
        raise ValueError("Session not found")
    if session["status"] != "completed":
        session["status"] = "aborted" if reason in {"aborted", "manual_end"} else "completed"
        session["final_scores"] = _compute_final_scores(session)
        _log_event(
            session,
            "session_ended",
            {"reason": reason, "status": session["status"], "final_scores": session["final_scores"]},
        )
        _persist_session(session)
    return session
