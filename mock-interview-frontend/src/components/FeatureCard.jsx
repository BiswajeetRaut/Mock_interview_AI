import React from 'react'
import { Box, Heading, Text, Button, VStack } from '@chakra-ui/react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'

const MotionBox = motion(Box)

export default function FeatureCard({ title, subtitle, description, actionLabel, to, user }) {
  const navigate = useNavigate()

  const handleClick = () => {
    if (!user) {
      navigate('/login')
      return
    }
    navigate(to)
  }

  return (
    <MotionBox
      whileHover={{ y: -8, scale: 1.01 }}
      bg="gray.800"
      borderWidth="1px"
      borderColor="gray.700"
      p="6"
      rounded="lg"
      boxShadow="lg"
    >
      <VStack align="start" spacing="3">
        <Heading size="md">{title}</Heading>
        {subtitle && <Text color="gray.400" fontSize="sm">{subtitle}</Text>}
        <Text color="gray.300" fontSize="sm">{description}</Text>
        <Button mt="2" colorScheme="blue" onClick={handleClick}>{actionLabel}</Button>
      </VStack>
    </MotionBox>
  )
}
