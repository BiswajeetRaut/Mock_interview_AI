import React from "react";
import { useNavigate } from "react-router-dom";
import { Box, Button, Heading, Text, VStack } from "@chakra-ui/react";
import { motion } from "framer-motion";

import { GoogleAuthProvider, signInWithPopup } from "firebase/auth";
import { googleAuth } from "../api/auth.api";
import { useAuth } from "../context/AuthContext";
import {auth} from "../firebase"

const MotionBox = motion(Box);

export default function Login() {
  const [loading, setLoading] = React.useState(false);
  const navigate = useNavigate();
  const { setUser } = useAuth();

  const handleGoogleLogin = async () => {
    try {
      setLoading(true);

      // 1️⃣ Firebase Google popup
      const provider = new GoogleAuthProvider();
      const result = await signInWithPopup(auth, provider);

      // 2️⃣ Get Firebase ID token
      const token = await result.user.getIdToken();

      // 3️⃣ Send token to backend
      const data = await googleAuth(token);

      // 4️⃣ Save backend user in context
      setUser(data.user);

      navigate("/");
    } catch (err) {
      console.error("Google login failed", err);
    } finally {
      setLoading(false);
    }
  };

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
            <Text color="gray.400" mt="2">
              Sign in with Google to continue to Mock Interview
            </Text>
          </Box>

          <Button
            onClick={handleGoogleLogin}
            isLoading={loading}
            colorScheme="whiteAlpha"
            bg="white"
            color="gray.900"
          >
            Sign in with Google
          </Button>

          <Text fontSize="xs" color="gray.500" textAlign="center" mt="3">
            By continuing you agree to our Terms and Privacy.
          </Text>
        </VStack>
      </MotionBox>
    </Box>
  );
}
