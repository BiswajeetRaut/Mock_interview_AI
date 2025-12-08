// src/components/VideoCard.jsx
import React from "react";
import { Box, Flex, Text, IconButton } from "@chakra-ui/react";
import { Maximize2 } from "lucide-react";

export default function VideoCard({
    label,
    gradient,
    speaking = false,
    compact = false,
}) {
    return (
        <Box
            position="relative"
            bg="linear-gradient(135deg, rgba(55,65,81,0.45), rgba(15,23,42,0.7))"
            borderRadius="2xl"
            border="1px solid rgba(255,255,255,0.16)"
            backdropFilter="blur(20px)"
            overflow="hidden"
            minH={compact ? "190px" : { base: "260px", md: "340px" }}
            flex="1"
            role="group"
            transition="all 0.25s ease"
        >
            {/* Center avatar */}
            <Flex position="absolute" inset="0" align="center" justify="center">
                <Flex
                    h={compact ? "72px" : { base: "96px", md: "140px" }}
                    w={compact ? "72px" : { base: "96px", md: "140px" }}
                    borderRadius="full"
                    bgGradient={gradient}
                    align="center"
                    justify="center"
                    fontWeight="bold"
                    fontSize={compact ? "lg" : { base: "2xl", md: "3xl" }}
                    transform={speaking ? "scale(1.1)" : "scale(1)"}
                    boxShadow={
                        speaking
                            ? "0 0 30px rgba(96,165,250,0.6)"
                            : "0 0 18px rgba(15,23,42,0.8)"
                    }
                    transition="all 0.25s ease"
                >
                    {label}
                </Flex>
            </Flex>

            {/* Speaking bars */}
            {speaking && (
                <Flex
                    position="absolute"
                    bottom="50%"
                    left="50%"
                    transform="translate(-50%, 50%)"
                    gap={1}
                >
                </Flex>
            )}

            {/* Label pill */}
            <Flex
                position="absolute"
                bottom={3}
                left={3}
                px={3}
                py={1.5}
                borderRadius="lg"
                bg="blackAlpha.60"
                backdropFilter="blur(10px)"
                align="center"
                gap={2}
            >
                <Box
                    h="8px"
                    w="8px"
                    borderRadius="full"
                    bg={speaking ? "green.300" : "gray.400"}
                />
                <Text fontSize="sm" fontWeight="medium">
                    {label}
                </Text>
            </Flex>

        </Box>
    );
}
