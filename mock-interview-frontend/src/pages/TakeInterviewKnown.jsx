import React from "react";
import { Box, Heading, useColorModeValue } from "@chakra-ui/react";
import InterviewForm from "../components/InterviewForm";
import { useNavigate, useSearchParams } from "react-router-dom";
import { startSession } from "../api/session.api";
import { buildSessionStartPayload } from "../utils/sessionPayload";

export default function TakeInterviewKnown() {
    const [params] = useSearchParams();
    const company = params.get("company");
    const navigate = useNavigate();
    const bg = useColorModeValue("gray.100", "gray.800");

    const handleSubmit = async (formData) => {
        const selectedTypes = Object.keys(formData.topics || {});
        const payload = await buildSessionStartPayload({
            company: formData.company,
            role: formData.role,
            experience: formData.experience,
            jd: formData.jd,
            resume: formData.resume,
            selectedTypes,
            topics: formData.topics,
        });
        const session = await startSession(payload);

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
