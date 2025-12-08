import React, { useState, useRef, useEffect } from "react";
import {
  Box,
  Heading,
  Input,
  IconButton,
  VStack,
  HStack,
  Text,
  Avatar,
  Spinner,
} from "@chakra-ui/react";
import { motion } from "framer-motion";
import { Send } from "lucide-react";
import { api } from "../api/mockApi";

const MotionBox = motion(Box);

export default function AskMockGPT() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: "ai",
      text: "Hi! I'm MockGPT. Ask me anything about interviews, tech, or careers! 😊",
    },
  ]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMsg = {
      id: Date.now(),
      sender: "user",
      text: input,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await api.askMockGPT(userMsg.text);

      const aiMsg = {
        id: Date.now() + 1,
        sender: "ai",
        text: res.answer || "Sorry, I couldn't process that.",
      };

      setMessages((prev) => [...prev, aiMsg]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 2,
          sender: "ai",
          text: "⚠️ Something went wrong. Try again!",
        },
      ]);
    }

    setLoading(false);
  };

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <Box
      h="calc(100vh - 80px)"
      display="flex"
      flexDirection="column"
      alignItems="center"
      bg="linear-gradient(135deg, #0f0f11, #1a1a1d)"
      borderRadius="xl"
      border="1px solid rgba(255,255,255,0.08)"
      overflow="hidden"
      p={4}
    >
      {/* HEADER */}
      <HStack
        p={4}
        borderBottom="1px solid rgba(255,255,255,0.08)"
        backdropFilter="blur(12px)"
        textAlign="left"
      >
        <Avatar size="md" bg="blue.600" name="MockGPT" />
        <Box>
          <Heading size="md">Ask MockGPT</Heading>
          <Text fontSize="xs" color="gray.400">
            AI assistant for interview prep
          </Text>
        </Box>
      </HStack>

      {/* CHAT AREA */}
      <VStack
        flex="1"
        overflowY="auto"
        width="70%"
        spacing={4}
        py={4}
        px={1}
        css={{
          "&::-webkit-scrollbar": { width: "6px" },
          "&::-webkit-scrollbar-thumb": {
            background: "rgba(255,255,255,0.1)",
            borderRadius: "10px",
          },
        }}
      >
        {messages.map((msg) => (
          <MotionBox
            key={msg.id}
            alignSelf={msg.sender === "user" ? "flex-end" : "flex-start"}
            maxW="80%"
            p={3}
            borderRadius="lg"
            bg={
              msg.sender === "user"
                ? "blue.600"
                : "rgba(255,255,255,0.08)"
            }
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <Text fontSize="sm" color="white">
              {msg.text}
            </Text>
          </MotionBox>
        ))}

        {loading && (
          <HStack alignSelf="flex-start" spacing={3}>
            <Avatar size="xs" bg="blue.600" />
            <HStack
              p={2}
              borderRadius="lg"
              bg="rgba(255,255,255,0.08)"
              spacing={1}
            >
              <Spinner size="sm" color="blue.300" />
              <Text fontSize="xs" color="gray.300">
                MockGPT is typing...
              </Text>
            </HStack>
          </HStack>
        )}

        <div ref={bottomRef} />
      </VStack>

      {/* INPUT BAR */}
      <HStack
        p={3}
        borderTop="1px solid rgba(255,255,255,0.08)"
        backdropFilter="blur(12px)"
        width="70%"
      >
        <Input
          placeholder="Ask me anything..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          bg="rgba(255,255,255,0.06)"
          border="1px solid rgba(255,255,255,0.1)"
          _focus={{ borderColor: "blue.400" }}
        />

        <IconButton
          icon={<Send size={18} />}
          colorScheme="blue"
          onClick={sendMessage}
          isDisabled={!input.trim()}
        />
      </HStack>
    </Box>
  );
}
