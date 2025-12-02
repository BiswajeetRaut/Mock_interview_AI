import React from 'react'
import { useParams } from 'react-router-dom'
import { Box, Heading, Textarea, Button, Grid, GridItem } from '@chakra-ui/react'
import { motion } from 'framer-motion'

const MotionGrid = motion(Grid)

export default function InterviewPage() {
  const { id } = useParams()
  const [questionIndex, setQuestionIndex] = React.useState(0)
  const [answers, setAnswers] = React.useState([''])
  const questions = [
    { text: 'Explain the difference between array and linked list', id: 'q1' },
    { text: 'Implement two-sum (describe approach)', id: 'q2' },
    { text: 'Describe a time you resolved a conflict in a team', id: 'q3' },
  ]

  const saveAnswer = (text) => {
    const next = [...answers]
    next[questionIndex] = text
    setAnswers(next)
  }

  return (
    <MotionGrid templateColumns={{ base: '1fr', md: '2fr 1fr' }} gap="6" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <GridItem>
        <Box bg="gray.800" p="4" borderRadius="md">
          <Box mb="3" color="gray.400">Interview ID: {id} — Question {questionIndex + 1} / {questions.length}</Box>
          <Heading size="md" mb="3">{questions[questionIndex].text}</Heading>
          <Textarea value={answers[questionIndex] || ''} onChange={(e) => saveAnswer(e.target.value)} minH="200px" bg="gray.900" />
          <Box display="flex" justifyContent="space-between" mt="4">
            <Button onClick={() => setQuestionIndex(Math.max(0, questionIndex - 1))}>Previous</Button>
            <Box>
              <Button mr="2" colorScheme="blue" onClick={() => setQuestionIndex(Math.min(questions.length - 1, questionIndex + 1))}>Next</Button>
              <Button colorScheme="green" onClick={() => alert('Submit flow: send answers to backend (not wired)')}>Submit Interview</Button>
            </Box>
          </Box>
        </Box>
      </GridItem>

      <GridItem>
        <Box bg="gray.800" p="4" borderRadius="md">
          <Heading size="sm" mb="3">Timer</Heading>
          <Box fontSize="2xl" mb="4">00:25:00</Box>
          <Heading size="sm" mb="2">Controls</Heading>
          <Button w="full" mb="2" colorScheme="yellow">Record</Button>
          <Button w="full" variant="outline">Add Note</Button>
        </Box>
      </GridItem>
    </MotionGrid>
  )
}
