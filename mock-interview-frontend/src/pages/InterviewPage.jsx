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
  VStack,
} from "@chakra-ui/react";
import {
  MessageSquare,
  Code as CodeIcon,
} from "lucide-react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import VideoCard from "../components/VideoCard";
import TranscriptModal from "../components/TranscriptPanel";
import CodingPlayground from "../components/CodingPlayground";
import CallControls from "../components/CallControls";
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

export default function InterviewPage() {
  const { state } = useLocation();
  const { id: idFromParams } = useParams();
  const navigate = useNavigate();
  const { company, role, experience, id: idFromState, session: sessionFromState } = state || {};
  const id = idFromState || idFromParams;
  const [sessionState, setSessionState] = useState(sessionFromState || null);
  const [micOn, setMicOn] = useState(true);
  const isUserSpeaking = useMicActivity(micOn);
  const silenceTimeoutRef = useRef(null);
  const [speakerOn, setSpeakerOn] = useState(true);
  const [showTranscript, setShowTranscript] = useState(false);
  const [showCode, setShowCode] = useState(false);
  const [duration, setDuration] = useState(0);

  const [isAISpeaking, setIsAISpeaking] = useState(false);

  const [code, setCode] = useState("// Start coding here...\n");
  const [answerDraft, setAnswerDraft] = useState("");
  const {
    transcript: speechTranscript,
    finalTranscript,
    listening,
    browserSupportsSpeechRecognition,
    resetTranscript,
  } = useSpeechRecognition();

  const [transcriptEntries, setTranscriptEntries] = useState([
    { speaker: "AI", text: "Welcome! I'm your AI interviewer.", time: "10:00:01" },
    { speaker: "AI", text: "Tell me about yourself.", time: "10:00:10" },
  ]);

  const timestamp = () => new Date().toLocaleTimeString();

  const buildTranscriptFromSession = (session) => {
    const entries = (session?.turns || []).flatMap((turn) => ([
      { speaker: "AI", text: turn.question_text, time: turn.completed_at || timestamp() },
      { speaker: "YOU", text: turn.user_answer_transcript, time: turn.completed_at || timestamp() },
    ]));

    const latestQuestion = session?.latest_question?.question_text;
    if (latestQuestion) {
      const alreadyPresent = entries.some(
        (entry) => entry.speaker === "AI" && entry.text === latestQuestion,
      );
      if (!alreadyPresent) {
        entries.push({ speaker: "AI", text: latestQuestion, time: timestamp() });
      }
    }

    return entries.length
      ? entries
      : [
        { speaker: "AI", text: "Welcome! I'm your AI interviewer.", time: timestamp() },
      ];
  };

  useEffect(() => {
    const loadSession = async () => {
      if (!id) return;
      try {
        const current = await fetchSessionState(id);
        setSessionState(current);
        setTranscriptEntries(buildTranscriptFromSession(current));
      } catch (error) {
        console.error("Failed to load session state:", error);
      }
    };

    if (!sessionFromState) {
      loadSession();
      return;
    }

    setTranscriptEntries(buildTranscriptFromSession(sessionFromState));
  }, [id, sessionFromState]);

  // Timer
  useEffect(() => {
    const t = setInterval(() => setDuration((d) => d + 1), 1000);
    return () => clearInterval(t);
  }, []);

  // Fake animations
  useEffect(() => {
    const aiInterval = setInterval(() => {
      if (Math.random() > 0.55) {
        setIsAISpeaking(true);
        setTimeout(() => setIsAISpeaking(false), 2600);
      }
    }, 5000);
    return () => clearInterval(aiInterval);
  }, []);

  useEffect(() => {
    if (!browserSupportsSpeechRecognition) {
      console.warn("[speech] Browser does not support speech recognition.");
      return;
    }

    if (!micOn) {
      if (silenceTimeoutRef.current) {
        clearTimeout(silenceTimeoutRef.current);
        silenceTimeoutRef.current = null;
      }

      SpeechRecognition.abortListening();
      resetTranscript();
      return;
    }

    if (isUserSpeaking) {
      if (silenceTimeoutRef.current) {
        clearTimeout(silenceTimeoutRef.current);
        silenceTimeoutRef.current = null;
      }

      if (!listening) {
        SpeechRecognition.startListening({
          continuous: true,
          language: "en-US",
        });
      }

      return;
    }

    if (listening && !silenceTimeoutRef.current) {
      silenceTimeoutRef.current = setTimeout(() => {
        SpeechRecognition.stopListening();
        silenceTimeoutRef.current = null;
      }, 1200);
    }
  }, [
    browserSupportsSpeechRecognition,
    isUserSpeaking,
    listening,
    micOn,
    resetTranscript,
  ]);

  // useEffect(() => {
  //   if (!speechTranscript.trim()) return;
  //   console.log("[interview][speech][interim]", speechTranscript);
  // }, [speechTranscript]);

  useEffect(() => {
    if (!speechTranscript?.trim()) return;
    setAnswerDraft(speechTranscript);
  }, [speechTranscript]);

  useEffect(() => {
    return () => {
      if (silenceTimeoutRef.current) {
        clearTimeout(silenceTimeoutRef.current);
      }
      SpeechRecognition.abortListening();
    };
  }, []);


  const formatTime = (s) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  };

  const handleEnd = async () => {
    if (window.confirm("End the interview?")) {
      try {
        if (!id) return;
        const reason = sessionState?.status === "active" ? "manual_end" : "completed";
        await endSession(id, reason);
        const report = await fetchSessionReport(id);
        navigate("/result-details", {
          state: {
            result: {
              id: report.session_id,
              company: report.company,
              role: report.role,
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
      } catch (error) {
        console.error("Failed to fetch interview data:", error);
        alert("An error occurred while retrieving the interview data.");
      }
    }
  };

  const handleRecordToggle = () => {
    if (!browserSupportsSpeechRecognition) {
      alert("Speech recognition is not supported in this browser.");
      return;
    }
    if (listening) {
      SpeechRecognition.stopListening();
      return;
    }
    resetTranscript();
    setAnswerDraft("");
    SpeechRecognition.startListening({ continuous: true, language: "en-US" });
  };

  const handleSendAnswer = async () => {
    const answer = answerDraft.trim() || finalTranscript.trim();
    if (!answer || !id) return;
    try {
      const requestId =
        globalThis.crypto?.randomUUID?.() || `REQ_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
      const updatedSession = await submitSessionAnswer(id, answer, requestId);
      setSessionState(updatedSession);
      const nextQuestion = updatedSession.latest_question?.question_text;
      const sessionFinished = !nextQuestion && updatedSession.status !== "active";

      setTranscriptEntries((prev) => [
        ...prev,
        { speaker: "YOU", text: answer, time: timestamp() },
        {
          speaker: "AI",
          text: sessionFinished
            ? "Great work — this interview is complete. You can end now to see the report."
            : nextQuestion || "Got it. Let's move to the next part.",
          time: timestamp(),
        },
      ]);
      setAnswerDraft("");
      resetTranscript();
    } catch (error) {
      console.error("Failed to send answer:", error);
      alert("Could not send your answer. Please try again.");
    }
  };

  return (
    <>
      {/* Transcript Overlay */}
      <TranscriptModal
        isOpen={showTranscript}
        onClose={() => setShowTranscript(false)}
        transcript={transcriptEntries}
      />

      <Flex
        direction="column"
        h="100vh"
        bg="linear-gradient(135deg, #020617 0%, #0f172a 100%)"
        color="white"
        overflow="hidden"
      >
        {/* Header */}
        <Flex
          px={{ base: 4, md: 6 }}
          py={4}
          align="center"
          justify="space-between"
          borderBottom="1px solid rgba(148,163,184,0.35)"
          bg="blackAlpha.500"
          backdropFilter="blur(18px)"
        >
          <HStack spacing={3}>
            <Box
              h="42px"
              w="42px"
              borderRadius="lg"
              bgGradient="linear(to-br, blue.500, purple.600)"
              display="flex"
              alignItems="center"
              justifyContent="center"
              fontWeight="bold"
            >
              AI
            </Box>
            <Box>
              <Text fontSize="lg" fontWeight="semibold">
                {company || "Mock Company"} — {role || "Interview"}
              </Text>
              <HStack spacing={2} fontSize="xs" color="gray.400">
                <Box h="8px" w="8px" borderRadius="full" bg="green.400" />
                <Text>Live • {formatTime(duration)}</Text>
                {experience && (
                  <Text color="gray.500">• {experience} yrs exp</Text>
                )}
              </HStack>
            </Box>
          </HStack>

          <HStack spacing={2}>
            <IconButton
              aria-label="Toggle coding playground"
              icon={<CodeIcon size={18} />}
              size="sm"
              bg={showCode ? "blue.600" : "whiteAlpha.100"}
              _hover={{ bg: showCode ? "blue.500" : "whiteAlpha.200" }}
              onClick={() => setShowCode((v) => !v)}
            />
            <IconButton
              aria-label="Open transcript"
              icon={<MessageSquare size={18} />}
              size="sm"
              bg="whiteAlpha.100"
              _hover={{ bg: "whiteAlpha.200" }}
              onClick={() => setShowTranscript(true)}
            />
          </HStack>
        </Flex>

        {/* Main Content */}
        <Flex flex="1" p={{ base: 3, md: 4 }} gap={4} overflow="hidden">
          {/* LEFT SIDE — Video Cards */}
          <Flex
            direction="column"
            gap={4}
            minW={0}
            flexShrink={0}
            flexBasis={{ base: "100%", md: showCode ? "25%" : "100%" }}
            maxW={{ base: "100%", md: showCode ? "25%" : "100%" }}
          >
            {/* Videos */}
            <Flex
              flex="1"
              gap={4}
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

            {/* Controls */}
            <CallControls
              micOn={micOn}
              setMicOn={setMicOn}
              speakerOn={speakerOn}
              setSpeakerOn={setSpeakerOn}
              onEnd={handleEnd}
            />

            <Box
              bg="whiteAlpha.100"
              border="1px solid rgba(148,163,184,0.35)"
              borderRadius="lg"
              p={3}
            >
              <VStack spacing={3} align="stretch">
                <Text fontSize="sm" color="gray.300">
                  Answer input (record or type, then send)
                </Text>
                <Textarea
                  value={answerDraft}
                  onChange={(e) => setAnswerDraft(e.target.value)}
                  placeholder="Type your answer here or use Record Answer..."
                  bg="blackAlpha.500"
                  borderColor="whiteAlpha.300"
                  minH="90px"
                />
                <HStack spacing={3}>
                  <Button
                    size="sm"
                    colorScheme={listening ? "red" : "purple"}
                    onClick={handleRecordToggle}
                  >
                    {listening ? "Stop Recording" : "Record Answer"}
                  </Button>
                  <Button
                    size="sm"
                    colorScheme="blue"
                    onClick={handleSendAnswer}
                    isDisabled={!answerDraft.trim() && !finalTranscript.trim()}
                  >
                    Send Answer
                  </Button>
                </HStack>
              </VStack>
            </Box>

          </Flex>

          {/* RIGHT SIDE — Coding Playground */}
          {showCode && (
            <CodingPlayground
              code={code}
              setCode={setCode}
              isOpen={showCode}
              flexGrow={1}
              flexBasis={{ base: "100%", md: "75%" }}
              maxW={{ base: "100%", md: "75%" }}
            />
          )}
        </Flex>
      </Flex>
    </>
  );
}
