// src/components/CallControls.jsx
import React from "react";
import { Flex, IconButton, Box } from "@chakra-ui/react";
import { Mic, MicOff, Volume2, VolumeX, Phone } from "lucide-react";

export default function CallControls({
    micOn,
    setMicOn,
    speakerOn,
    setSpeakerOn,
    onEnd,
}) {
    return (
        <Flex
            bg="blackAlpha.500"
            borderRadius="2xl"
            border="1px solid rgba(148,163,184,0.4)"
            backdropFilter="blur(18px)"
            px={{ base: 4, md: 8 }}
            py={{ base: 3, md: 4 }}
            align="center"
            justify="center"
            gap={{ base: 2, md: 4 }}
        >
            {/* MIC */}
            <IconButton
                aria-label="Toggle mic"
                icon={micOn ? <Mic size={18} /> : <MicOff size={18} />}
                size="lg"
                borderRadius="full"
                bg={micOn ? "whiteAlpha.100" : "red.400"}
                _hover={{ bg: micOn ? "whiteAlpha.200" : "red.500" }}
                onClick={() => setMicOn((v) => !v)}
            />

            {/* SPEAKER */}
            <IconButton
                aria-label="Toggle speaker"
                icon={speakerOn ? <Volume2 size={18} /> : <VolumeX size={18} />}
                size="lg"
                borderRadius="full"
                bg={speakerOn ? "whiteAlpha.100" : "red.400"}
                _hover={{ bg: speakerOn ? "whiteAlpha.200" : "red.500" }}
                onClick={() => setSpeakerOn((v) => !v)}
            />

            {/* Divider */}
            <Box w="1px" h="40px" bg="whiteAlpha.200" />

            {/* END CALL */}
            <IconButton
                aria-label="End call"
                icon={<Phone size={18} />}
                size="lg"
                borderRadius="full"
                bg="red.500"
                _hover={{ bg: "red.600" }}
                onClick={onEnd}
            />
        </Flex>
    );
}
