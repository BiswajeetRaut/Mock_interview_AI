// src/pages/InterviewPage.jsx
import React, { useEffect, useState } from "react";
import {
  Flex,
  Box,
  HStack,
  Text,
  IconButton,
} from "@chakra-ui/react";
import {
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Phone,
  MessageSquare,
  Code as CodeIcon,
} from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

import VideoCard from "../components/VideoCard";
import TranscriptModal from "../components/TranscriptPanel";
import CodingPlayground from "../components/CodingPlayground";
import CallControls from "../components/CallControls";
import useMicActivity from "../hooks/useMicActivity";
import { fetchInterview } from "../api/interview.api";

export default function InterviewPage() {
  const { state } = useLocation();
  console.log(state)
  const navigate = useNavigate();
  const { company, role, experience, id } = state || {};
  const [micOn, setMicOn] = useState(true);
  const isUserSpeaking = useMicActivity(micOn);
  const [speakerOn, setSpeakerOn] = useState(true);
  const [showTranscript, setShowTranscript] = useState(false);
  const [showCode, setShowCode] = useState(false);
  const [duration, setDuration] = useState(0);

  const [isAISpeaking, setIsAISpeaking] = useState(false);

  const [code, setCode] = useState("// Start coding here...\n");

  const [transcript] = useState([
    { speaker: "AI", text: "Welcome! I'm your AI interviewer.", time: "10:00:01" },
    { speaker: "AI", text: "Tell me about yourself.", time: "10:00:10" },
  ]);

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


  const formatTime = (s) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  };

  const handleEnd = async () => {
    if (window.confirm("End the interview?")) {
      try {
        const interviewData = await fetchInterview(id);
        // Navigate to the results page with the interview data
        navigate("/results", { state: { interview: interviewData } });
      } catch (error) {
        console.error("Failed to fetch interview data:", error);
        alert("An error occurred while retrieving the interview data.");
      }
    }
  };

  return (
    <>
      {/* Transcript Overlay */}
      <TranscriptModal
        isOpen={showTranscript}
        onClose={() => setShowTranscript(false)}
        transcript={transcript}
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
