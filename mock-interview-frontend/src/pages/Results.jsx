import React from 'react'
import { api } from '../api/mockApi'
import { Box, Heading, VStack, Text, HStack } from '@chakra-ui/react'

export default function Results() {
  const [results, setResults] = React.useState([])
  React.useEffect(() => { api.fetchResults().then(setResults) }, [])

  return (
    <Box>
      <Heading size="lg" mb="4">Your Results</Heading>
      <VStack spacing="3" align="stretch">
        {results.map(r => (
          <HStack key={r.id} bg="gray.800" p="4" borderRadius="md" justify="space-between">
            <Box>
              <Text fontWeight="medium">{r.company} — {r.role}</Text>
              <Text fontSize="sm" color="gray.400">{r.date}</Text>
            </Box>
            <Box textAlign="right">
              <Text fontSize="lg" fontWeight="semibold">{r.score}%</Text>
              <Text as="a" href="#" color="blue.300" fontSize="sm">View details</Text>
            </Box>
          </HStack>
        ))}
      </VStack>
    </Box>
  )
}
