import React, { useEffect, useRef } from 'react'
import {
  Box, Container, Heading, Text, SimpleGrid, VStack, HStack,
  Icon, Button, List, ListItem, Flex, Badge, Divider, Grid, GridItem
} from '@chakra-ui/react'
import { motion, useInView } from 'framer-motion'
import { CheckIcon } from '@chakra-ui/icons'
import FeatureCard from '../components/FeatureCard'
import { useAuth } from '../context/AuthContext'

const MotionBox = motion(Box)
const MotionText = motion(Text)
const MotionHeading = motion(Heading)
const MotionFlex = motion(Flex)

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 24 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.65, ease: [0.22, 1, 0.36, 1], delay },
})

const fadeIn = (delay = 0) => ({
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  transition: { duration: 0.7, delay },
})

function RevealBlock({ children, delay = 0, style = {} }) {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: '-60px' })
  return (
    <MotionBox
      ref={ref}
      initial={{ opacity: 0, y: 28 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1], delay }}
      style={style}
    >
      {children}
    </MotionBox>
  )
}

const stat = [
  { value: '20+', label: 'Company tracks' },
  { value: '5', label: 'Interview types' },
  { value: '1000+', label: 'Practice questions' },
  { value: 'AI', label: 'Real-time feedback' },
]

const rounds = [
  { tag: 'DSA', title: 'Data Structures & Algorithms', desc: 'Timed coding rounds with Monaco IDE, testcases, and instant pass/fail feedback.' },
  { tag: 'System Design', title: 'Architecture Deep-dives', desc: 'Open-ended design challenges evaluated by an AI rubric for breadth, depth, and tradeoffs.' },
  { tag: 'Behavioural', title: 'STAR-format coaching', desc: 'Structured response analysis with suggestions on framing, specifics, and impact.' },
  { tag: 'Resume', title: 'Resume-based rounds', desc: 'Upload your CV and get questions crafted from your own experience and target role.' },
  { tag: 'Managerial', title: 'Leadership & culture-fit', desc: 'Scenario-driven questions for senior roles — evaluated against leadership principles.' },
]

export default function Landing() {
  const { user } = useAuth()

  return (
    <Box
      minH="100vh"
      bg="#0b0c0e"
      color="white"
      fontFamily="'DM Sans', 'Helvetica Neue', sans-serif"
      overflowX="hidden"
    >
      {/* Subtle grid background */}
      <Box
        position="fixed"
        inset={0}
        pointerEvents="none"
        zIndex={0}
        style={{
          backgroundImage:
            'linear-gradient(rgba(255,255,255,0.028) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.028) 1px, transparent 1px)',
          backgroundSize: '48px 48px',
        }}
      />

      {/* Glow accent */}
      <Box
        position="fixed"
        top="-200px"
        right="-200px"
        w="600px"
        h="600px"
        borderRadius="full"
        pointerEvents="none"
        zIndex={0}
        style={{
          background: 'radial-gradient(circle, rgba(99,179,237,0.07) 0%, transparent 70%)',
        }}
      />

      <Container maxW="1100px" position="relative" zIndex={1} pt={{ base: 16, md: 24 }} pb={24}>

        {/* ── HERO ── */}
        <Grid templateColumns={{ base: '1fr', md: '1fr 1fr' }} gap={16} alignItems="center" mb={24}>
          <GridItem>
            <MotionBox {...fadeIn(0)}>
              <Badge
                bg="whiteAlpha.100"
                color="blue.200"
                border="1px solid"
                borderColor="blue.800"
                px={3} py={1}
                borderRadius="full"
                fontSize="xs"
                letterSpacing="widest"
                textTransform="uppercase"
                mb={6}
                display="inline-flex"
              >
                Interview preparation · AI-powered
              </Badge>
            </MotionBox>

            <MotionHeading
              {...fadeUp(0.08)}
              fontSize={{ base: '3.4rem', md: '4.2rem' }}
              lineHeight="1.07"
              fontWeight="700"
              letterSpacing="-0.03em"
              fontFamily="'DM Sans', sans-serif"
              mb={6}
            >
              Practice like it's{' '}
              <Box as="span" color="blue.300">
                the real thing.
              </Box>
            </MotionHeading>

            <MotionText {...fadeUp(0.16)} fontSize="lg" color="gray.400" lineHeight="1.8" mb={9} maxW="440px">
              Mock interviews tailored to company, role, and experience — with a live IDE, AI feedback, and curated paths for 20+ top companies.
            </MotionText>

            <MotionFlex {...fadeUp(0.22)} gap={3} wrap="wrap">
              <Button
                size="lg"
                bg="blue.500"
                color="white"
                _hover={{ bg: 'blue.400', transform: 'translateY(-1px)', boxShadow: '0 8px 30px rgba(99,179,237,0.3)' }}
                _active={{ transform: 'translateY(0)' }}
                transition="all 0.2s"
                fontWeight="600"
                px={7}
                borderRadius="10px"
                onClick={() => window.location.assign(user ? '/take-interview' : '/login')}
              >
                Start a mock interview
              </Button>
              <Button
                size="lg"
                variant="ghost"
                color="gray.300"
                border="1px solid"
                borderColor="whiteAlpha.200"
                _hover={{ borderColor: 'blue.500', color: 'white', bg: 'whiteAlpha.50' }}
                transition="all 0.2s"
                fontWeight="500"
                px={7}
                borderRadius="10px"
                onClick={() => window.location.assign(user ? '/results' : '/login')}
              >
                View results
              </Button>
            </MotionFlex>
          </GridItem>

          {/* Stats block */}
          <GridItem>
            <RevealBlock delay={0.1}>
              <SimpleGrid columns={2} gap={4}>
                {stat.map((s, i) => (
                  <MotionBox
                    key={s.label}
                    initial={{ opacity: 0, scale: 0.94 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.18 + i * 0.07, duration: 0.5, ease: 'easeOut' }}
                    bg="whiteAlpha.50"
                    border="1px solid"
                    borderColor="whiteAlpha.100"
                    borderRadius="16px"
                    p={6}
                    backdropFilter="blur(6px)"
                    _hover={{ borderColor: 'blue.700', bg: 'whiteAlpha.100' }}
                  >
                    <Text fontSize="2.6rem" fontWeight="700" letterSpacing="-0.04em" color="white" lineHeight="1">
                      {s.value}
                    </Text>
                    <Text fontSize="sm" color="gray.500" mt={2} fontWeight="500">
                      {s.label}
                    </Text>
                  </MotionBox>
                ))}
              </SimpleGrid>
            </RevealBlock>
          </GridItem>
        </Grid>

        {/* ── DIVIDER ── */}
        <Divider borderColor="whiteAlpha.100" mb={24} />

        {/* ── ROUND TYPES ── */}
        <RevealBlock>
          <Flex justify="space-between" align="flex-end" mb={10} flexWrap="wrap" gap={4}>
            <Box>
              <Text fontSize="xs" color="blue.400" fontWeight="600" letterSpacing="widest" textTransform="uppercase" mb={2}>
                Coverage
              </Text>
              <Heading fontSize={{ base: '2xl', md: '3xl' }} fontWeight="700" letterSpacing="-0.03em">
                Every kind of round, covered.
              </Heading>
            </Box>
          </Flex>
        </RevealBlock>

        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} gap={5} mb={24}>
          {rounds.map((r, i) => (
            <RevealBlock key={r.tag} delay={i * 0.06}>
              <Box
                h="100%"
                bg="whiteAlpha.40"
                border="1px solid"
                borderColor="whiteAlpha.100"
                borderRadius="16px"
                p={6}
                position="relative"
                overflow="hidden"
                _hover={{
                  borderColor: 'blue.700',
                  bg: 'rgba(99,179,237,0.04)',
                  transform: 'translateY(-3px)',
                  boxShadow: '0 12px 40px rgba(0,0,0,0.4)',
                }}
                transition="all 0.25s ease"
                cursor="default"
              >
                <Badge
                  bg="blue.900"
                  color="blue.300"
                  borderRadius="6px"
                  px={2.5}
                  py={0.5}
                  fontSize="2xs"
                  fontWeight="600"
                  letterSpacing="wider"
                  textTransform="uppercase"
                  mb={4}
                  display="inline-block"
                >
                  {r.tag}
                </Badge>
                <Text fontWeight="600" fontSize="md" mb={2} color="gray.100" letterSpacing="-0.01em">
                  {r.title}
                </Text>
                <Text fontSize="sm" color="gray.500" lineHeight="1.75">
                  {r.desc}
                </Text>
              </Box>
            </RevealBlock>
          ))}

          {/* CTA card */}
          <RevealBlock delay={rounds.length * 0.06}>
            <Box
              h="100%"
              bg="blue.900"
              border="1px solid"
              borderColor="blue.700"
              borderRadius="16px"
              p={6}
              display="flex"
              flexDirection="column"
              justifyContent="space-between"
              _hover={{ transform: 'translateY(-3px)', boxShadow: '0 12px 40px rgba(99,179,237,0.15)' }}
              transition="all 0.25s ease"
            >
              <Box>
                <Text fontWeight="700" fontSize="lg" color="blue.100" letterSpacing="-0.02em" mb={2}>
                  Design your own
                </Text>
                <Text fontSize="sm" color="blue.300" lineHeight="1.75">
                  Mix and match round types, difficulty, topics, and experience level to build a fully custom session.
                </Text>
              </Box>
              <Button
                mt={6}
                size="sm"
                bg="blue.500"
                color="white"
                _hover={{ bg: 'blue.400' }}
                borderRadius="8px"
                fontWeight="600"
                alignSelf="flex-start"
                onClick={() => window.location.assign(user ? '/take-interview' : '/login')}
              >
                Build interview →
              </Button>
            </Box>
          </RevealBlock>
        </SimpleGrid>

        {/* ── FEATURE TRIO ── */}
        <RevealBlock>
          <Text fontSize="xs" color="blue.400" fontWeight="600" letterSpacing="widest" textTransform="uppercase" mb={2}>
            Features
          </Text>
          <Heading fontSize={{ base: '2xl', md: '3xl' }} fontWeight="700" letterSpacing="-0.03em" mb={10}>
            Built for serious prep.
          </Heading>
        </RevealBlock>

        <SimpleGrid columns={{ base: 1, md: 3 }} gap={5} mb={24}>
          {[
            {
              title: 'Take Interview',
              sub: 'Custom or company-specific',
              desc: 'Pick a target company or design from scratch. Set the role, experience level, and round type — then start.',
              cta: 'Design interview',
              to: '/take-interview',
            },
            {
              title: 'Review Results',
              sub: 'Detailed session history',
              desc: 'Access full transcripts, test results, AI scoring breakdowns, and targeted study recommendations.',
              cta: 'See results',
              to: '/results',
            },
            {
              title: 'Ask mockGPT',
              sub: 'On-demand coaching',
              desc: 'Get sample questions, topic explanations, or a custom study plan built around your gaps and goals.',
              cta: 'Open coach',
              to: '/ask',
            },
          ].map((card, i) => (
            <RevealBlock key={card.title} delay={i * 0.07}>
              <FeatureCard
                title={card.title}
                subtitle={card.sub}
                description={card.desc}
                actionLabel={card.cta}
                to={card.to}
                user={user}
              />
            </RevealBlock>
          ))}
        </SimpleGrid>

        {/* ── FULL FEATURE LIST ── */}
        <RevealBlock>
          <Box
            bg="whiteAlpha.40"
            border="1px solid"
            borderColor="whiteAlpha.100"
            borderRadius="20px"
            p={{ base: 8, md: 10 }}
          >
            <Flex justify="space-between" align="flex-start" mb={8} flexWrap="wrap" gap={6}>
              <Box>
                <Text fontSize="xs" color="blue.400" fontWeight="600" letterSpacing="widest" textTransform="uppercase" mb={2}>
                  Everything included
                </Text>
                <Heading fontSize="xl" fontWeight="700" letterSpacing="-0.02em">
                  No paywalled features.
                </Heading>
              </Box>
            </Flex>

            <SimpleGrid columns={{ base: 1, md: 2 }} gap={3}>
              {[
                'Google Sign-in and profile management',
                'Monaco code editor with sandboxed test-runner',
                'Company-specific templates for 20+ companies',
                'Automated scoring and AI rubric feedback',
                'Customisable round designer — role, level, type',
                'Full session save with transcripts',
                'Resume upload + resume-based question generation',
                'mockGPT coach for plans, tips, and deep-dives',
              ].map((feat) => (
                <HStack key={feat} spacing={3} align="flex-start">
                  <Icon as={CheckIcon} color="blue.400" mt="4px" flexShrink={0} boxSize={3} />
                  <Text fontSize="sm" color="gray.400" lineHeight="1.6">
                    {feat}
                  </Text>
                </HStack>
              ))}
            </SimpleGrid>
          </Box>
        </RevealBlock>

        {/* ── BOTTOM CTA ── */}
        <RevealBlock delay={0.1}>
          <Flex
            mt={16}
            direction="column"
            align="center"
            textAlign="center"
            gap={6}
          >
            <Heading fontSize={{ base: '2xl', md: '3.2rem' }} fontWeight="700" letterSpacing="-0.03em" maxW="560px">
              Ready to get uncomfortable?
            </Heading>
            <Text color="gray.500" fontSize="md" maxW="380px" lineHeight="1.8">
              The best interviewees practise more, not differently. Start your first session in under a minute.
            </Text>
            <Button
              size="lg"
              bg="blue.500"
              color="white"
              _hover={{ bg: 'blue.400', transform: 'translateY(-2px)', boxShadow: '0 12px 36px rgba(99,179,237,0.35)' }}
              _active={{ transform: 'translateY(0)' }}
              transition="all 0.2s"
              fontWeight="600"
              px={9}
              borderRadius="10px"
              onClick={() => window.location.assign(user ? '/take-interview' : '/login')}
            >
              Start free →
            </Button>
          </Flex>
        </RevealBlock>

      </Container>
    </Box>
  )
}