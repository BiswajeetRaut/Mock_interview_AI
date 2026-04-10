import React from "react";
import {
  Box,
  Flex,
  Text,
  HStack,
  Button,
  Select,
  VStack,
  Badge,
} from "@chakra-ui/react";
import Editor from "@monaco-editor/react";
import { Code, Play } from "lucide-react";

export default function CodingPlayground({
  code,
  setCode,
  language,
  setLanguage,
  questionPack,
  onRunCode,
  runResult,
  isRunning,
  onSubmitCode,
  isSubmittingCode,
  onLoadTemplate,
}) {
  const examples = questionPack?.examples || [];
  const testCases = questionPack?.test_cases || [];
  const outline = questionPack?.expected_solution_outline || [];
  const topicTags = questionPack?.topic_tags || [];

  return (
    <Flex
      flex="1"
      direction="column"
      bg="rgba(30,41,59,0.45)"
      backdropFilter="blur(20px)"
      borderRadius="2xl"
      border="1px solid rgba(255,255,255,0.12)"
      overflow="hidden"
      minH={0}
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
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          >
            <option value="python">Python</option>
            <option value="javascript">JavaScript</option>
          </Select>

          <Button
            size="sm"
            leftIcon={<Play size={16} />}
            bg="green.500"
            color="white"
            _hover={{ bg: "green.600" }}
            isLoading={isRunning}
            onClick={onRunCode}
          >
            Run
          </Button>
          <Button
            size="sm"
            bg="blue.500"
            color="white"
            _hover={{ bg: "blue.600" }}
            isLoading={isSubmittingCode}
            onClick={onSubmitCode}
          >
            Submit
          </Button>
          <Button
            size="sm"
            variant="outline"
            borderColor="whiteAlpha.400"
            color="gray.200"
            onClick={() => onLoadTemplate?.(language)}
          >
            Reset Template
          </Button>
        </HStack>
      </Flex>

      <Flex
        direction="column"
        p={4}
        gap={3}
        borderBottom="1px solid rgba(255,255,255,0.08)"
        maxH="45%"
        overflowY="auto"
      >
        <Box border="1px solid rgba(255,255,255,0.14)" borderRadius="md" p={3} bg="rgba(255,255,255,0.03)">
          <Text fontSize="xs" color="gray.400" textTransform="uppercase" mb={1}>Solve Function Contract</Text>
          <Text fontSize="sm" color="gray.200">
            Implement <b>solve(input_data)</b> in Python or <b>solve(inputData)</b> in JavaScript.
          </Text>
          <Text fontSize="xs" color="gray.400" mt={1}>
            Return the final output directly (string/number/array/object). The runner compares it with expected output.
          </Text>
        </Box>

        <Text fontSize="md" fontWeight="semibold">Question</Text>
        <Text fontSize="sm" color="gray.200">{questionPack?.question_text || "No coding question yet."}</Text>
        {!!topicTags.length && (
          <HStack spacing={2} flexWrap="wrap">
            {topicTags.map((tag) => <Badge key={tag} colorScheme="blue">{tag}</Badge>)}
          </HStack>
        )}
        {!!outline.length && (
          <VStack align="stretch" spacing={1}>
            <Text fontSize="xs" color="gray.400" textTransform="uppercase">Expected Approach</Text>
            {outline.map((item, idx) => (
              <Text key={`${item}-${idx}`} fontSize="sm" color="gray.300">• {item}</Text>
            ))}
          </VStack>
        )}
        {!!examples.length && (
          <Box>
            <Text fontSize="xs" color="gray.400" textTransform="uppercase" mb={1}>Example</Text>
            <Text fontSize="sm" color="gray.200">Input: {JSON.stringify(examples[0].input)}</Text>
            <Text fontSize="sm" color="gray.200">Output: {String(examples[0].output)}</Text>
            <Text fontSize="sm" color="gray.400">{examples[0].explanation}</Text>
          </Box>
        )}
        {!!testCases.length && (
          <Box>
            <Text fontSize="xs" color="gray.400" textTransform="uppercase" mb={1}>Test Cases</Text>
            {testCases.map((testCase, index) => {
              const testResult = runResult?.results?.[index];
              const passed = testResult?.passed;
              return (
                <Box key={`tc-${index}`} p={2} border="1px solid rgba(255,255,255,0.1)" borderRadius="md" mb={2}>
                  <HStack justify="space-between">
                    <Text fontSize="sm">Case {index + 1}</Text>
                    {typeof passed === "boolean" && (
                      <Badge colorScheme={passed ? "green" : "red"}>{passed ? "Pass" : "Fail"}</Badge>
                    )}
                  </HStack>
                  <Text fontSize="xs" color="gray.300">Input: {JSON.stringify(testCase.input)}</Text>
                  <Text fontSize="xs" color="gray.300">Expected: {String(testCase.expected_output)}</Text>
                  {testResult && <Text fontSize="xs" color="gray.300">Actual: {String(testResult.actual)}</Text>}
                </Box>
              );
            })}
          </Box>
        )}
      </Flex>

      <Box flex="1" minH="260px" overflow="hidden">
        <Editor
          height="100%"
          theme="vs-dark"
          defaultLanguage={language === "python" ? "python" : "javascript"}
          language={language === "python" ? "python" : "javascript"}
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
