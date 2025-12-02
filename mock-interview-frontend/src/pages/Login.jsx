import React from 'react'
import { useNavigate } from 'react-router-dom'
import { Box, Button, Heading, Text, VStack } from '@chakra-ui/react'
import { motion } from 'framer-motion'
import { api } from '../api/mockApi'

const MotionBox = motion(Box)

export default function Login({ setUser }) {
  const [loading, setLoading] = React.useState(false)
  const navigate = useNavigate()

  const onGoogleSignIn = async () => {
    setLoading(true)
    const u = await api.signInWithGoogle()
    setUser(u)
    setLoading(false)
    navigate('/')
  }

  return (
    <Box display="flex" alignItems="center" justifyContent="center" minH="70vh" px="4">
      <MotionBox
        initial={{ scale: 0.98, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.45 }}
        w="full"
        maxW="md"
        bgGradient="linear(to-br, gray.800, gray.900)"
        p="8"
        borderRadius="2xl"
        borderWidth="1px"
        borderColor="gray.700"
        boxShadow="xl"
      >
        <VStack spacing="6" align="stretch">
          <Box>
            <Heading size="lg">Welcome back</Heading>
            <Text color="gray.400" mt="2">Sign in with Google to continue to Mock Interview</Text>
          </Box>

          <Button onClick={onGoogleSignIn} isLoading={loading} colorScheme="whiteAlpha" bg="white" color="gray.900">
            Sign in with Google
          </Button>

          <Text fontSize="xs" color="gray.500" textAlign="center">Or continue as a demo</Text>

          <Button onClick={async () => { setLoading(true); const u = await api.signInWithGoogle(); setUser(u); setLoading(false); navigate('/'); }} variant="outline">
            Continue as demo
          </Button>

          <Text fontSize="xs" color="gray.500" textAlign="center" mt="3">By continuing you agree to our Terms and Privacy.</Text>
        </VStack>
      </MotionBox>
    </Box>
  )
}
