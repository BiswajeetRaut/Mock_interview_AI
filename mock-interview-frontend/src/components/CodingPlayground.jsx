// src/components/CodingPlayground.jsx
import React, { useEffect, useRef, useState } from "react";
import { Flex, Box, HStack, Text, Button } from "@chakra-ui/react";
import Editor from "@monaco-editor/react";
import { Play, Send, RotateCcw, AlertTriangle } from "lucide-react";

const SUMMARY_BAR_HEIGHT = 36;
const DEFAULT_RESULTS_HEIGHT = 176;
const MIN_RESULTS_HEIGHT = 60;

export default function CodingPlayground({
  code,
  setCode,
  language,
  setLanguage,
  onRunCode,
  runResult,
  isRunning,
  onSubmitCode,
  isSubmittingCode,
  onLoadTemplate,
  runnerDisabled = false,
  ...rest
}) {
  const containerRef = useRef(null);
  const [resultsHeight, setResultsHeight] = useState(DEFAULT_RESULTS_HEIGHT);
  const dragStateRef = useRef({
    active: false,
    startY: 0,
    startHeight: DEFAULT_RESULTS_HEIGHT,
  });

  useEffect(() => {
    if (!runResult) return;

    const hasFailures = runResult.results?.some((result) => !result.passed);
    setResultsHeight(hasFailures ? DEFAULT_RESULTS_HEIGHT : MIN_RESULTS_HEIGHT);
  }, [runResult]);

  useEffect(() => {
    const handlePointerMove = (event) => {
      if (!dragStateRef.current.active) return;

      const container = containerRef.current;
      if (!container) return;

      const deltaY = dragStateRef.current.startY - event.clientY;
      const maxResultsHeight = Math.max(
        MIN_RESULTS_HEIGHT,
        container.getBoundingClientRect().height - 180
      );

      const nextHeight = Math.min(
        maxResultsHeight,
        Math.max(MIN_RESULTS_HEIGHT, dragStateRef.current.startHeight + deltaY)
      );

      setResultsHeight(nextHeight);
    };

    const stopDragging = () => {
      dragStateRef.current.active = false;
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", stopDragging);
    window.addEventListener("pointercancel", stopDragging);

    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", stopDragging);
      window.removeEventListener("pointercancel", stopDragging);
    };
  }, []);

  const handleResizeStart = (event) => {
    event.preventDefault();
    dragStateRef.current = {
      active: true,
      startY: event.clientY,
      startHeight: resultsHeight,
    };
  };

  const failedResults =
    runResult?.results
      ?.map((result, index) => ({ ...result, idx: index }))
      .filter((result) => !result.passed) || [];

  return (
    <Flex
      ref={containerRef}
      direction="column"
      bg="#0d1117"
      overflow="hidden"
      minH={0}
      {...rest}
    >
      {/* ── Editor toolbar ── */}
      <Flex
        px={4} h="44px"
        align="center" justify="space-between"
        flexShrink={0}
        style={{
          background: "rgba(13,17,23,0.95)",
          borderBottom: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        {/* Language selector */}
        <HStack spacing={2}>
          {["python", "javascript"].map((lang) => (
            <Button
              key={lang}
              h="26px" px={3}
              fontSize="11.5px" fontWeight="500"
              borderRadius="6px"
              bg={language === lang ? "rgba(99,179,237,0.12)" : "transparent"}
              color={language === lang ? "blue.300" : "gray.500"}
              border="1px solid"
              borderColor={language === lang ? "rgba(99,179,237,0.25)" : "transparent"}
              _hover={{ bg: "rgba(255,255,255,0.06)", color: "gray.300" }}
              transition="all 0.15s"
              onClick={() => {
                setLanguage(lang);
                onLoadTemplate?.(lang);
              }}
            >
              {lang === "python" ? "Python" : "JavaScript"}
            </Button>
          ))}
        </HStack>

        {/* Actions */}
        <HStack spacing={1.5}>
          <Button
            h="28px" px={3}
            fontSize="11.5px" fontWeight="500"
            borderRadius="6px"
            bg="transparent" color="gray.500"
            border="1px solid rgba(255,255,255,0.07)"
            leftIcon={<RotateCcw size={11} />}
            _hover={{ bg: "rgba(255,255,255,0.06)", color: "gray.400" }}
            transition="all 0.15s"
            onClick={() => onLoadTemplate?.(language)}
          >
            Reset
          </Button>

          <Button
            h="28px" px={3.5}
            fontSize="11.5px" fontWeight="600"
            borderRadius="6px"
            bg="rgba(72,187,120,0.1)"
            color="green.400"
            border="1px solid rgba(72,187,120,0.22)"
            leftIcon={<Play size={11} />}
            isLoading={isRunning}
            loadingText="Running"
            isDisabled={runnerDisabled}
            title={runnerDisabled ? "Test execution is temporarily unavailable" : undefined}
            _hover={{ bg: "rgba(72,187,120,0.18)", color: "green.300" }}
            transition="all 0.15s"
            onClick={onRunCode}
          >
            Run
          </Button>

          <Button
            h="28px" px={3.5}
            fontSize="11.5px" fontWeight="600"
            borderRadius="6px"
            bg={runResult?.all_passed ? "rgba(72,187,120,0.15)" : "rgba(99,179,237,0.1)"}
            color={runResult?.all_passed ? "green.300" : "blue.300"}
            border="1px solid"
            borderColor={runResult?.all_passed ? "rgba(72,187,120,0.28)" : "rgba(99,179,237,0.22)"}
            leftIcon={<Send size={11} />}
            isLoading={isSubmittingCode}
            loadingText="Submitting"
            _hover={{
              bg: runResult?.all_passed ? "rgba(72,187,120,0.22)" : "rgba(99,179,237,0.18)",
              color: runResult?.all_passed ? "green.200" : "blue.200",
            }}
            transition="all 0.15s"
            onClick={onSubmitCode}
          >
            Submit
          </Button>
        </HStack>
      </Flex>

      {/* ── Disabled-runner notice ── */}
      {runnerDisabled && (
        <Flex
          px={4} h="30px" flexShrink={0}
          align="center" gap={2}
          style={{
            background: "rgba(214,158,46,0.1)",
            borderBottom: "1px solid rgba(214,158,46,0.22)",
          }}
        >
          <AlertTriangle size={12} color="#D69E2E" />
          <Text fontSize="11.5px" color="#D69E2E">
            Test execution is temporarily unavailable. You can still submit your code — it just won't be run against test cases.
          </Text>
        </Flex>
      )}

      {/* ── Monaco editor — takes all remaining height ── */}
      <Box flex="1" minH={0} overflow="hidden">
        <Editor
          height="100%"
          theme="vs-dark"
          language={language === "python" ? "python" : "javascript"}
          value={code}
          onChange={(v) => setCode(v ?? "")}
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            lineHeight: 22,
            padding: { top: 16, bottom: 16 },
            smoothScrolling: true,
            scrollBeyondLastLine: false,
            roundedSelection: true,
            cursorBlinking: "smooth",
            cursorSmoothCaretAnimation: "on",
            renderLineHighlight: "gutter",
            fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
            fontLigatures: true,
            tabSize: 2,
            scrollbar: {
              verticalScrollbarSize: 4,
              horizontalScrollbarSize: 4,
            },
          }}
        />
      </Box>

      {/* ── Run results strip (only when there are results) ── */}
      {runResult && (
        <Box
          flexShrink={0}
          h={`${resultsHeight}px`}
          style={{
            borderTop: "1px solid rgba(255,255,255,0.055)",
            background: "rgba(8,10,14,0.9)",
          }}
        >
          <Flex
            h="14px"
            align="center"
            justify="center"
            cursor="row-resize"
            onPointerDown={handleResizeStart}
            style={{ touchAction: "none" }}
          >
            <Box
              h="3px"
              w="44px"
              borderRadius="full"
              bg="rgba(255,255,255,0.14)"
              _hover={{ bg: "rgba(255,255,255,0.22)" }}
              transition="background 0.15s"
            />
          </Flex>

          {/* Summary bar */}
          <Flex
            px={4} h="36px"
            align="center"
            gap={3}
            borderBottom={failedResults.length > 0 ? "1px solid rgba(255,255,255,0.04)" : "none"}
          >
            <Box
              h="7px" w="7px" borderRadius="full" flexShrink={0}
              bg={runResult.all_passed ? "green.400" : "red.400"}
              style={{
                boxShadow: runResult.all_passed
                  ? "0 0 6px rgba(72,187,120,0.7)"
                  : "0 0 6px rgba(252,129,129,0.7)",
              }}
            />
            <Text fontSize="12px" color={runResult.all_passed ? "green.400" : "red.400"} fontWeight="600">
              {runResult.all_passed
                ? `All ${runResult.total} tests passed`
                : `${runResult.passed} / ${runResult.total} tests passed`}
            </Text>
            {runResult.results?.length > 0 && (
              <HStack spacing={1} ml={1}>
                {runResult.results.map((r, i) => (
                  <Box
                    key={i}
                    h="6px" w="6px" borderRadius="full"
                    bg={r.passed ? "green.500" : "red.500"}
                    title={`Case ${i + 1}: ${r.passed ? "Pass" : "Fail"}`}
                  />
                ))}
              </HStack>
            )}
          </Flex>

          {/* Failed case details */}
          {failedResults.length > 0 && (
            <Box
              px={4} py={2.5}
              h={`${Math.max(resultsHeight - SUMMARY_BAR_HEIGHT - 14, 0)}px`}
              overflowY="auto"
              sx={{
                "&::-webkit-scrollbar": { width: "3px" },
                "&::-webkit-scrollbar-thumb": { bg: "rgba(255,255,255,0.07)", borderRadius: "full" },
              }}
            >
              {failedResults.map((r) => (
                <Flex key={r.idx} gap={4} mb={1.5} fontFamily="'JetBrains Mono', monospace" fontSize="11px">
                  <Text color="gray.600" flexShrink={0}>Case {r.idx + 1}</Text>
                  <Text color="gray.500">
                    Expected: <Box as="span" color="green.500">{String(r.expected)}</Box>
                  </Text>
                  <Text color="gray.500">
                    Got: <Box as="span" color="red.400">{String(r.actual)}</Box>
                  </Text>
                </Flex>
              ))}
            </Box>
          )}
        </Box>
      )}
    </Flex>
  );
}
