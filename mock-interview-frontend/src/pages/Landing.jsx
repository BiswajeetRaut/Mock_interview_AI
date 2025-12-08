import React from 'react'
import { Box, Container, Heading, Text, SimpleGrid, VStack, HStack, Icon, Button, List, ListItem, ListIcon } from '@chakra-ui/react'
import { motion } from 'framer-motion'
import { CheckIcon } from '@chakra-ui/icons'
import FeatureCard from '../components/FeatureCard'
import { useAuth } from '../context/AuthContext'

const MotionBox = motion(Box)

export default function Landing() {
  const { user } = useAuth();
  return (
    <Container maxW="7xl" py="10">
      <MotionBox initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
        <SimpleGrid columns={{ base: 1, md: 2 }} spacing="10" alignItems="center">
          <VStack align="start" spacing="6">
            <Heading size="2xl" lineHeight="short">MockInterview — Real practice. Better outcomes.</Heading>
            <Text fontSize="lg" color="gray.300">
              Design and run realistic mock interviews tailored to company, role and experience.
              Choose from DSA, system design, core fundamentals, resume-based or managerial rounds.
              Live code, run tests, get AI feedback, and use curated interview paths for top companies.
            </Text>

            <HStack spacing="3" pt="2">
              <Button colorScheme="blue" onClick={() => window.location.assign(user ? '/take-interview' : '/login')}>Start a mock interview</Button>
              <Button variant="outline" onClick={() => window.location.assign(user ? '/results' : '/login')}>View results</Button>
            </HStack>

            <Box mt="4">
              <Text fontWeight="semibold" mb="2">Why MockInterview — quick highlights</Text>
              <List spacing="2">
                <ListItem><ListIcon as={CheckIcon} color="green.300" />Company-specific interview templates (curated for 20 companies)</ListItem>
                <ListItem><ListIcon as={CheckIcon} color="green.300" />Customizable interviews: DSA, System Design, Resume-focused, Managerial</ListItem>
                <ListItem><ListIcon as={CheckIcon} color="green.300" />In-browser IDE with test-runner for realtime coding experience</ListItem>
                <ListItem><ListIcon as={CheckIcon} color="green.300" />AI-powered feedback and scoring for behavioral and technical answers</ListItem>
              </List>
            </Box>
          </VStack>

          <MotionBox p="6" bg="gray.800" borderRadius="lg" borderWidth="1px" borderColor="gray.700" boxShadow="xl">
            <Heading size="md" mb="3">Product tour</Heading>

            <VStack align="start" spacing="4">
              <Box>
                <Text fontWeight="semibold">Curated company tracks</Text>
                <Text fontSize="sm" color="gray.400">Prebuilt interview flows for top companies — rounds, topics, typical difficulty and sample questions.</Text>
              </Box>

              <Box>
                <Text fontWeight="semibold">Design your interview</Text>
                <Text fontSize="sm" color="gray.400">Pick role, experience level and type. Customize topics and difficulty mix before starting.</Text>
              </Box>

              <Box>
                <Text fontWeight="semibold">Live coding + tests</Text>
                <Text fontSize="sm" color="gray.400">Monaco editor + sandboxed test runner. Run testcases and get instant feedback and score.</Text>
              </Box>

              <Box>
                <Text fontWeight="semibold">AI feedback & transcripts</Text>
                <Text fontSize="sm" color="gray.400">AI coach provides rubric-based feedback for behavioral answers and suggested improvements.</Text>
              </Box>
            </VStack>
          </MotionBox>
        </SimpleGrid>
      </MotionBox>

      <MotionBox mt="12" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}>
        <Heading size="lg" mb="6">Get started</Heading>

        <SimpleGrid columns={{ base: 1, md: 3 }} spacing="6">
          <FeatureCard
            title="Take Interview"
            subtitle="Custom or company-specific"
            description="Create a mock interview tailored to a company, role and your experience. Choose DSA, resume-based, or managerial."
            actionLabel="Design interview"
            to="/take-interview"
            user={user}
          />

          <FeatureCard
            title="View Previous Results"
            subtitle="Review & improve"
            description="Access past sessions, detailed feedback, test results, and suggested study areas to improve faster."
            actionLabel="See results"
            to="/results"
            user={user}
          />

          <FeatureCard
            title="Ask mockGPT"
            subtitle="Get coaching"
            description="Ask the AI coach for feedback, tips, sample questions, or a custom practice plan for your target role."
            actionLabel="Ask mockGPT"
            to="/ask"
            user={user}
          />
        </SimpleGrid>
      </MotionBox>

      <MotionBox mt="12" bg="gray.800" p="6" borderRadius="lg" borderWidth="1px" borderColor="gray.700" boxShadow="lg">
        <Heading size="md" mb="3">Full feature list</Heading>
        <SimpleGrid columns={{ base: 1, md: 2 }} spacing="4">
          <Box>
            <List spacing="2">
              <ListItem><ListIcon as={CheckIcon} color="green.300" />Google Sign-in and profile</ListItem>
              <ListItem><ListIcon as={CheckIcon} color="green.300" />Company-specific templates + LLM enrichment</ListItem>
              <ListItem><ListIcon as={CheckIcon} color="green.300" />Customizable interview design</ListItem>
              <ListItem><ListIcon as={CheckIcon} color="green.300" />Monaco code editor with test-runner</ListItem>
            </List>
          </Box>
          <Box>
            <List spacing="2">
              <ListItem><ListIcon as={CheckIcon} color="green.300" />Automated scoring + AI feedback</ListItem>
              <ListItem><ListIcon as={CheckIcon} color="green.300" />Save sessions & transcripts</ListItem>
              <ListItem><ListIcon as={CheckIcon} color="green.300" />20 curated company tracks</ListItem>
              <ListItem><ListIcon as={CheckIcon} color="green.300" />Resume parsing & resume-based questions</ListItem>
            </List>
          </Box>
        </SimpleGrid>
      </MotionBox>
    </Container>
  )
}
