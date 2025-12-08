import React from "react";
import { Box, Heading, useColorModeValue } from "@chakra-ui/react";
import InterviewForm from "../components/InterviewForm";
import { useNavigate, useSearchParams } from "react-router-dom";
import { createInterview } from "../api/interview.api";

export default function TakeInterviewKnown() {
    const [params] = useSearchParams();
    const company = params.get("company");
    const navigate = useNavigate();
    const bg = useColorModeValue("gray.100", "gray.800");

    const handleSubmit = async (formData) => {
        const res = await createInterview(formData);
        navigate(`/interview/${res.id}`, { state: { ...formData, id: res.id } });
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
