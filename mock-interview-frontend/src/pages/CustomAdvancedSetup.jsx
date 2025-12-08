import React, { useState, useRef } from "react";
import {
    Box,
    Heading,
    VStack,
    Button,
    useColorModeValue,
    Divider,
    Text
} from "@chakra-ui/react";
import { useLocation, useNavigate } from "react-router-dom";

import TypeSelector from "../components/TypeSelector";
import TopicSelector from "../components/TopicSelector";

import {
    DSA_TOPICS,
    SYSTEM_DESIGN_TOPICS,
    MANAGERIAL_TOPICS
} from "../data/topics";
import { createInterview } from "../api/interview.api";

const INTERVIEW_TYPES = [
    {
        id: "tech-dsa",
        label: "Technical – DSA",
        desc: "Algorithm & data structure problems."
    },
    {
        id: "system-design",
        label: "System Design",
        desc: "Architecture, scaling, infra, databases, caching."
    },
    {
        id: "managerial",
        label: "Managerial",
        desc: "Leadership, communication, conflict resolution."
    },
    {
        id: "resume-based",
        label: "Resume Based",
        desc: "Experience deep‑dive — No topic selection required."
    }
];

export default function CustomAdvancedSetup() {
    const { state } = useLocation();
    const navigate = useNavigate();

    const { company, role, experience, jd, resume } = state;

    const bg = useColorModeValue("gray.100", "gray.900");

    const [selectedTypes, setSelectedTypes] = useState([]);
    const [topicsMap, setTopicsMap] = useState({
        "tech-dsa": [],
        "system-design": [],
        "managerial": [],
        "resume-based": []
    });

    const fileInputRef = useRef();

    const toggleType = (typeId) => {
        if (selectedTypes.includes(typeId)) {
            setSelectedTypes(selectedTypes.filter((t) => t !== typeId));
        } else {
            setSelectedTypes([...selectedTypes, typeId]);
        }
    };

    const updateTopics = (id, newTopics) => {
        setTopicsMap({ ...topicsMap, [id]: newTopics });
    };

    const getTopics = (typeId) => {
        switch (typeId) {
            case "tech-dsa":
                return DSA_TOPICS;
            case "system-design":
                return SYSTEM_DESIGN_TOPICS;
            case "managerial":
                return MANAGERIAL_TOPICS;
            default:
                return [];
        }
    };

    const handleStart = async () => {
        const res = await createInterview({ company, role, experience, jd, resume, topics: topicsMap });
        navigate(`/interview/${res.id}`, { state: { id: res.id, company, role, experience, jd, resume, topicsMap } });

    };

    return (
        <Box
            maxW="850px"
            mx="auto"
            mt="40px"
            p="8"
            bg={bg}
            rounded="xl"
            shadow="xl"
        >
            <Heading mb="1" fontWeight="bold">
                Advanced Interview Customization
            </Heading>

            <Box color="gray.400" mb="6">
                Choose interview types and refine topic-level focus.
            </Box>

            {/* SELECT TYPES */}
            <Heading size="md" mb="2">
                Select Interview Types
            </Heading>

            <TypeSelector
                types={INTERVIEW_TYPES}
                selected={selectedTypes}
                toggle={toggleType}
            />

            <Divider my="6" />

            {/* DYNAMIC TOPIC SECTIONS */}
            {selectedTypes.map((t) =>
                t === "resume-based" ? null : (
                    <Box key={t} mt="4">
                        <Heading size="sm" mb="2">
                            {INTERVIEW_TYPES.find((x) => x.id === t)?.label} Topics
                        </Heading>

                        <TopicSelector
                            topics={getTopics(t)}
                            selected={topicsMap[t]}
                            setSelected={(newList) => updateTopics(t, newList)}
                        />
                    </Box>
                )
            )}

            {/* RESUME UPLOAD IF RESUME-BASED SELECTED */}
            {selectedTypes.includes("resume-based") && (
                <Box mt="8">
                    <Heading size="sm" mb="2">Upload Resume</Heading>

                    <Box
                        bg="gray.900"
                        p="5"
                        rounded="lg"
                        border="2px dashed"
                        borderColor="gray.600"
                        textAlign="center"
                        cursor="pointer"
                        _hover={{ borderColor: "blue.400" }}
                        onDragOver={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                        }}
                        onDrop={(e) => {
                            e.preventDefault();
                            const file = e.dataTransfer.files[0];
                            if (file) setResume(file);
                        }}
                        onClick={() => fileInputRef.current.click()}
                    >
                        <Text color="gray.400">
                            Drag & Drop Resume here, or <strong>click to browse</strong>
                        </Text>

                        {resume && (
                            <Text mt="3" fontSize="sm" color="blue.300">
                                Uploaded: {resume.name}
                            </Text>
                        )}
                    </Box>

                    <input
                        type="file"
                        accept=".pdf,.doc,.docx,.txt"
                        style={{ display: "none" }}
                        ref={fileInputRef}
                        onChange={(e) => {
                            if (e.target.files[0]) setResume(e.target.files[0]);
                        }}
                    />
                </Box>
            )}

            <VStack mt="10">
                <Button
                    size="lg"
                    colorScheme="blue"
                    w="full"
                    onClick={handleStart}
                    isDisabled={
                        selectedTypes.length === 0 ||
                        (selectedTypes.includes("resume-based") && !resume)
                    }
                >
                    Start Interview
                </Button>
            </VStack>
        </Box>
    );
}
