import React from "react";
import { Box, Flex, Text, HStack, Button, Select } from "@chakra-ui/react";
import Editor from "@monaco-editor/react";
import { Code, Play } from "lucide-react";

export default function CodingPlayground({ code, setCode }) {
  return (
    <Flex
      flex="1"
      direction="column"
      bg="rgba(30,41,59,0.45)"
      backdropFilter="blur(20px)"
      borderRadius="2xl"
      border="1px solid rgba(255,255,255,0.12)"
      overflow="hidden"
    >
      {/* HEADER */}
      <Flex
        p={4}
        borderBottom="1px solid rgba(255,255,255,0.1)"
        justify="space-between"
        align="center"
      >
        <HStack spacing={3}>
          <Code size={20} color="#60a5fa" />
          <Text fontSize="lg" fontWeight="semibold">
            Coding Playground
          </Text>
        </HStack>

        <HStack spacing={3}>
          <Select
            size="sm"
            bg="rgba(255,255,255,0.05)"
            border="1px solid rgba(255,255,255,0.2)"
            borderRadius="lg"
            w="120px"
          >
            <option>JavaScript</option>
            <option>Python</option>
            <option>Java</option>
            <option>C++</option>
          </Select>

          <Button
            size="sm"
            leftIcon={<Play size={16} />}
            bg="green.500"
            color="white"
            _hover={{ bg: "green.600" }}
          >
            Run
          </Button>
        </HStack>
      </Flex>

      {/* Monaco Editor */}
      <Box flex="1">
        <Editor
          height="100%"
          theme="vs-dark"
          defaultLanguage="javascript"
          value={code}
          onChange={(v) => setCode(v)}
          options={{
            minimap: { enabled: false },
            fontSize: 15,
            padding: { top: 18 },
            smoothScrolling: true,
            scrollBeyondLastLine: false,
            roundedSelection: true,
          }}
        />
      </Box>
    </Flex>
  );
}
