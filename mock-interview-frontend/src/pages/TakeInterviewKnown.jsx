import React from "react";
import { Box, Heading, useColorModeValue } from "@chakra-ui/react";
import InterviewForm from "../components/InterviewForm";
import { useNavigate, useSearchParams } from "react-router-dom";
import { startSession } from "../api/session.api";

export default function TakeInterviewKnown() {
    const [params] = useSearchParams();
    const company = params.get("company");
    const navigate = useNavigate();
    const bg = useColorModeValue("gray.100", "gray.800");

    const handleSubmit = async (formData) => {
        const resumeData = typeof formData.resume === "string"
            ? formData.resume
            : formData.resume?.name
                ? `Uploaded resume file: ${formData.resume.name}`
                : "";

        const session = await startSession({
            user_id: "anonymous",
            candidate_name: "Candidate",
            company: formData.company,
            role: formData.role,
            difficulty: "medium",
            language_preference: "python",
            total_turns_planned: 8,
            turn_distribution: { code: 3, resume: 3, hr: 2 },
            resume_content: {
                format: "text",
                data: resumeData,
            },
        });

        navigate(`/interview/${session.session_id}`, {
            state: {
                ...formData,
                id: session.session_id,
                session,
            },
        });
    };


    return (
        <Box maxW="600px" mx="auto" mt="40px" p="8" bg={bg} rounded="xl" shadow="lg">
            <Heading mb="6" textAlign="center">
                {company} — Interview Setup
            </Heading>

            <InterviewForm company={company} showJD={false} onSubmit={handleSubmit} />
        </Box>
    );
}
