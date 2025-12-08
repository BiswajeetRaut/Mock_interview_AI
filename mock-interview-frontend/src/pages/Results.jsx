import React from "react";
import { useLocation } from "react-router-dom";
import {
  Box,
  Heading,
  VStack,
  Text,
  HStack,
  Flex,
  Badge,
  Button,
  Divider,
  Icon,
} from "@chakra-ui/react";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";

const MotionBox = motion(Box);

export default function Results() {
  const location = useLocation();
  const newInterview = location.state?.interview; // Retrieve new interview data from state
  const [results, setResults] = React.useState([]);
  console.log(results)
  React.useEffect(() => {
    if (newInterview) {
      setResults((prevResults) => [newInterview, ...prevResults]); // Append new interview to results
    }
  }, [newInterview]);
  return (
    <Box
      px={{ base: 4, md: 8 }}
      py={{ base: 6, md: 10 }}
      maxW="6xl"
      mx="auto"
      color="white"
    >
      {/* PAGE HEADER */}
      <Heading
        size="xl"
        mb={6}
        bgGradient="linear(to-r, blue.300, purple.400)"
        bgClip="text"
      >
        Your Interview Results
      </Heading>

      {results.length === 0 ? (
        <Flex
          h="250px"
          direction="column"
          align="center"
          justify="center"
          bg="rgba(255,255,255,0.05)"
          border="1px solid rgba(255,255,255,0.1)"
          borderRadius="xl"
          backdropFilter="blur(12px)"
        >
          <Text fontSize="lg" color="gray.300">
            No results found yet.
          </Text>
          <Text fontSize="sm" color="gray.500" mt={1}>
            Complete an interview to see your performance summary.
          </Text>
        </Flex>
      ) : (
        <VStack spacing={5} align="stretch">
          {results.map((r) => (
            <MotionBox
              key={r.id}
              p={5}
              rounded="xl"
              bg="rgba(255,255,255,0.05)"
              border="1px solid rgba(255,255,255,0.1)"
              backdropFilter="blur(15px)"
              shadow="md"
              whileHover={{ scale: 1.01, y: -2 }}
              transition={{ duration: 0.2 }}
            >
              <Flex justify="space-between" align="flex-start" direction={{ base: "column", md: "row" }}>
                {/* LEFT SIDE */}
                <Box>
                  <Text fontWeight="semibold" fontSize="lg">
                    {r.company} — {r.role}
                  </Text>
                  <Text fontSize="sm" mt={1} color="gray.400">
                    Experience: {r.experience} years
                  </Text>
                  {r.jd && (
                    <Text fontSize="sm" mt={1} color="gray.400">
                      Job Description: {r.jd}
                    </Text>
                  )}
                  {r.topics && (
                    <Text fontSize="sm" mt={1} color="gray.400">
                      Topics: {Object.keys(r.topics).join(", ")}
                    </Text>
                  )}
                </Box>

                {/* RIGHT SIDE */}
                <Flex
                  direction="column"
                  align={{ base: "flex-start", md: "flex-end" }}
                  mt={{ base: 4, md: 0 }}
                >
                  <Button
                    rightIcon={<Icon as={ArrowRight} size={18} />}
                    size="sm"
                    colorScheme="blue"
                    variant="solid"
                    onClick={() => alert("Detail page coming soon!")}
                  >
                    View Details
                  </Button>
                </Flex>
              </Flex>
            </MotionBox>
          ))}
        </VStack>
      )}
    </Box>
  );
}
