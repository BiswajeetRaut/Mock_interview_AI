import React from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/mockApi'
import { Box, Button, FormControl, FormLabel, Input, NumberInput, NumberInputField, Select, VStack, Heading } from '@chakra-ui/react'
import { motion } from 'framer-motion'

const MotionBox = motion(Box)

export default function TakeInterview() {
  const [company, setCompany] = React.useState('')
  const [role, setRole] = React.useState('')
  const [experience, setExperience] = React.useState(2)
  const [type, setType] = React.useState('tech-dsa')
  const [created, setCreated] = React.useState(null)
  const [loading, setLoading] = React.useState(false)
  const navigate = useNavigate()

  const submit = async (e) => {
    e.preventDefault()
    setLoading(true)
    const res = await api.createInterview({ company, role, experience, type })
    setCreated(res)
    setLoading(false)
  }

  return (
    <Box>
      <Heading size="lg" mb="4">Design your interview</Heading>

      <MotionBox initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.35 }} bg="gray.800" p="6" borderRadius="md">
        <form onSubmit={submit}>
          <VStack spacing="4" align="stretch">
            <FormControl>
              <FormLabel>Company</FormLabel>
              <Input value={company} onChange={(e) => setCompany(e.target.value)} placeholder="e.g. Google" bg="gray.900" />
            </FormControl>

            <FormControl>
              <FormLabel>Role</FormLabel>
              <Input value={role} onChange={(e) => setRole(e.target.value)} placeholder="e.g. Software Engineer" bg="gray.900" />
            </FormControl>

            <FormControl>
              <FormLabel>Experience (years)</FormLabel>
              <NumberInput value={experience} min={0} onChange={(val) => setExperience(Number(val))}>
                <NumberInputField bg="gray.900" />
              </NumberInput>
            </FormControl>

            <FormControl>
              <FormLabel>Interview Type</FormLabel>
              <Select value={type} onChange={(e) => setType(e.target.value)} bg="gray.900">
                <option value="tech-dsa">Technical - DSA</option>
                <option value="tech-resume">Technical - Resume based</option>
                <option value="managerial">Managerial</option>
              </Select>
            </FormControl>

            <Button type="submit" colorScheme="green" isLoading={loading}>{loading ? 'Creating...' : 'Design Interview'}</Button>
          </VStack>
        </form>
      </MotionBox>

      {created && (
        <MotionBox initial={{ y: 8, opacity: 0 }} animate={{ y: 0, opacity: 1 }} mt="4" bg="gray.800" p="4" borderRadius="md">
          <Heading size="sm" mb="2">Interview created</Heading>
          <Box color="gray.400" mb="3">ID: {created.id}</Box>
          <Button colorScheme="blue" onClick={() => navigate(`/interview/${created.id}`)}>Start Interview</Button>
        </MotionBox>
      )}
    </Box>
  )
}
