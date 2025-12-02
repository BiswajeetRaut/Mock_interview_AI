import React from 'react'
import Card from '../components/Card'
import { SimpleGrid } from '@chakra-ui/react'
import { motion } from 'framer-motion'

const MotionGrid = motion(SimpleGrid)

export default function Home() {
  return (
    <MotionGrid initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.35 }} columns={{ base: 1, md: 3 }} spacing="6">
      <Card title="Take Interview" to="/take-interview" description="Create a mock interview tailored to a company, role and experience." />
      <Card title="View Previous Results" to="/results" description="See your past interviews, recordings and feedback." />
      <Card title="Ask mockGPT" to="/ask" description="Ask an AI coach for tips, feedback and interview questions." />
    </MotionGrid>
  )
}
