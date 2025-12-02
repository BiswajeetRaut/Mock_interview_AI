import React from 'react'
import { Link as RouterLink } from 'react-router-dom'
import { Box, Heading, Text, Link } from '@chakra-ui/react'
import { motion } from 'framer-motion'

const MotionBox = motion(Box)

export default function Card({ title, to, description }) {
  return (
    <MotionBox
      whileHover={{ y: -8 }}
      bg="gray.800"
      borderWidth="1px"
      borderColor="gray.700"
      p="6"
      rounded="lg"
      boxShadow="lg"
    >
      <Link as={RouterLink} to={to} style={{ display: 'block' }}>
        <Heading size="md" mb="2">{title}</Heading>
        <Text color="gray.400" fontSize="sm">{description}</Text>
      </Link>
    </MotionBox>
  )
}
