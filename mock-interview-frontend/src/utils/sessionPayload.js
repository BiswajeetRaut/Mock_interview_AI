const ROUND_TYPE_ALIASES = {
  "tech-resume": "resume-based",
};

const ROUND_TYPE_TO_AGENT = {
  "tech-dsa": "code",
  "system-design": "code",
  managerial: "hr",
  "resume-based": "resume",
};

export const normalizeRoundType = (roundType) =>
  ROUND_TYPE_ALIASES[roundType] || roundType;

export const normalizeTopicsMap = (topics = {}, selectedTypes = []) => {
  const orderedTypes = selectedTypes.length
    ? selectedTypes
    : Object.keys(topics || {});
  return orderedTypes.reduce((acc, roundType) => {
    const normalizedType = normalizeRoundType(roundType);
    acc[normalizedType] = [
      ...(topics?.[roundType] || topics?.[normalizedType] || []),
    ];
    return acc;
  }, {});
};

export const buildTurnDistributionFromTypes = (
  selectedTypes = [],
  totalTurns = 8,
) => {
  const distribution = { code: 0, resume: 0, hr: 0 };
  const normalized = selectedTypes.length ? selectedTypes : ["tech-dsa"];

  // Round-robin distribute totalTurns across the selected types,
  // exactly matching the backend's _expand_round_sequence logic.
  for (let i = 0; i < totalTurns; i++) {
    const roundType = normalized[i % normalized.length];
    const agentType =
      ROUND_TYPE_TO_AGENT[normalizeRoundType(roundType)] || "code";
    distribution[agentType] += 1;
  }

  return distribution;
};

const readResumeContent = async (resume, jd = "") => {
  if (!resume) {
    return jd || "";
  }

  if (typeof resume === "string") {
    return resume || jd || "";
  }

  if (typeof resume.text === "function") {
    const textLikeTypes = ["text/plain", "application/json"];
    if (textLikeTypes.includes(resume.type)) {
      try {
        return await resume.text();
      } catch {
        return `Uploaded resume file: ${resume.name}`;
      }
    }
  }

  return `Uploaded resume file: ${resume.name}`;
};

export const buildSessionStartPayload = async ({
  company,
  role,
  experience = 0,
  jd = "",
  resume = null,
  selectedTypes = [],
  topics = {},
  candidateName = "Candidate",
}) => {
  const totalTurnsPlanned = 8;
  const normalizedSelectedTypes = selectedTypes.map(normalizeRoundType);
  const normalizedTopics = normalizeTopicsMap(topics, normalizedSelectedTypes);
  const turnDistribution = buildTurnDistributionFromTypes(
    normalizedSelectedTypes,
    totalTurnsPlanned,
  );
  const resumeData = await readResumeContent(resume, jd);

  return {
    user_id: "anonymous",
    candidate_name: candidateName,
    company,
    role,
    experience,
    jd,
    resume: resume?.name || resume || null,
    selected_types: normalizedSelectedTypes,
    topics: normalizedTopics,
    difficulty: "medium",
    language_preference: "python",
    total_turns_planned: totalTurnsPlanned,
    turn_distribution: turnDistribution,
    resume_content: {
      format: "text",
      data: resumeData,
    },
  };
};
