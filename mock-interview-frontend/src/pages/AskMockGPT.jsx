import React from 'react'
import { api } from '../api/mockApi'
import { Box, Heading, Textarea, Button } from '@chakra-ui/react'

export default function AskMockGPT() {
  const [q, setQ] = React.useState('')
  const [resp, setResp] = React.useState(null)

  const ask = async () => {
    const r = await api.askMockGPT(q)
    setResp(r.answer)
  }

  return (
    <Box maxW="2xl">
      <Heading size="lg" mb="4">Ask mockGPT</Heading>
      <Textarea value={q} onChange={(e) => setQ(e.target.value)} minH="160px" bg="gray.800" mb="3" />
      <Box display="flex" gap="2" mb="4">
        <Button colorScheme="blue" onClick={ask}>Ask</Button>
        <Button variant="outline" onClick={() => { setQ(''); setResp(null); }}>Clear</Button>
      </Box>

      {resp && (
        <Box bg="gray.800" p="4" borderRadius="md">
          <Heading size="sm" mb="2">Response</Heading>
          <Box color="gray.300" fontSize="sm">{resp}</Box>
        </Box>
      )}
    </Box>
  )
}
