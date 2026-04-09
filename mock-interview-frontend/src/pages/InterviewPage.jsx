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
} from "@chakra-ui/react";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageSquare,
  Code as CodeIcon,
  Send,
  Mic,
  MicOff,
  ChevronUp,
  ChevronDown,
} from "lucide-react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import VideoCard from "../components/VideoCard";
import TranscriptModal from "../components/TranscriptPanel";
import CodingPlayground from "../components/CodingPlayground";
import useMicActivity from "../hooks/useMicActivity";
import {
  endSession,
  fetchSessionReport,
  fetchSessionState,
  submitSessionAnswer,
} from "../api/session.api";
import SpeechRecognition, {
  useSpeechRecognition,
} from "react-speech-recognition";
import Speech from "speak-tts";

const MotionBox = motion(Box);

export default function InterviewPage() {
  const { state } = useLocation();
  const { id: idFromParams } = useParams();
  const navigate = useNavigate();
  const { company, role, experience, id: idFromState, session: sessionFromState } = state || {};
  const id = idFromState || idFromParams;
  const [sessionState, setSessionState] = useState(sessionFromState || null);
  const speechRef = useRef(null);
  const lastSpokenAITextRef = useRef("");
  const [showTranscript, setShowTranscript] = useState(false);
  const [showCode, setShowCode] = useState(false);
  const [duration, setDuration] = useState(0);
  const [ttsReady, setTtsReady] = useState(false);
  const [isAISpeaking, setIsAISpeaking] = useState(false);
  const [composerExpanded, setComposerExpanded] = useState(true);
  const textareaRef = useRef(null);

  const [code, setCode] = useState("// Start coding here...\n");
  const [answerDraft, setAnswerDraft] = useState("");
  const {
    transcript: speechTranscript,
    finalTranscript,
    listening,
    browserSupportsSpeechRecognition,
    resetTranscript,
  } = useSpeechRecognition();
  const isUserSpeaking = useMicActivity(listening);

  const [transcriptEntries, setTranscriptEntries] = useState([]);

  const timestamp = () => new Date().toLocaleTimeString();

  const pickPreferredVoiceName = (voices = []) => {
    const englishVoice = voices.find((v) => v?.lang?.toLowerCase().startsWith("en-"));
    return englishVoice?.name || null;
  };

  const buildTranscriptFromSession = (session) => {
    const entries = (session?.turns || []).flatMap((turn) => ([
      { speaker: "AI", text: turn.question_text, time: turn.completed_at || timestamp() },
      { speaker: "YOU", text: turn.user_answer_transcript, time: turn.completed_at || timestamp() },
    ]));
    const latestQuestion = session?.latest_question?.question_text;
    if (latestQuestion) {
      const alreadyPresent = entries.some(
        (e) => e.speaker === "AI" && e.text === latestQuestion,
      );
      if (!alreadyPresent) entries.push({ speaker: "AI", text: latestQuestion, time: timestamp() });
    }
    return entries.length
      ? entries
      : [{ speaker: "AI", text: "Welcome! I'm your AI interviewer.", time: timestamp() }];
  };

  useEffect(() => {
    const loadSession = async () => {
      if (!id) return;
      try {
        const current = await fetchSessionState(id);
        setSessionState(current);
        setTranscriptEntries(buildTranscriptFromSession(current));
      } catch (err) {
        console.error("Failed to load session state:", err);
      }
    };
    if (!sessionFromState) { loadSession(); return; }
    setTranscriptEntries(buildTranscriptFromSession(sessionFromState));
  }, [id, sessionFromState]);

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
      })
      .catch(console.error);
    return () => { cancelled = true; speech.cancel(); setIsAISpeaking(false); };
  }, []);

  useEffect(() => {
    if (!speechTranscript?.trim()) return;
    setAnswerDraft(speechTranscript);
  }, [speechTranscript]);

  useEffect(() => {
    const latestAI = [...transcriptEntries].reverse().find((e) => e.speaker === "AI" && e.text?.trim());
    const next = latestAI?.text?.trim();
    if (!next || !ttsReady || !speechRef.current) return;
    if (next === lastSpokenAITextRef.current) return;
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

  useEffect(() => {
    return () => {
      if (speechRef.current) speechRef.current.cancel();
      SpeechRecognition.abortListening();
    };
  }, []);

  const formatTime = (s) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  };

  const handleEnd = async () => {
    if (!window.confirm("End the interview?")) return;
    try {
      if (!id) return;
      const reason = sessionState?.status === "active" ? "manual_end" : "completed";
      await endSession(id, reason);
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
            transcript: (report.detailed_turns || []).flatMap((turn) => [
              { speaker: "AI", text: turn.question_text },
              { speaker: "YOU", text: turn.user_answer_transcript },
            ]),
          },
        },
      });
    } catch (err) {
      console.error(err);
      alert("An error occurred while retrieving the interview data.");
    }
  };

  const handleRecordToggle = () => {
    if (!browserSupportsSpeechRecognition) { alert("Speech recognition is not supported in this browser."); return; }
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
    if (!answer || !id) return;
    try {
      if (speechRef.current) { speechRef.current.cancel(); setIsAISpeaking(false); }
      if (listening) SpeechRecognition.abortListening();
      const requestId = globalThis.crypto?.randomUUID?.() || `REQ_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
      const updatedSession = await submitSessionAnswer(id, answer, requestId);
      setSessionState(updatedSession);
      const nextQuestion = updatedSession.latest_question?.question_text;
      const sessionFinished = !nextQuestion && updatedSession.status !== "active";
      const aiReplyText = sessionFinished
        ? "Great work — this interview is complete. You can end now to see your report."
        : nextQuestion || "Got it. Let's move to the next part.";
      setTranscriptEntries((prev) => [
        ...prev,
        { speaker: "YOU", text: answer, time: timestamp() },
        { speaker: "AI", text: aiReplyText, time: timestamp() },
      ]);
      setAnswerDraft("");
      resetTranscript();
    } catch (err) {
      console.error(err);
      alert("Could not send your answer. Please try again.");
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSendAnswer();
    }
  };

  const canSend = !!(answerDraft.trim() || finalTranscript.trim());

  return (
    <>
      <TranscriptModal
        isOpen={showTranscript}
        onClose={() => setShowTranscript(false)}
        transcript={transcriptEntries}
      />

      <Flex
        direction="column"
        h="100vh"
        bg="#080a0e"
        color="white"
        overflow="hidden"
        fontFamily="'DM Sans', 'Helvetica Neue', sans-serif"
      >

        {/* ── TOP BAR ── */}
        <Flex
          px={{ base: 4, md: 6 }}
          h="56px"
          align="center"
          justify="space-between"
          flexShrink={0}
          style={{
            background: "rgba(8,10,14,0.85)",
            backdropFilter: "blur(20px)",
            borderBottom: "1px solid rgba(255,255,255,0.06)",
          }}
        >
          {/* Left — session info */}
          <HStack spacing={3}>
            <Box
              h="34px" w="34px" borderRadius="9px" bg="blue.500"
              display="flex" alignItems="center" justifyContent="center"
              fontWeight="700" fontSize="13px" color="white"
              style={{ boxShadow: "0 0 0 1px rgba(99,179,237,0.3)" }}
            >
              AI
            </Box>
            <Box>
              <Text fontSize="14px" fontWeight="600" letterSpacing="-0.01em">
                {company || "Mock Company"}{" "}
                <Box as="span" color="gray.500" fontWeight="400">·</Box>{" "}
                {role || "Interview"}
              </Text>
              <HStack spacing={2} mt="1px">
                <Box h="6px" w="6px" borderRadius="full" bg="green.400"
                  style={{ boxShadow: "0 0 6px rgba(72,187,120,0.8)" }} />
                <Text fontSize="11px" color="gray.500" letterSpacing="0.02em">
                  LIVE · {formatTime(duration)}
                  {experience && ` · ${experience} yrs`}
                </Text>
              </HStack>
            </Box>
          </HStack>

          {/* Right — toolbar + end */}
          <HStack spacing={2}>
            <IconButton
              aria-label="Toggle coding playground"
              icon={<CodeIcon size={15} />}
              size="sm" h="32px" w="32px" minW="32px"
              bg={showCode ? "blue.600" : "whiteAlpha.80"}
              border="1px solid"
              borderColor={showCode ? "blue.500" : "whiteAlpha.100"}
              borderRadius="8px"
              color={showCode ? "white" : "gray.400"}
              _hover={{ bg: showCode ? "blue.500" : "whiteAlpha.200", color: "white" }}
              transition="all 0.18s"
              onClick={() => setShowCode((v) => !v)}
            />
            <IconButton
              aria-label="Open transcript"
              icon={<MessageSquare size={15} />}
              size="sm" h="32px" w="32px" minW="32px"
              bg="whiteAlpha.80"
              border="1px solid" borderColor="whiteAlpha.100"
              borderRadius="8px" color="gray.400"
              _hover={{ bg: "whiteAlpha.200", color: "white" }}
              transition="all 0.18s"
              onClick={() => setShowTranscript(true)}
            />

            <Box h="20px" w="1px" bg="whiteAlpha.100" mx={1} />

            <Button
              h="32px" px={4}
              fontSize="12px" fontWeight="600"
              borderRadius="8px"
              bg="rgba(254,178,178,0.08)"
              color="red.400"
              border="1px solid"
              borderColor="rgba(252,129,129,0.2)"
              _hover={{
                bg: "rgba(254,178,178,0.15)",
                borderColor: "rgba(252,129,129,0.4)",
                color: "red.300",
              }}
              _active={{ transform: "scale(0.97)" }}
              transition="all 0.18s"
              onClick={handleEnd}
            >
              End Interview
            </Button>
          </HStack>
        </Flex>

        {/* ── MAIN AREA ── */}
        <Flex flex="1" p={{ base: 3, md: 4 }} gap={4} overflow="hidden" minH={0}>

          {/* LEFT — Video + Controls */}
          <Flex
            direction="column"
            gap={3}
            flexShrink={0}
            flexBasis={{ base: "100%", md: showCode ? "26%" : "100%" }}
            maxW={{ base: "100%", md: showCode ? "26%" : "100%" }}
            minH={0}
          >
            {/* Video cards */}
            <Flex
              flex="1"
              gap={3}
              direction={showCode ? "column" : { base: "column", md: "row" }}
              minH={0}
            >
              <VideoCard
                label="AI"
                gradient="linear(to-br, blue.400, purple.600)"
                speaking={isAISpeaking}
                compact={showCode}
              />
              <VideoCard
                label="YOU"
                gradient="linear(to-br, green.400, teal.600)"
                speaking={isUserSpeaking}
                compact={showCode}
              />
            </Flex>
          </Flex>

          {/* RIGHT — Coding Playground */}
          {showCode && (
            <CodingPlayground
              code={code}
              setCode={setCode}
              isOpen={showCode}
              flexGrow={1}
              flexBasis={{ base: "100%", md: "74%" }}
              maxW={{ base: "100%", md: "74%" }}
            />
          )}
        </Flex>

        {/* ── ANSWER COMPOSER DOCK ── */}
        <Box
          flexShrink={0}
          px={{ base: 3, md: 4 }}
          pb={3}
          style={{ background: "rgba(8,10,14,0.95)" }}
        >
          {/* Composer card */}
          <Box
            borderRadius="14px"
            border="1px solid"
            borderColor={listening ? "rgba(99,179,237,0.4)" : "rgba(255,255,255,0.08)"}
            overflow="hidden"
            style={{
              background: "rgba(255,255,255,0.03)",
              transition: "border-color 0.25s ease",
              boxShadow: listening
                ? "0 0 0 3px rgba(99,179,237,0.08), 0 8px 32px rgba(0,0,0,0.5)"
                : "0 8px 32px rgba(0,0,0,0.4)",
            }}
          >
            {/* Composer header — always visible */}
            <Flex
              px={4} py={2.5}
              align="center"
              justify="space-between"
              borderBottom={composerExpanded ? "1px solid rgba(255,255,255,0.06)" : "none"}
              cursor="pointer"
              onClick={() => setComposerExpanded((v) => !v)}
              _hover={{ bg: "whiteAlpha.50" }}
              transition="background 0.15s"
            >
              <HStack spacing={3}>
                {/* Recording pulse */}
                <AnimatePresence>
                  {listening && (
                    <MotionBox
                      initial={{ scale: 0.6, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      exit={{ scale: 0.6, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <HStack spacing={1.5}>
                        <Box position="relative" h="8px" w="8px">
                          <Box
                            position="absolute" inset={0} borderRadius="full" bg="red.400"
                            style={{ animation: "ping 1.2s cubic-bezier(0,0,0.2,1) infinite", opacity: 0.5 }}
                          />
                          <Box position="absolute" inset={0} borderRadius="full" bg="red.400" />
                        </Box>
                        <Text fontSize="11px" color="red.400" fontWeight="600" letterSpacing="0.06em">
                          RECORDING
                        </Text>
                      </HStack>
                    </MotionBox>
                  )}
                </AnimatePresence>

                {!listening && (
                  <Text fontSize="12px" color="gray.500" fontWeight="500">
                    Your answer
                  </Text>
                )}

                {answerDraft && !listening && (
                  <Badge
                    bg="whiteAlpha.100" color="gray.400"
                    borderRadius="5px" px={2} py={0.5}
                    fontSize="10px" fontWeight="500"
                  >
                    {answerDraft.split(/\s+/).filter(Boolean).length} words
                  </Badge>
                )}
              </HStack>

              <HStack spacing={2} onClick={(e) => e.stopPropagation()}>
                {/* Record toggle */}
                <Button
                  size="sm" h="28px" px={3}
                  fontSize="12px" fontWeight="600"
                  borderRadius="7px"
                  bg={listening ? "rgba(254,178,178,0.12)" : "whiteAlpha.80"}
                  color={listening ? "red.300" : "gray.400"}
                  border="1px solid"
                  borderColor={listening ? "rgba(252,129,129,0.3)" : "whiteAlpha.100"}
                  _hover={{
                    bg: listening ? "rgba(254,178,178,0.2)" : "whiteAlpha.200",
                    color: listening ? "red.200" : "white",
                  }}
                  leftIcon={listening ? <MicOff size={12} /> : <Mic size={12} />}
                  transition="all 0.18s"
                  onClick={handleRecordToggle}
                >
                  {listening ? "Stop" : "Record"}
                </Button>

                {/* Send */}
                <Button
                  size="sm" h="28px" px={3}
                  fontSize="12px" fontWeight="600"
                  borderRadius="7px"
                  bg={canSend ? "blue.500" : "whiteAlpha.50"}
                  color={canSend ? "white" : "gray.600"}
                  _hover={canSend ? { bg: "blue.400" } : {}}
                  rightIcon={<Send size={11} />}
                  isDisabled={!canSend}
                  transition="all 0.2s"
                  style={canSend ? { boxShadow: "0 4px 14px rgba(99,179,237,0.3)" } : {}}
                  onClick={handleSendAnswer}
                >
                  Send
                </Button>

                {/* Collapse chevron */}
                <IconButton
                  aria-label="Toggle composer"
                  icon={composerExpanded ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
                  size="sm" h="28px" w="28px" minW="28px"
                  bg="transparent" color="gray.600"
                  borderRadius="7px"
                  _hover={{ bg: "whiteAlpha.100", color: "gray.400" }}
                  transition="all 0.15s"
                  onClick={() => setComposerExpanded((v) => !v)}
                />
              </HStack>
            </Flex>

            {/* Expandable textarea */}
            <AnimatePresence initial={false}>
              {composerExpanded && (
                <MotionBox
                  key="composer-body"
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
                  style={{ overflow: "hidden" }}
                >
                  <Box px={4} pt={3} pb={3}>
                    <Textarea
                      ref={textareaRef}
                      value={answerDraft}
                      onChange={(e) => setAnswerDraft(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder={
                        listening
                          ? "Listening… speak your answer"
                          : "Type your answer, or hit Record to speak  ·  ⌘↵ to send"
                      }
                      rows={3}
                      resize="none"
                      bg="transparent"
                      border="none"
                      outline="none"
                      p={0}
                      fontSize="14px"
                      color={listening ? "gray.200" : "gray.300"}
                      _placeholder={{ color: "gray.600", fontSize: "13px" }}
                      _focus={{ boxShadow: "none", border: "none" }}
                      fontFamily="'DM Sans', sans-serif"
                      lineHeight="1.7"
                      style={{ caretColor: listening ? "#68D391" : "#63B3ED" }}
                    />
                    <Text fontSize="10px" color="gray.700" mt={2} textAlign="right" letterSpacing="0.02em">
                      ⌘↵ to send
                    </Text>
                  </Box>
                </MotionBox>
              )}
            </AnimatePresence>
          </Box>
        </Box>

      </Flex>

      {/* Pulse keyframe */}
      <style>{`
        @keyframes ping {
          75%, 100% { transform: scale(2); opacity: 0; }
        }
      `}</style>
    </>
  );
}
