import {
  Box,
  Flex,
  Text,
  VStack,
  Badge,
  IconButton,
} from "@chakra-ui/react";
import { motion } from "framer-motion";
import { X } from "lucide-react";

const MotionBox = motion(Box);

export default function TranscriptPanel({ isOpen, onClose, transcript }) {
  return (
    <>
      {/* OVERLAY */}
      {isOpen && (
        <Box
          position="fixed"
          inset="0"
          bg="rgba(0,0,0,0.45)"
          backdropFilter="blur(2px)"
          zIndex="90"
          onClick={onClose}
        />
      )}

      {/* PANEL */}
      <MotionBox
        position="fixed"
        top="0"
        left="0"
        h="100vh"
        w={{ base: "100%", md: "50%" }}
        bg="rgba(26, 32, 44, 0.45)"
        backdropFilter="blur(20px)"
        borderRight="1px solid rgba(255,255,255,0.15)"
        zIndex="1000000"
        boxShadow="2xl"
        initial={{ x: "-100%" }}
        animate={{ x: isOpen ? "0%" : "-100%" }}
        transition={{ duration: 0.35, ease: "easeInOut" }}
        display="flex"
        flexDirection="column"
      >

        {/* HEADER */}
        <Flex
          justify="space-between"
          align="center"
          px="5"
          py="4"
          borderBottom="1px solid rgba(255,255,255,0.15)"
        >
          <Box>
            <Text fontSize="lg" fontWeight="semibold">
              Conversation Transcript
            </Text>
            <Text fontSize="xs" color="gray.400" mt="1">
              Live transcription of your interview
            </Text>
          </Box>

          <IconButton
            icon={<X size={20} />}
            aria-label="close transcript"
            bg="transparent"
            color="white"
            _hover={{ bg: "whiteAlpha.200" }}
            onClick={onClose}
          />
        </Flex>

        {/* CONTENT */}
        <VStack
          align="stretch"
          spacing={4}
          px="5"
          py="4"
          overflowY="auto"
        >
          {transcript.map((item, idx) => (
            <Box key={idx}>
              <Flex gap={2} align="center" mb={1}>
                <Badge
                  px={2}
                  py={1}
                  borderRadius="md"
                  bg={item.speaker === "AI" ? "blue.500" : "green.500"}
                  color="white"
                  fontSize="xs"
                >
                  {item.speaker}
                </Badge>
                <Text fontSize="xs" color="gray.400">
                  {item.time}
                </Text>
              </Flex>

              <Text
                fontSize="sm"
                color="gray.200"
                borderLeft="2px solid rgba(255,255,255,0.15)"
                pl={3}
              >
                {item.text}
              </Text>
            </Box>
          ))}
        </VStack>
      </MotionBox>
    </>
  );
}
