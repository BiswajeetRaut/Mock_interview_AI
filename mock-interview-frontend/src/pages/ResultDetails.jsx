import React from "react";
import {
    Box,
    Heading,
    Text,
    VStack,
    HStack,
    Divider,
    Badge,
    Flex,
    Icon,
} from "@chakra-ui/react";
import { CheckCircle, XCircle, Star, MessageSquare } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

export default function ResultDetails() {
    const navigate = useNavigate();

    // Dummy data (AI evaluation)
    const result = {
        id: "demo-123",
        company: "Accenture",
        role: "SDE I",
        score: 78,
        summary:
            "Overall strong performance with good problem‑solving structure. Improve communication clarity and go deeper in system design reasoning.",
        strengths: [
            "Explained thought process clearly in DSA question.",
            "Good understanding of time complexity tradeoffs.",
            "Calm and confident communication tone.",
        ],
        weaknesses: [
            "Missed an edge case in array manipulation question.",
            "System design answer lacked scalability considerations.",
        ],
        recommendations: [
            "Practice 2–3 DSA medium problems daily.",
            "Revise caching, load balancing, horizontal scaling.",
            "Improve STAR storytelling for HR-style questions.",
        ],
        timeline: [
            {
                q: "Tell me about yourself.",
                ai: "Good intro. Confidence level high.",
                type: "behavioral",
            },
            {
                q: "Solve: Find the longest increasing subsequence.",
                ai: "Correct approach. Missed optimized O(n log n) version.",
                type: "dsa",
            },
            {
                q: "Design a URL shortener.",
                ai: "Structure was okay. Needed better explanation of database sharding.",
                type: "system design",
            },
        ],
    };

    return (
        <Box
            maxW="6xl"
            mx="auto"
            px={{ base: 4, md: 8 }}
            py={{ base: 6, md: 10 }}
            color="white"
        >
            {/* PAGE HEADER */}
            <HStack mb={6} spacing={4}>
                <Box>
                    <Heading
                        size="xl"
                        bgGradient="linear(to-r, blue.300, purple.400)"
                        bgClip="text"
                        fontWeight="extrabold"
                    >
                        Interview Results
                    </Heading>
                    <Text fontSize="sm" color="gray.400" mt={1}>
                        AI evaluation of your mock interview performance
                    </Text>
                </Box>
            </HStack>

            {/* MAIN CARD */}
            <Box
                bg="rgba(15,23,42,0.85)"
                border="1px solid rgba(148,163,184,0.45)"
                borderRadius="2xl"
                backdropFilter="blur(16px)"
                p={{ base: 6, md: 8 }}
                boxShadow="0 8px 40px rgba(0,0,0,0.45)"
            >
                {/* Role Info */}
                <Flex justify="space-between" align="center" mb={6}>
                    <Box>
                        <Heading size="md">
                            {result.company} — {result.role}
                        </Heading>
                        <Text fontSize="xs" color="gray.400">
                            Result ID: {result.id}
                        </Text>
                    </Box>

                    <Box
                        bg="rgba(30,58,138,0.6)"
                        px={5}
                        py={3}
                        borderRadius="lg"
                        border="1px solid rgba(96,165,250,0.4)"
                    >
                        <Heading size="lg" color="blue.300">
                            {result.score}%
                        </Heading>
                        <Text fontSize="xs" color="gray.400" textAlign="center">
                            Overall Score
                        </Text>
                    </Box>
                </Flex>

                {/* SUMMARY */}
                <Box mb={8}>
                    <Heading size="sm" color="blue.300" mb={2}>
                        AI Summary
                    </Heading>
                    <Text color="gray.300" fontSize="sm">
                        {result.summary}
                    </Text>
                </Box>

                <Divider borderColor="whiteAlpha.300" my={6} />

                {/* STRENGTHS */}
                <Box mb={8}>
                    <Heading size="sm" color="green.300" mb={3}>
                        Strengths
                    </Heading>

                    <VStack align="flex-start" spacing={3}>
                        {result.strengths.map((item, i) => (
                            <HStack key={i} spacing={3}>
                                <Icon as={CheckCircle} color="green.400" />
                                <Text fontSize="sm" color="gray.200">
                                    {item}
                                </Text>
                            </HStack>
                        ))}
                    </VStack>
                </Box>

                {/* WEAKNESSES */}
                <Box mb={8}>
                    <Heading size="sm" color="red.300" mb={3}>
                        Areas to Improve
                    </Heading>

                    <VStack align="flex-start" spacing={3}>
                        {result.weaknesses.map((item, i) => (
                            <HStack key={i} spacing={3}>
                                <Icon as={XCircle} color="red.400" />
                                <Text fontSize="sm" color="gray.200">
                                    {item}
                                </Text>
                            </HStack>
                        ))}
                    </VStack>
                </Box>

                {/* RECOMMENDATIONS */}
                <Box mb={8}>
                    <Heading size="sm" color="yellow.300" mb={3}>
                        Recommended for You
                    </Heading>

                    <VStack align="flex-start" spacing={3}>
                        {result.recommendations.map((item, i) => (
                            <HStack key={i} spacing={3}>
                                <Icon as={Star} color="yellow.400" />
                                <Text fontSize="sm" color="gray.200">
                                    {item}
                                </Text>
                            </HStack>
                        ))}
                    </VStack>
                </Box>

                <Divider borderColor="whiteAlpha.300" my={6} />

                {/* TIMELINE */}
                <Box>
                    <Heading size="sm" color="purple.300" mb={4}>
                        Interview Timeline
                    </Heading>

                    <VStack align="stretch" spacing={5}>
                        {result.timeline.map((item, i) => (
                            <Box
                                key={i}
                                p={4}
                                borderRadius="lg"
                                bg="rgba(255,255,255,0.05)"
                                border="1px solid rgba(255,255,255,0.12)"
                                backdropFilter="blur(10px)"
                            >
                                <Text fontSize="sm" color="gray.300" mb={2}>
                                    <b>Q:</b> {item.q}
                                </Text>
                                <HStack spacing={2}>
                                    <Icon as={MessageSquare} color="blue.300" />
                                    <Text fontSize="xs" color="gray.400">
                                        {item.ai}
                                    </Text>
                                </HStack>

                                <Badge
                                    mt={2}
                                    colorScheme={
                                        item.type === "dsa"
                                            ? "blue"
                                            : item.type === "system design"
                                                ? "purple"
                                                : "green"
                                    }
                                >
                                    {item.type}
                                </Badge>
                            </Box>
                        ))}
                    </VStack>
                </Box>
            </Box>
        </Box>
    );
}
