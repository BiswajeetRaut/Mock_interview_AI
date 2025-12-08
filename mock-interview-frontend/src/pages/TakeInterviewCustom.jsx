import React from "react";
import { Box, Heading, useColorModeValue } from "@chakra-ui/react";
import InterviewForm from "../components/InterviewForm";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/mockApi";

export default function TakeInterviewCustom() {
    const [params] = useSearchParams();
    const company = params.get("company");
    const navigate = useNavigate();
    const bg = useColorModeValue("gray.100", "gray.800");

    const handleSubmit = async (formData) => {
        const res = await api.createInterview(formData);
        navigate("/take-interview/custom-advanced", { state: formData });
    };


    return (
        <Box maxW="600px" mx="auto" mt="40px" p="8" bg={bg} rounded="xl" shadow="lg">
            <Heading mb="6" textAlign="center">
                {company} — Custom Interview Setup
            </Heading>

            <InterviewForm company={company} custom={true} onSubmit={handleSubmit} />
        </Box>
    );
}
