// src/pages/InterviewPage.jsx
import React, { useEffect, useRef, useState } from "react";
import {
  Flex,
  Box,
  HStack,
  Text,
  IconButton,
  Button,
  Textarea,
  Badge,
  Spinner,
} from "@chakra-ui/react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Code as CodeIcon,
  Send,
  Mic,
  MicOff,
  ChevronUp,
  ChevronDown,
} from "lucide-react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import VideoCard from "../components/VideoCard";
import CodingPlayground from "../components/CodingPlayground";
import useMicActivity from "../hooks/useMicActivity";
import {
  endSession,
  fetchSessionReport,
  fetchSessionState,
  submitSessionAnswer,
} from "../api/session.api";
import SpeechRecognition, { useSpeechRecognition } from "react-speech-recognition";
import Speech from "speak-tts";
import { executeCode } from "../api/coding.api";

const MotionBox = motion(Box);

const CODE_TEMPLATES = {
  python: `def solve(input_data):
    # input_data will match each test case "input" payload.
    # Return only the final answer (e.g., int/string/list/dict).
    return None
`,
  javascript: `function solve(inputData) {
  // inputData will match each test case "input" payload.
  // Return only the final answer.
  return null;
}
`,
};

// ── Chat bubble ───────────────────────────────────────────────────────────────
function TranscriptBubble({ entry, isLatest, maxWidth = "82%" }) {
  const isAI = entry.speaker === "AI";
  return (
    <MotionBox
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
      alignSelf={isAI ? "flex-start" : "flex-end"}
      maxW={maxWidth}
    >
      <Flex direction="column" gap="3px" align={isAI ? "flex-start" : "flex-end"}>
        <Text fontSize="10px" color="gray.600" fontWeight="500" letterSpacing="0.04em" px={1}>
          {isAI ? "INTERVIEWER" : "YOU"} · {entry.time}
        </Text>
        <Box
          px={4} py={2.5}
          borderRadius={isAI ? "3px 12px 12px 12px" : "12px 3px 12px 12px"}
          bg={isAI ? "rgba(99,179,237,0.07)" : "rgba(255,255,255,0.055)"}
          border="1px solid"
          borderColor={isAI ? "rgba(99,179,237,0.15)" : "rgba(255,255,255,0.07)"}
          style={isLatest && isAI ? { boxShadow: "0 0 0 1px rgba(99,179,237,0.1)" } : {}}
        >
          <Text
            fontSize="13.5px"
            color={isAI ? "gray.100" : "gray.300"}
            lineHeight="1.65"
            fontWeight={isLatest && isAI ? "500" : "400"}
          >
            {entry.text}
          </Text>
        </Box>
      </Flex>
    </MotionBox>
  );
}

// ── Live speech indicator bar ─────────────────────────────────────────────────
function _LiveSpeechBar({ transcript, listening }) {
  if (!listening) return null;
  return (
    <Box px={3} pb={1.5}>
      <Box
        px={3.5} py={2}
        borderRadius="9px"
        border="1px solid rgba(72,187,120,0.22)"
        bg="rgba(72,187,120,0.04)"
      >
        <HStack spacing={2.5}>
          <HStack spacing="2px" flexShrink={0} h="14px" align="center">
            {[0, 1, 2, 3].map((i) => (
              <Box
                key={i} w="2.5px" borderRadius="full" bg="green.400"
                style={{
                  animation: `soundBar 0.75s ease-in-out ${i * 0.11}s infinite alternate`,
                  minHeight: "3px", maxHeight: "14px",
                }}
              />
            ))}
          </HStack>
          <Text
            fontSize="12px"
            color={transcript?.trim() ? "gray.300" : "gray.600"}
            fontStyle={transcript?.trim() ? "normal" : "italic"}
            flex="1"
            noOfLines={2}
            lineHeight="1.45"
          >
            {transcript?.trim() || "Listening…"}
          </Text>
        </HStack>
      </Box>
    </Box>
  );
}

// ── Mini speaker pill (used in code mode) ─────────────────────────────────────
function MiniVideoCard({ label, speaking, dotColor }) {
  return (
    <HStack
      spacing={2} px={2.5} py={1.5}
      borderRadius="8px"
      border="1px solid"
      borderColor={speaking ? "rgba(99,179,237,0.25)" : "rgba(255,255,255,0.06)"}
      bg={speaking ? "rgba(99,179,237,0.05)" : "rgba(255,255,255,0.025)"}
      transition="all 0.2s"
    >
      <Box
        h="20px" w="20px" borderRadius="full" bg={dotColor}
        display="flex" alignItems="center" justifyContent="center"
        fontSize="9px" fontWeight="700" color="white" flexShrink={0}
        style={speaking ? { boxShadow: `0 0 8px rgba(99,179,237,0.45)` } : {}}
        transition="box-shadow 0.2s"
      />
      <Text fontSize="11px" color={speaking ? "gray.300" : "gray.500"} fontWeight="500">
        {label}
      </Text>
      {speaking && (
        <HStack spacing="2px" h="10px" align="center">
          {[0, 1, 2].map((i) => (
            <Box
              key={i} w="2px" borderRadius="full" bg={dotColor}
              style={{
                animation: `soundBar 0.6s ease-in-out ${i * 0.1}s infinite alternate`,
                minHeight: "3px", maxHeight: "10px",
              }}
            />
          ))}
        </HStack>
      )}
    </HStack>
  );
}

function TypingBubble({ label = "AI is thinking" }) {
  return (
    <MotionBox
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      alignSelf="flex-start"
      maxW="82%"
    >
      <Flex direction="column" gap="3px" align="flex-start">
        <Text fontSize="10px" color="gray.600" fontWeight="500" letterSpacing="0.04em" px={1}>
          INTERVIEWER
        </Text>
        <Box
          px={4}
          py={3}
          borderRadius="3px 12px 12px 12px"
          bg="rgba(99,179,237,0.055)"
          border="1px solid rgba(99,179,237,0.13)"
        >
          <HStack spacing={2.5}>
            <HStack spacing="5px">
              {[0, 1, 2].map((index) => (
                <Box
                  key={index}
                  h="6px"
                  w="6px"
                  borderRadius="full"
                  bg="blue.300"
                  style={{
                    animation: `typingPulse 0.9s ease-in-out ${index * 0.12}s infinite`,
                  }}
                />
              ))}
            </HStack>
            <Text fontSize="12px" color="gray.400">
              {label}
            </Text>
          </HStack>
        </Box>
      </Flex>
    </MotionBox>
  );
}

// ── Answer composer dock (shared between modes) ───────────────────────────────
function AnswerComposer({
  composerExpanded, setComposerExpanded,
  listening, answerDraft, setAnswerDraft,
  textareaRef, handleKeyDown,
  handleRecordToggle, handleSendAnswer, canSend, isSending, awaitingReplyLabel,
}) {
  return (
    <Box flexShrink={0} px={3} pb={3} pt={1.5}>
      <Box
        borderRadius="11px"
        border="1px solid"
        borderColor={listening ? "rgba(99,179,237,0.32)" : "rgba(255,255,255,0.07)"}
        overflow="hidden"
        style={{
          background: "rgba(255,255,255,0.022)",
          transition: "border-color 0.25s ease, box-shadow 0.25s ease",
          boxShadow: listening
            ? "0 0 0 3px rgba(99,179,237,0.055), 0 4px 16px rgba(0,0,0,0.5)"
            : "0 4px 16px rgba(0,0,0,0.38)",
        }}
      >
        {/* Header */}
        <Flex
          px={3.5} py={2}
          align="center" justify="space-between"
          borderBottom={composerExpanded ? "1px solid rgba(255,255,255,0.05)" : "none"}
          cursor="pointer"
          onClick={() => setComposerExpanded((v) => !v)}
          _hover={{ bg: "rgba(255,255,255,0.018)" }}
          transition="background 0.15s"
          userSelect="none"
        >
          <HStack spacing={2}>
            <AnimatePresence mode="wait">
              {listening ? (
                <MotionBox
                  key="rec"
                  initial={{ opacity: 0, scale: 0.85 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.85 }}
                  transition={{ duration: 0.14 }}
                >
                  <HStack spacing={1.5}>
                    <Box position="relative" h="7px" w="7px">
                      <Box
                        position="absolute" inset={0} borderRadius="full" bg="red.400"
                        style={{ animation: "ping 1.2s cubic-bezier(0,0,0.2,1) infinite", opacity: 0.55 }}
                      />
                      <Box position="absolute" inset={0} borderRadius="full" bg="red.400" />
                    </Box>
                    <Text fontSize="10.5px" color="red.400" fontWeight="700" letterSpacing="0.08em">
                      RECORDING
                    </Text>
                  </HStack>
                </MotionBox>
              ) : isSending ? (
                <MotionBox key="sending" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.14 }}>
                  <Text fontSize="11.5px" color="blue.300" fontWeight="500">
                    {awaitingReplyLabel || "Sending answer..."}
                  </Text>
                </MotionBox>
              ) : (
                <MotionBox key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.14 }}>
                  <Text fontSize="11.5px" color="gray.500" fontWeight="500">Your answer</Text>
                </MotionBox>
              )}
            </AnimatePresence>

            {answerDraft && !listening && (
              <Text fontSize="10px" color="gray.600" fontWeight="500">
                {answerDraft.split(/\s+/).filter(Boolean).length}w
              </Text>
            )}
          </HStack>

          <HStack spacing={1.5} onClick={(e) => e.stopPropagation()}>
            <Button
              h="26px" px={3} fontSize="11.5px" fontWeight="600" borderRadius="6px"
              bg={listening ? "rgba(254,178,178,0.09)" : "rgba(255,255,255,0.05)"}
              color={listening ? "red.400" : "gray.400"}
              border="1px solid"
              borderColor={listening ? "rgba(252,129,129,0.22)" : "rgba(255,255,255,0.07)"}
              _hover={{
                bg: listening ? "rgba(254,178,178,0.16)" : "rgba(255,255,255,0.09)",
                color: listening ? "red.300" : "gray.300",
              }}
              leftIcon={listening ? <MicOff size={11} /> : <Mic size={11} />}
              transition="all 0.16s"
              onClick={handleRecordToggle}
              isDisabled={isSending}
            >
              {listening ? "Stop" : "Record"}
            </Button>

            <Button
              h="26px" px={3} fontSize="11.5px" fontWeight="600" borderRadius="6px"
              bg={canSend ? "blue.500" : "rgba(255,255,255,0.04)"}
              color={canSend ? "white" : "gray.600"}
              border="1px solid"
              borderColor={canSend ? "blue.600" : "rgba(255,255,255,0.05)"}
              _hover={canSend ? { bg: "blue.400" } : {}}
              rightIcon={<Send size={10} />}
              isDisabled={!canSend}
              isLoading={isSending}
              loadingText="Sending"
              transition="all 0.18s"
              style={canSend ? { boxShadow: "0 2px 10px rgba(99,179,237,0.28)" } : {}}
              onClick={handleSendAnswer}
            >
              Send
            </Button>

            <IconButton
              aria-label="Toggle composer"
              icon={composerExpanded ? <ChevronDown size={12} /> : <ChevronUp size={12} />}
              h="26px" w="26px" minW="26px"
              bg="transparent" color="gray.600" borderRadius="6px"
              _hover={{ bg: "rgba(255,255,255,0.06)", color: "gray.400" }}
              transition="all 0.14s"
              onClick={() => setComposerExpanded((v) => !v)}
              isDisabled={isSending}
            />
          </HStack>
        </Flex>

        {/* Textarea body */}
        <AnimatePresence initial={false}>
          {composerExpanded && (
            <MotionBox
              key="body"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
              style={{ overflow: "hidden" }}
            >
              <Box px={3.5} pt={2.5} pb={2}>
                <Textarea
                  ref={textareaRef}
                  value={answerDraft}
                  onChange={(e) => setAnswerDraft(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={
                    listening
                      ? "Listening… speak your answer"
                      : "Type your answer or hit Record  ·  ⌘↵ to send"
                  }
                  rows={3}
                  resize="none"
                  isDisabled={isSending}
                  bg="transparent"
                  border="none"
                  p={0}
                  fontSize="13.5px"
                  color={listening ? "gray.200" : "gray.400"}
                  _placeholder={{ color: "gray.600", fontSize: "13px" }}
                  _focus={{ boxShadow: "none", border: "none", outline: "none" }}
                  fontFamily="'DM Sans', sans-serif"
                  lineHeight="1.7"
                  style={{ caretColor: listening ? "#68D391" : "#63B3ED" }}
                />
                <Text fontSize="9.5px" color="gray.700" mt={1} textAlign="right">
                  ⌘↵ to send
                </Text>
              </Box>
            </MotionBox>
          )}
        </AnimatePresence>
      </Box>
    </Box>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function InterviewPage() {
  const { state } = useLocation();
  const { id: idFromParams } = useParams();
  const navigate = useNavigate();
  const { company, role, experience, id: idFromState, session: sessionFromState } = state || {};
  const id = idFromState || idFromParams;

  const [sessionState, setSessionState] = useState(sessionFromState || null);
  const speechRef = useRef(null);
  const lastSpokenAITextRef = useRef("");
  const transcriptEndRef = useRef(null);

  const [showCode, setShowCode] = useState(false);
  const [duration, setDuration] = useState(0);
  const [ttsReady, setTtsReady] = useState(false);
  const [isAISpeaking, setIsAISpeaking] = useState(false);
  const [composerExpanded, setComposerExpanded] = useState(true);
  const [codePanelWidth, setCodePanelWidth] = useState(38);
  const [isSessionLoading, setIsSessionLoading] = useState(!sessionFromState);
  const [isSendingAnswer, setIsSendingAnswer] = useState(false);
  const [isAwaitingReply, setIsAwaitingReply] = useState(false);
  const [isEndingInterview, setIsEndingInterview] = useState(false);
  const textareaRef = useRef(null);
  const codeLayoutRef = useRef(null);
  const codeDragStateRef = useRef({ active: false });

  const [code, setCode] = useState(CODE_TEMPLATES.python);
  const [language, setLanguage] = useState("python");
  const [runResult, setRunResult] = useState(null);
  const [isRunningCode, setIsRunningCode] = useState(false);
  const [isSubmittingCode, setIsSubmittingCode] = useState(false);
  const [isCodingRunnerDisabled, setIsCodingRunnerDisabled] = useState(false);
  const [answerDraft, setAnswerDraft] = useState("");
  const [transcriptEntries, setTranscriptEntries] = useState([]);

  const {
    transcript: speechTranscript,
    finalTranscript,
    listening,
    browserSupportsSpeechRecognition,
    resetTranscript,
  } = useSpeechRecognition();

  const isUserSpeaking = useMicActivity(listening);
  const timestamp = () => new Date().toLocaleTimeString();
  const pickPreferredVoiceName = (voices = []) =>
    voices.find((v) => v?.lang?.toLowerCase().startsWith("en-"))?.name || null;

  const buildTranscriptFromSession = (session) => {
    const entries = (session?.turns || []).flatMap((turn) => ([
      { speaker: "AI", text: turn.question_text, time: turn.completed_at || timestamp() },
      { speaker: "YOU", text: turn.user_answer_transcript, time: turn.completed_at || timestamp() },
    ]));
    const latestQuestion = session?.latest_question?.question_text;
    if (latestQuestion && !entries.some((e) => e.speaker === "AI" && e.text === latestQuestion)) {
      entries.push({ speaker: "AI", text: latestQuestion, time: timestamp() });
    }
    return entries.length
      ? entries
      : [{ speaker: "AI", text: "Welcome! I'm your AI interviewer. Let's begin.", time: timestamp() }];
  };

  useEffect(() => {
    const loadSession = async () => {
      if (!id) return;
      try {
        setIsSessionLoading(true);
        const current = await fetchSessionState(id);
        setSessionState(current);
        setTranscriptEntries(buildTranscriptFromSession(current));
      } catch (err) { console.error(err); }
      finally { setIsSessionLoading(false); }
    };
    if (!sessionFromState) { loadSession(); return; }
    setIsSessionLoading(false);
    setTranscriptEntries(buildTranscriptFromSession(sessionFromState));
  }, [id, sessionFromState]);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcriptEntries]);

  useEffect(() => {
    const t = setInterval(() => setDuration((d) => d + 1), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const speech = new Speech();
    speechRef.current = speech;
    if (!speech.hasBrowserSupport()) return;
    let cancelled = false;
    speech.init({ lang: "en-US", rate: 1, pitch: 1, volume: 1, splitSentences: true })
      .then(({ voices }) => {
        if (cancelled) return;
        const name = pickPreferredVoiceName(voices);
        if (name) { try { speech.setVoice(name); } catch (e) { console.warn(e); } }
        setTtsReady(true);
      }).catch(console.error);
    return () => { cancelled = true; speech.cancel(); setIsAISpeaking(false); };
  }, []);

  useEffect(() => {
    if (!speechTranscript?.trim()) return;
    setAnswerDraft(speechTranscript);
  }, [speechTranscript]);

  useEffect(() => {
    const latestAI = [...transcriptEntries].reverse().find((e) => e.speaker === "AI" && e.text?.trim());
    const next = latestAI?.text?.trim();
    if (!next || !ttsReady || !speechRef.current || next === lastSpokenAITextRef.current) return;
    lastSpokenAITextRef.current = next;
    if (listening) SpeechRecognition.stopListening();
    speechRef.current.speak({
      text: next, queue: false,
      listeners: {
        onstart: () => setIsAISpeaking(true),
        onend: () => setIsAISpeaking(false),
        onerror: () => setIsAISpeaking(false),
      },
    }).catch((e) => { setIsAISpeaking(false); console.error(e); });
  }, [listening, transcriptEntries, ttsReady]);

  useEffect(() => () => {
    speechRef.current?.cancel();
    SpeechRecognition.abortListening();
  }, []);

  useEffect(() => {
    const handlePointerMove = (event) => {
      if (!codeDragStateRef.current.active) return;

      const container = codeLayoutRef.current;
      if (!container) return;

      const rect = container.getBoundingClientRect();
      const nextWidth = ((event.clientX - rect.left) / rect.width) * 100;
      const clampedWidth = Math.min(60, Math.max(28, nextWidth));

      setCodePanelWidth(clampedWidth);
    };

    const stopDragging = () => {
      codeDragStateRef.current.active = false;
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", stopDragging);
    window.addEventListener("pointercancel", stopDragging);

    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", stopDragging);
      window.removeEventListener("pointercancel", stopDragging);
    };
  }, []);

  const formatTime = (s) =>
    `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

  const handleEnd = async () => {
    if (!window.confirm("End the interview?")) return;
    try {
      setIsEndingInterview(true);
      if (!id) return;
      await endSession(id, sessionState?.status === "active" ? "manual_end" : "completed");
      const report = await fetchSessionReport(id);
      navigate("/result-details", {
        state: {
          result: {
            id: report.session_id, company: report.company, role: report.role,
            score: report.overall_score,
            feedback: {
              summary: `Overall verdict: ${report.overall_verdict}`,
              strengths: report.strengths || [],
              improvements: report.improvement_areas || [],
            },
            transcript: (report.detailed_turns || []).flatMap((t) => [
              { speaker: "AI", text: t.question_text },
              { speaker: "YOU", text: t.user_answer_transcript },
            ]),
          },
        },
      });
    } catch (err) { console.error(err); alert("An error occurred."); }
    finally { setIsEndingInterview(false); }
  };

  const handleRecordToggle = () => {
    if (isSendingAnswer) return;
    if (!browserSupportsSpeechRecognition) { alert("Speech recognition not supported."); return; }
    if (speechRef.current) { speechRef.current.cancel(); setIsAISpeaking(false); }
    if (listening) { SpeechRecognition.abortListening(); return; }
    resetTranscript();
    setAnswerDraft("");
    SpeechRecognition.startListening({ continuous: true, language: "en-US" });
    setComposerExpanded(true);
    setTimeout(() => textareaRef.current?.focus(), 100);
  };

  const handleSendAnswer = async () => {
    const answer = answerDraft.trim() || finalTranscript.trim();
    if (!answer || !id || isSendingAnswer) return;
    const optimisticEntryId = globalThis.crypto?.randomUUID?.() || `TMP_${Date.now()}`;
    try {
      setIsSendingAnswer(true);
      setIsAwaitingReply(true);
      speechRef.current?.cancel();
      setIsAISpeaking(false);
      if (listening) SpeechRecognition.abortListening();
      setTranscriptEntries((prev) => [
        ...prev,
        { id: optimisticEntryId, speaker: "YOU", text: answer, time: timestamp() },
      ]);
      setAnswerDraft("");
      resetTranscript();
      const requestId = globalThis.crypto?.randomUUID?.() || `REQ_${Date.now()}`;
      const updated = await submitSessionAnswer(id, answer, requestId);
      setSessionState(updated);
      const nextQ = updated.latest_question?.question_text;
      const done = !nextQ && updated.status !== "active";
      setTranscriptEntries((prev) => [
        ...prev.filter((entry) => entry.id !== optimisticEntryId),
        { speaker: "YOU", text: answer, time: timestamp() },
        {
          speaker: "AI",
          text: done
            ? "Great work — interview complete. End to see your report."
            : nextQ || "Got it. Let's move on.",
          time: timestamp(),
        },
      ]);
    } catch (err) {
      setTranscriptEntries((prev) => prev.filter((entry) => entry.id !== optimisticEntryId));
      setAnswerDraft(answer);
      console.error(err);
      alert("Could not send your answer.");
    } finally {
      setIsSendingAnswer(false);
      setIsAwaitingReply(false);
    }
  };

  const handleKeyDown = (e) => {
    if (isSendingAnswer) return;
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); handleSendAnswer(); }
  };

  const isCodingQuestion = sessionState?.latest_question?.agent_type === "code";
  const codingQuestionPack = sessionState?.latest_question || null;
  const testCases = codingQuestionPack?.test_cases || [];
  const canSend = !!(answerDraft.trim() || finalTranscript.trim()) && !isSendingAnswer;

  useEffect(() => { if (isCodingQuestion) setShowCode(true); }, [isCodingQuestion]);
  useEffect(() => { setRunResult(null); }, [sessionState?.latest_question?.question_id]);
  useEffect(() => {
    setCode((prev) => {
      const trimmed = (prev || "").trim();
      const isTemplate = Object.values(CODE_TEMPLATES).some((t) => t.trim() === trimmed);
      return (!trimmed || isTemplate) ? (CODE_TEMPLATES[language] || CODE_TEMPLATES.python) : prev;
    });
  }, [language]);

  const handleRunCode = async () => {
    if (isCodingRunnerDisabled) return;
    if (!testCases.length) { alert("No test cases available."); return; }
    setIsRunningCode(true);
    try {
      setRunResult(await executeCode({ code, language, test_cases: testCases }));
    } catch (err) {
      if (err?.response?.status === 503) setIsCodingRunnerDisabled(true);
      else alert(err?.response?.data?.detail || "Failed to run code.");
    } finally {
      setIsRunningCode(false);
    }
  };

  const handleSubmitCode = async () => {
    if (!id || !isCodingQuestion) return;
    setIsSubmittingCode(true);

    // Test execution is best-effort: if the runner is disabled or fails,
    // the candidate can still submit their code for the interview to continue.
    let result = runResult;
    if (!result && !isCodingRunnerDisabled) {
      try {
        result = await executeCode({ code, language, test_cases: testCases });
        setRunResult(result);
      } catch (err) {
        if (err?.response?.status === 503) {
          setIsCodingRunnerDisabled(true);
        } else {
          setIsSubmittingCode(false);
          alert(err?.response?.data?.detail || "Failed to run code.");
          return;
        }
      }
    }

    try {
      const summary = result
        ? (result.all_passed
            ? `All ${result.total} test cases passed.`
            : `${result.passed}/${result.total} test cases passed.`)
        : "Test execution is temporarily unavailable — code submitted for review.";
      const requestId = globalThis.crypto?.randomUUID?.() || `REQ_${Date.now()}`;
      setIsAwaitingReply(true);
      const updated = await submitSessionAnswer(id, `Code submission: ${summary}`, requestId, code, language);
      setSessionState(updated);
      const aiReply = updated.latest_question?.question_text || "Code submitted. Let's continue.";
      setTranscriptEntries((prev) => [
        ...prev,
        { speaker: "YOU", text: `Submitted code. ${summary}`, time: timestamp() },
        { speaker: "AI", text: aiReply, time: timestamp() },
      ]);
      setAnswerDraft("");
    } catch (err) { alert(err?.response?.data?.detail || "Failed to submit."); }
    finally {
      setIsSubmittingCode(false);
      setIsAwaitingReply(false);
    }
  };

  const composerProps = {
    composerExpanded, setComposerExpanded, listening,
    answerDraft, setAnswerDraft, textareaRef, handleKeyDown,
    handleRecordToggle, handleSendAnswer, canSend,
    isSending: isSendingAnswer,
    awaitingReplyLabel: isAwaitingReply ? "Waiting for interviewer..." : "",
  };

  const handleCodePanelResizeStart = (event) => {
    event.preventDefault();
    codeDragStateRef.current.active = true;
  };

  if (isSessionLoading && !sessionState) {
    return (
      <Flex
        h="100vh"
        bg="#080a0e"
        color="white"
        align="center"
        justify="center"
        direction="column"
        gap={4}
      >
        <Spinner size="lg" color="blue.300" thickness="3px" />
        <Text fontSize="14px" color="gray.400">Loading interview session...</Text>
      </Flex>
    );
  }

  return (
    <>
      <Flex
        direction="column" h="100vh" bg="#080a0e" color="white"
        overflow="hidden" fontFamily="'DM Sans', 'Helvetica Neue', sans-serif"
      >
        {/* ── TOP BAR ── */}
        <Flex
          px={{ base: 4, md: 6 }} h="52px"
          align="center" justify="space-between" flexShrink={0}
          style={{
            background: "rgba(8,10,14,0.92)",
            backdropFilter: "blur(20px)",
            borderBottom: "1px solid rgba(255,255,255,0.055)",
          }}
        >
          <HStack spacing={3}>
            <Box
              h="30px" w="30px" borderRadius="8px" bg="blue.500" flexShrink={0}
              display="flex" alignItems="center" justifyContent="center"
              fontWeight="700" fontSize="12px" color="white"
              style={{ boxShadow: "0 0 0 1px rgba(99,179,237,0.28)" }}
            >
              AI
            </Box>
            <Box>
              <Text fontSize="13.5px" fontWeight="600" letterSpacing="-0.01em" lineHeight="1.25">
                {company || "Mock Company"}
                <Box as="span" color="gray.700" fontWeight="400" mx={1.5}>·</Box>
                {role || "Interview"}
              </Text>
              <HStack spacing={1.5} mt="1px">
                <Box h="5px" w="5px" borderRadius="full" bg="green.400"
                  style={{ boxShadow: "0 0 5px rgba(72,187,120,0.85)" }} />
                <Text fontSize="10.5px" color="gray.500" letterSpacing="0.03em">
                  LIVE · {formatTime(duration)}{experience && ` · ${experience} yrs`}
                </Text>
              </HStack>
            </Box>
          </HStack>

          <HStack spacing={2}>
            <Button
              h="30px" px={3} fontSize="12px" fontWeight="500" borderRadius="7px"
              bg={showCode ? "rgba(99,179,237,0.1)" : "rgba(255,255,255,0.04)"}
              color={showCode ? "blue.300" : "gray.400"}
              border="1px solid"
              borderColor={showCode ? "rgba(99,179,237,0.25)" : "rgba(255,255,255,0.07)"}
              leftIcon={<CodeIcon size={12} />}
              _hover={{ bg: showCode ? "rgba(99,179,237,0.16)" : "rgba(255,255,255,0.08)", color: showCode ? "blue.200" : "gray.300" }}
              transition="all 0.16s"
              onClick={() => setShowCode((v) => !v)}
            >
              {showCode ? "Hide IDE" : "Open IDE"}
            </Button>
            <Box h="16px" w="1px" bg="rgba(255,255,255,0.07)" />
            <Button
              h="30px" px={4} fontSize="12px" fontWeight="600" borderRadius="7px"
              bg="rgba(254,178,178,0.06)" color="red.400"
              border="1px solid" borderColor="rgba(252,129,129,0.16)"
              _hover={{ bg: "rgba(254,178,178,0.12)", borderColor: "rgba(252,129,129,0.32)", color: "red.300" }}
              _active={{ transform: "scale(0.97)" }}
              transition="all 0.16s"
              onClick={handleEnd}
              isLoading={isEndingInterview}
              loadingText="Ending"
            >
              End Interview
            </Button>
          </HStack>
        </Flex>

        {/* ── BODY ── */}
        <Flex flex="1" overflow="hidden" minH={0}>

          {/* ═══ INTERVIEW MODE ═══ */}
          {!showCode && (
            <Flex
              flex="1"
              minH={0}
              minW={0}
              direction={{ base: "column", xl: "row" }}
              overflow="hidden"
            >
              <Flex
                direction="column"
                flex="1"
                minW={0}
                minH={0}
                p={{ base: 3, md: 4 }}
                gap={4}
              >
                <Flex
                  flex="1"
                  minH={0}
                  direction={{ base: "column", lg: "row" }}
                  gap={4}
                >
                  <VideoCard
                    label="AI"
                    gradient="linear(to-br, blue.400, purple.600)"
                    speaking={isAISpeaking}
                  />
                  <VideoCard
                    label="YOU"
                    gradient="linear(to-br, green.400, teal.600)"
                    speaking={isUserSpeaking}
                  />
                </Flex>

                {/* Session card */}
                <Box
                  px={4} py={3} borderRadius="12px"
                  bg="rgba(255,255,255,0.028)"
                  border="1px solid rgba(255,255,255,0.055)"
                >
                  <Text fontSize="9.5px" color="gray.600" fontWeight="600" letterSpacing="0.07em" textTransform="uppercase" mb={1.5}>
                    Session
                  </Text>
                  <Text fontSize="13px" color="gray.400" lineHeight="1.5" fontWeight="500">
                    {company || "—"} · {role || "—"}
                  </Text>
                  {experience && (
                    <Text fontSize="11px" color="gray.600" mt={0.5}>{experience} yrs exp</Text>
                  )}
                </Box>
                <AnswerComposer {...composerProps} />
              </Flex>

              {/* Transcript rail */}
              <Flex
                direction="column"
                w={{ base: "100%", xl: "360px" }}
                minW={{ xl: "320px" }}
                maxW={{ xl: "400px" }}
                flexShrink={0}
                borderLeft={{ base: "none", xl: "1px solid rgba(255,255,255,0.045)" }}
                borderTop={{ base: "1px solid rgba(255,255,255,0.045)", xl: "none" }}
                bg="rgba(255,255,255,0.018)"
                overflow="hidden"
              >
                <Box
                  px={4}
                  py={3}
                  borderBottom="1px solid rgba(255,255,255,0.05)"
                  flexShrink={0}
                >
                  <Text fontSize="10px" color="gray.600" fontWeight="700" letterSpacing="0.08em" textTransform="uppercase" mb={1.5}>
                    Transcript
                  </Text>
                  <Text fontSize="12px" color="gray.400" lineHeight="1.6">
                    Latest interviewer prompts and your responses stay here while the video stage remains primary.
                  </Text>
                </Box>

                <Flex
                  direction="column" flex="1" overflowY="auto"
                  px={4} pt={4} pb={3} gap={3}
                  sx={{
                    "&::-webkit-scrollbar": { width: "3px" },
                    "&::-webkit-scrollbar-track": { bg: "transparent" },
                    "&::-webkit-scrollbar-thumb": { bg: "rgba(255,255,255,0.07)", borderRadius: "full" },
                  }}
                >
                  {transcriptEntries.map((entry, i) => (
                    <TranscriptBubble
                      key={i} entry={entry}
                      isLatest={i === transcriptEntries.length - 1}
                      maxWidth="100%"
                    />
                  ))}
                  {isAwaitingReply && <TypingBubble label="AI is thinking..." />}
                  <div ref={transcriptEndRef} />
                </Flex>
              </Flex>
            </Flex>
          )}

          {/* ═══ CODE MODE ═══ */}
          {showCode && (
            <Flex ref={codeLayoutRef} flex="1" overflow="hidden" minH={0}>

              {/* Left panel — question + conversation */}
              <Flex
                direction="column"
                w={{ base: "100%", md: `${codePanelWidth}%` }}
                flexShrink={0}
                overflow="hidden"
              >
                {/* Mini speaker pills */}
                <Flex gap={2} px={3} pt={3} pb={2} flexShrink={0}
                  borderBottom="1px solid rgba(255,255,255,0.04)">
                  <MiniVideoCard label="AI" speaking={isAISpeaking} dotColor="blue.400" />
                  <MiniVideoCard label="YOU" speaking={isUserSpeaking} dotColor="green.400" />
                </Flex>

                {/* Scrollable question + hints + history */}
                <Flex
                  direction="column" flex="1" overflowY="auto"
                  px={4} pt={3} pb={2} gap={4}
                  sx={{
                    "&::-webkit-scrollbar": { width: "3px" },
                    "&::-webkit-scrollbar-track": { bg: "transparent" },
                    "&::-webkit-scrollbar-thumb": { bg: "rgba(255,255,255,0.07)", borderRadius: "full" },
                  }}
                >
                  {/* Question */}
                  {sessionState?.latest_question?.question_text && (
                    <Box p={4} borderRadius="11px"
                      bg="rgba(99,179,237,0.055)"
                      border="1px solid rgba(99,179,237,0.13)">
                      <Text fontSize="10px" color="blue.500" fontWeight="700" letterSpacing="0.08em"
                        textTransform="uppercase" mb={2}>
                        Problem
                      </Text>
                      <Text fontSize="13.5px" color="gray.100" lineHeight="1.75" fontWeight="500">
                        {sessionState.latest_question.question_text}
                      </Text>
                      {codingQuestionPack?.topic_tags?.length > 0 && (
                        <HStack spacing={1.5} mt={3} flexWrap="wrap">
                          {codingQuestionPack.topic_tags.map((tag) => (
                            <Badge key={tag} px={2} py="1px" fontSize="10px" borderRadius="5px"
                              bg="rgba(99,179,237,0.1)" color="blue.300"
                              border="1px solid rgba(99,179,237,0.18)">
                              {tag}
                            </Badge>
                          ))}
                        </HStack>
                      )}
                    </Box>
                  )}

                  {/* Examples */}
                  {codingQuestionPack?.examples?.length > 0 && (
                    <Box>
                      <Text fontSize="10.5px" color="gray.500" fontWeight="600" letterSpacing="0.06em"
                        textTransform="uppercase" mb={2}>
                        Examples
                      </Text>
                      {codingQuestionPack.examples.map((ex, i) => (
                        <Box key={i} mb={1.5} p={3} borderRadius="8px"
                          bg="rgba(255,255,255,0.025)"
                          border="1px solid rgba(255,255,255,0.065)"
                          fontFamily="'JetBrains Mono', 'Fira Code', monospace">
                          <Text fontSize="11.5px" color="gray.400">
                            <Box as="span" color="gray.600">in: </Box>
                            <Box as="span" color="gray.200">{JSON.stringify(ex.input)}</Box>
                          </Text>
                          <Text fontSize="11.5px" color="gray.400" mt="2px">
                            <Box as="span" color="gray.600">out: </Box>
                            <Box as="span" color="green.300">{String(ex.output)}</Box>
                          </Text>
                          {ex.explanation && (
                            <Text fontSize="11px" color="gray.500" mt={1.5} lineHeight="1.5"
                              fontFamily="'DM Sans', sans-serif">
                              {ex.explanation}
                            </Text>
                          )}
                        </Box>
                      ))}
                    </Box>
                  )}

                  {/* Function contract */}
                  <Box p={3} borderRadius="8px"
                    bg="rgba(255,255,255,0.018)"
                    border="1px solid rgba(255,255,255,0.055)">
                    <Text fontSize="10.5px" color="gray.600" fontWeight="600" letterSpacing="0.06em"
                      textTransform="uppercase" mb={1.5}>
                      Contract
                    </Text>
                    <Text fontSize="12px" color="gray.400" lineHeight="1.65">
                      Implement{" "}
                      <Box as="code" color="blue.400" fontFamily="monospace" fontSize="11.5px">solve(input_data)</Box>
                      {" "}(Python) or{" "}
                      <Box as="code" color="blue.400" fontFamily="monospace" fontSize="11.5px">solve(inputData)</Box>
                      {" "}(JS). Return the final answer directly.
                    </Text>
                  </Box>

                  {/* Test cases */}
                  {testCases.length > 0 && (
                    <Box>
                      <Flex justify="space-between" align="center" mb={2}>
                        <Text fontSize="10.5px" color="gray.500" fontWeight="600" letterSpacing="0.06em" textTransform="uppercase">
                          Test Cases
                        </Text>
                        {runResult && (
                          <Badge
                            fontSize="10px" px={2} py="1px" borderRadius="5px"
                            bg={runResult.all_passed ? "rgba(72,187,120,0.12)" : "rgba(252,129,129,0.12)"}
                            color={runResult.all_passed ? "green.300" : "red.300"}
                            border="1px solid"
                            borderColor={runResult.all_passed ? "rgba(72,187,120,0.25)" : "rgba(252,129,129,0.25)"}
                          >
                            {runResult.passed}/{runResult.total} passed
                          </Badge>
                        )}
                      </Flex>
                      {testCases.map((tc, i) => {
                        const res = runResult?.results?.[i];
                        const passed = res?.passed;
                        return (
                          <Box key={i} mb={1.5} p={3} borderRadius="8px"
                            bg={typeof passed === "boolean"
                              ? passed ? "rgba(72,187,120,0.04)" : "rgba(252,129,129,0.04)"
                              : "rgba(255,255,255,0.02)"}
                            border="1px solid"
                            borderColor={typeof passed === "boolean"
                              ? passed ? "rgba(72,187,120,0.18)" : "rgba(252,129,129,0.18)"
                              : "rgba(255,255,255,0.055)"}>
                            <Flex justify="space-between" align="center" mb={1}>
                              <Text fontSize="10.5px" color="gray.500" fontWeight="500">Case {i + 1}</Text>
                              {typeof passed === "boolean" && (
                                <Text fontSize="10px" color={passed ? "green.400" : "red.400"} fontWeight="600">
                                  {passed ? "✓ Pass" : "✗ Fail"}
                                </Text>
                              )}
                            </Flex>
                            <Text fontSize="11px" color="gray.500" fontFamily="monospace">
                              In: {JSON.stringify(tc.input)}
                            </Text>
                            <Text fontSize="11px" color="gray.500" fontFamily="monospace">
                              Expected: {String(tc.expected_output)}
                            </Text>
                            {res && (
                              <Text fontSize="11px" fontFamily="monospace"
                                color={passed ? "green.400" : "red.400"}>
                                Got: {String(res.actual)}
                              </Text>
                            )}
                          </Box>
                        );
                      })}
                    </Box>
                  )}

                  {/* Approach */}
                  {codingQuestionPack?.expected_solution_outline?.length > 0 && (
                    <Box>
                      <Text fontSize="10.5px" color="gray.600" fontWeight="600" letterSpacing="0.06em"
                        textTransform="uppercase" mb={2}>
                        Approach hints
                      </Text>
                      {codingQuestionPack.expected_solution_outline.map((item, i) => (
                        <HStack key={i} spacing={2} mb={1.5} align="flex-start">
                          <Box w="3px" h="3px" borderRadius="full" bg="gray.600" mt="7px" flexShrink={0} />
                          <Text fontSize="12px" color="gray.500" lineHeight="1.55">{item}</Text>
                        </HStack>
                      ))}
                    </Box>
                  )}

                  {/* Recent conversation */}
                  <Box>
                    <Text fontSize="10.5px" color="gray.600" fontWeight="600" letterSpacing="0.06em"
                      textTransform="uppercase" mb={2}>
                      Conversation
                    </Text>
                    <Flex direction="column" gap={2.5}>
                      {transcriptEntries.slice(-6).map((entry, i) => (
                        <Box key={i}>
                          <Text fontSize="9.5px"
                            color={entry.speaker === "AI" ? "blue.500" : "gray.600"}
                            fontWeight="600" letterSpacing="0.04em" mb="2px">
                            {entry.speaker}
                          </Text>
                          <Text fontSize="12px" color="gray.500" lineHeight="1.5" noOfLines={3}>
                            {entry.text}
                          </Text>
                        </Box>
                      ))}
                      {isAwaitingReply && (
                        <HStack spacing={2}>
                          <Spinner size="xs" color="blue.300" />
                          <Text fontSize="12px" color="gray.400">AI is thinking...</Text>
                        </HStack>
                      )}
                    </Flex>
                  </Box>
                </Flex>

                <AnswerComposer {...composerProps} />
              </Flex>

              {/* Right panel — full-height Monaco */}
              <Flex
                display={{ base: "none", md: "flex" }}
                w="12px"
                flexShrink={0}
                align="center"
                justify="center"
                cursor="col-resize"
                onPointerDown={handleCodePanelResizeStart}
                style={{ touchAction: "none" }}
              >
                <Box
                  h="56px"
                  w="3px"
                  borderRadius="full"
                  bg="rgba(255,255,255,0.12)"
                  _hover={{ bg: "rgba(255,255,255,0.22)" }}
                  transition="background 0.15s"
                />
              </Flex>

              <CodingPlayground
                code={code} setCode={setCode}
                language={language} setLanguage={setLanguage}
                onRunCode={handleRunCode}
                runResult={runResult}
                isRunning={isRunningCode}
                onSubmitCode={handleSubmitCode}
                isSubmittingCode={isSubmittingCode}
                onLoadTemplate={(lang) => setCode(CODE_TEMPLATES[lang] || CODE_TEMPLATES.python)}
                runnerDisabled={isCodingRunnerDisabled}
                flex="1" minW={0}
              />
            </Flex>
          )}
        </Flex>
      </Flex>

      <style>{`
        @keyframes ping { 75%, 100% { transform: scale(2.1); opacity: 0; } }
        @keyframes soundBar { from { height: 3px; } to { height: 14px; } }
        @keyframes typingPulse {
          0%, 80%, 100% { transform: scale(0.7); opacity: 0.45; }
          40% { transform: scale(1); opacity: 1; }
        }
      `}</style>
    </>
  );
}
