import React from 'react'
import { Link as RouterLink, useNavigate } from 'react-router-dom'
import { Box, Flex, HStack, Link, Button, Text } from '@chakra-ui/react'
import { motion } from 'framer-motion'

const MotionBox = motion(Box)

export default function Header({ user, setUser }) {
  const navigate = useNavigate()
  return (
    <MotionBox
      as="header"
      initial={{ y: -24, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.45 }}
      bg="gray.800"
      boxShadow="sm"
      py="3"
    >
      <Flex maxW="container.lg" mx="auto" px="4" align="center" justify="space-between">
        <Link as={RouterLink} to="/" fontWeight="semibold" fontSize="lg">mock-interview</Link>

        <HStack spacing="4" display={{ base: 'none', md: 'flex' }}>
          <Link as={RouterLink} to="/take-interview">Take Interview</Link>
          <Link as={RouterLink} to="/results">View Results</Link>
          <Link as={RouterLink} to="/ask">Ask mockGPT</Link>
        </HStack>

        <Box>
          {user ? (
            <HStack spacing="3">
              <Text fontSize="sm">{user.name}</Text>
              <Button size="sm" colorScheme="red" onClick={() => { setUser(null); navigate('/login') }}>Sign out</Button>
            </HStack>
          ) : (
            <Button as={RouterLink} to="/login" colorScheme="blue" size="sm">Sign in</Button>
          )}
        </Box>
      </Flex>
    </MotionBox>
  )
}
