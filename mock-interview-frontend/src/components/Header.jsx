import React, { useEffect, useState } from "react";
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
  DrawerBody,
  DrawerCloseButton,
  VStack,
  useDisclosure,
  Divider,
} from "@chakra-ui/react";
import { Link as RouterLink, useLocation, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X } from "lucide-react";
import { useAuth } from "../context/AuthContext";

const MotionBox = motion(Box);
const MotionFlex = motion(Flex);

const navItems = [
  { label: "Take Interview", to: "/take-interview" },
  { label: "View Results", to: "/results" },
  { label: "Ask mockGPT", to: "/ask" },
];

export default function Header() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const mobileNav = useDisclosure();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const handleSignOut = () => {
    logout();
    navigate("/login");
    mobileNav.onClose();
  };

  return (
    <>
      <MotionFlex
        as="header"
        initial={{ y: -16, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        position="sticky"
        top="0"
        zIndex={1000}
        px={{ base: 5, md: 10 }}
        py={0}
        align="center"
        justify="space-between"
        h="60px"
        fontFamily="'DM Sans', 'Helvetica Neue', sans-serif"
        style={{
          background: scrolled
            ? "rgba(11, 12, 14, 0.82)"
            : "rgba(11, 12, 14, 0.55)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          borderBottom: scrolled
            ? "1px solid rgba(255,255,255,0.07)"
            : "1px solid transparent",
          transition: "background 0.3s ease, border-color 0.3s ease",
        }}
      >
        {/* ── LOGO ── */}
        <Flex
          as={RouterLink}
          to="/"
          align="center"
          gap={2.5}
          _hover={{ textDecoration: "none", opacity: 0.85 }}
          transition="opacity 0.2s"
        >
          <Box
            h="32px"
            w="32px"
            rounded="9px"
            bg="blue.500"
            display="flex"
            alignItems="center"
            justifyContent="center"
            fontWeight="700"
            fontSize="15px"
            color="white"
            letterSpacing="-0.02em"
            flexShrink={0}
            style={{ boxShadow: "0 0 0 1px rgba(99,179,237,0.3)" }}
          >
            M
          </Box>
          <Text
            fontSize="15px"
            fontWeight="600"
            color="white"
            letterSpacing="-0.02em"
          >
            mock
            <Box as="span" color="blue.400" fontWeight="700">
              interview
            </Box>
          </Text>
        </Flex>

        {/* ── DESKTOP NAV ── */}
        <HStack
          spacing={1}
          display={{ base: "none", md: "flex" }}
          position="absolute"
          left="50%"
          transform="translateX(-50%)"
        >
          {navItems.map((item) => {
            const isActive = location.pathname === item.to;
            return (
              <Link
                key={item.label}
                as={RouterLink}
                to={user ? item.to : "/login"}
                px={4}
                py={1.5}
                fontSize="13.5px"
                fontWeight={isActive ? "600" : "500"}
                color={isActive ? "white" : "gray.400"}
                borderRadius="8px"
                bg={isActive ? "whiteAlpha.100" : "transparent"}
                _hover={{
                  textDecoration: "none",
                  color: "white",
                  bg: "whiteAlpha.80",
                }}
                transition="all 0.18s"
                position="relative"
              >
                {item.label}
                {isActive && (
                  <MotionBox
                    layoutId="nav-indicator"
                    position="absolute"
                    bottom="-1px"
                    left="50%"
                    transform="translateX(-50%)"
                    h="2px"
                    w="16px"
                    borderRadius="full"
                    bg="blue.400"
                  />
                )}
              </Link>
            );
          })}
        </HStack>

        {/* ── USER SECTION ── */}
        <HStack spacing={3} display={{ base: "none", md: "flex" }}>
          {user ? (
            <>
              <HStack
                spacing={2.5}
                px={3}
                py={1.5}
                borderRadius="10px"
                border="1px solid"
                borderColor="whiteAlpha.100"
                _hover={{ borderColor: "whiteAlpha.200", bg: "whiteAlpha.50" }}
                transition="all 0.2s"
              >
                <Avatar
                  size="xs"
                  name={user.name}
                  src={user.picture || undefined}
                  bg="blue.600"
                />
                <Text fontSize="13px" fontWeight="500" color="gray.300">
                  {user.name?.split(" ")[0]}
                </Text>
              </HStack>

              <Button
                size="sm"
                h="34px"
                px={4}
                fontSize="13px"
                fontWeight="500"
                bg="transparent"
                color="gray.500"
                border="1px solid"
                borderColor="whiteAlpha.100"
                borderRadius="9px"
                _hover={{ color: "red.300", borderColor: "red.800", bg: "transparent" }}
                transition="all 0.2s"
                onClick={handleSignOut}
              >
                Sign out
              </Button>
            </>
          ) : (
            <Button
              as={RouterLink}
              to="/login"
              size="sm"
              h="34px"
              px={5}
              fontSize="13px"
              fontWeight="600"
              bg="blue.500"
              color="white"
              borderRadius="9px"
              _hover={{
                bg: "blue.400",
                transform: "translateY(-1px)",
                boxShadow: "0 6px 20px rgba(99,179,237,0.25)",
              }}
              _active={{ transform: "translateY(0)" }}
              transition="all 0.2s"
            >
              Sign in
            </Button>
          )}
        </HStack>

        {/* ── MOBILE BURGER ── */}
        <IconButton
          display={{ base: "flex", md: "none" }}
          icon={mobileNav.isOpen ? <X size={18} /> : <Menu size={18} />}
          aria-label="Toggle menu"
          onClick={mobileNav.isOpen ? mobileNav.onClose : mobileNav.onOpen}
          bg="whiteAlpha.80"
          color="gray.300"
          border="1px solid"
          borderColor="whiteAlpha.100"
          borderRadius="9px"
          h="34px"
          w="34px"
          minW="34px"
          _hover={{ bg: "whiteAlpha.200", color: "white" }}
          transition="all 0.2s"
        />
      </MotionFlex>

      {/* ── MOBILE DRAWER ── */}
      <Drawer
        isOpen={mobileNav.isOpen}
        placement="right"
        onClose={mobileNav.onClose}
        size="xs"
      >
        <DrawerOverlay bg="blackAlpha.700" backdropFilter="blur(6px)" />
        <DrawerContent
          bg="#0f1012"
          border="none"
          borderLeft="1px solid"
          borderColor="whiteAlpha.100"
          fontFamily="'DM Sans', sans-serif"
        >
          <DrawerCloseButton
            color="gray.500"
            _hover={{ color: "white" }}
            top={4}
            right={4}
          />

          <DrawerBody pt={14} px={6}>
            <VStack align="start" spacing={1} w="full">
              {navItems.map((item, i) => {
                const isActive = location.pathname === item.to;
                return (
                  <MotionBox
                    key={item.label}
                    initial={{ opacity: 0, x: 16 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.06, duration: 0.3 }}
                    w="full"
                  >
                    <Link
                      as={RouterLink}
                      to={user ? item.to : "/login"}
                      display="block"
                      w="full"
                      px={4}
                      py={3}
                      fontSize="15px"
                      fontWeight={isActive ? "600" : "500"}
                      color={isActive ? "white" : "gray.400"}
                      bg={isActive ? "whiteAlpha.100" : "transparent"}
                      borderRadius="10px"
                      _hover={{
                        textDecoration: "none",
                        color: "white",
                        bg: "whiteAlpha.80",
                      }}
                      transition="all 0.18s"
                      onClick={mobileNav.onClose}
                    >
                      {item.label}
                    </Link>
                  </MotionBox>
                );
              })}

              <Divider
                borderColor="whiteAlpha.100"
                my={4}
              />

              {user ? (
                <VStack align="start" spacing={4} w="full">
                  <HStack spacing={3} px={1}>
                    <Avatar
                      size="sm"
                      name={user.name}
                      src={user.picture || undefined}
                      bg="blue.600"
                    />
                    <Box>
                      <Text fontSize="14px" fontWeight="600" color="gray.200">
                        {user.name}
                      </Text>
                      <Text fontSize="12px" color="gray.600">
                        Signed in
                      </Text>
                    </Box>
                  </HStack>

                  <Button
                    w="full"
                    size="sm"
                    h="38px"
                    fontSize="13px"
                    fontWeight="500"
                    bg="transparent"
                    color="gray.500"
                    border="1px solid"
                    borderColor="whiteAlpha.100"
                    borderRadius="9px"
                    _hover={{ color: "red.300", borderColor: "red.800" }}
                    transition="all 0.2s"
                    onClick={handleSignOut}
                  >
                    Sign out
                  </Button>
                </VStack>
              ) : (
                <Button
                  as={RouterLink}
                  to="/login"
                  w="full"
                  size="sm"
                  h="40px"
                  fontSize="14px"
                  fontWeight="600"
                  bg="blue.500"
                  color="white"
                  borderRadius="10px"
                  _hover={{ bg: "blue.400" }}
                  transition="all 0.2s"
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