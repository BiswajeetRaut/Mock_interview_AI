import React from "react";
import {
  Box,
  Flex,
  HStack,
  Link,
  Button,
  Text,
  IconButton,
  Avatar,
  Drawer,
  DrawerOverlay,
  DrawerContent,
  DrawerHeader,
  DrawerBody,
  DrawerCloseButton,
  VStack,
  useDisclosure,
  Divider,
} from "@chakra-ui/react";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Menu } from "lucide-react";
import { useAuth } from "../context/AuthContext";

const MotionFlex = motion(Flex);

export default function Header() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const mobileNav = useDisclosure();

  const navItems = [
    { label: "Take Interview", to: "/take-interview" },
    { label: "View Results", to: "/results" },
    { label: "Ask mockGPT", to: "/ask" },
  ];

  return (
    <>
      {/* NAVBAR */}
      <MotionFlex
        as="header"
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.4 }}
        position="sticky"
        top="0"
        zIndex="1000"
        bg="rgba(17, 24, 39, 0.55)"
        backdropFilter="blur(20px)"
        borderBottom="1px solid rgba(255,255,255,0.08)"
        px={{ base: 4, md: 8 }}
        py={3}
        align="center"
        justify="space-between"
      >
        {/* LOGO */}
        <Flex
          as={RouterLink}
          to="/"
          align="center"
          gap={2}
          _hover={{ textDecoration: "none" }}
        >
          <Box
            h="36px"
            w="36px"
            rounded="lg"
            bgGradient="linear(to-br, blue.400, purple.600)"
            display="flex"
            alignItems="center"
            justifyContent="center"
            fontWeight="bold"
            fontSize="lg"
            color="white"
            shadow="md"
          >
            M
          </Box>

          <Text fontSize="xl" fontWeight="bold">
            mock-interview
          </Text>
        </Flex>

        {/* DESKTOP NAV */}
        <HStack
          spacing={6}
          display={{ base: "none", md: "flex" }}
          fontSize="sm"
          color="gray.200"
        >
          {navItems.map((item) => (
            <Link
              key={item.label}
              as={RouterLink}
              to={user ? item.to : "/login"}
              _hover={{ color: "blue.300" }}
            >
              {item.label}
            </Link>
          ))}
        </HStack>

        {/* USER SECTION */}
        <HStack spacing={4} display={{ base: "none", md: "flex" }}>
          {user ? (
            <>
              <HStack spacing={2}>
                <Avatar
                  size="sm"
                  name={user.name}
                  src={user.picture || undefined}
                  bg="blue.600"
                />
                <Text fontSize="sm" fontWeight="medium">
                  {user.name}
                </Text>
              </HStack>

              <Button
                size="sm"
                colorScheme="red"
                onClick={() => {
                  logout();
                  navigate("/login");
                }}
              >
                Sign out
              </Button>
            </>
          ) : (
            <Button
              as={RouterLink}
              to="/login"
              colorScheme="blue"
              size="sm"
              px={6}
            >
              Sign in
            </Button>
          )}
        </HStack>

        {/* MOBILE MENU BUTTON */}
        <IconButton
          display={{ base: "flex", md: "none" }}
          icon={<Menu size={20} />}
          aria-label="Open menu"
          onClick={mobileNav.onOpen}
          bg="transparent"
          color="white"
          _hover={{ bg: "whiteAlpha.200" }}
        />
      </MotionFlex>

      {/* MOBILE DRAWER MENU */}
      <Drawer isOpen={mobileNav.isOpen} placement="left" onClose={mobileNav.onClose}>
        <DrawerOverlay />
        <DrawerContent
          bg="gray.900"
          borderRight="1px solid rgba(255,255,255,0.1)"
        >
          <DrawerCloseButton />
          <DrawerHeader fontSize="xl" fontWeight="bold">
            Navigation
          </DrawerHeader>

          <DrawerBody>
            <VStack align="start" spacing={6} mt={4}>
              {navItems.map((item) => (
                <Link
                  key={item.label}
                  as={RouterLink}
                  to={item.to}
                  fontSize="lg"
                  onClick={mobileNav.onClose}
                  _hover={{ color: "blue.400" }}
                >
                  {item.label}
                </Link>
              ))}

              <Divider opacity={0.3} />

              {/* Mobile User Section */}
              {user ? (
                <VStack align="start" spacing={4}>
                  <HStack spacing={3}>
                    <Avatar
                      size="md"
                      name={user.name}
                      src={user.picture || undefined}
                      bg="blue.600"
                    />
                    <Text fontSize="md">{user.name}</Text>
                  </HStack>

                  <Button
                    width="full"
                    colorScheme="red"
                    onClick={() => {
                      logout();
                      navigate("/login");
                      mobileNav.onClose();
                    }}
                  >
                    Sign out
                  </Button>
                </VStack>
              ) : (
                <Button
                  as={RouterLink}
                  to="/login"
                  width="full"
                  colorScheme="blue"
                  onClick={mobileNav.onClose}
                >
                  Sign in
                </Button>
              )}
            </VStack>
          </DrawerBody>
        </DrawerContent>
      </Drawer>
    </>
  );
}
