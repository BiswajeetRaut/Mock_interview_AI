import React, { useState, useRef, useEffect } from "react";
import {
  Box,
  VStack,
  Heading,
  Input,
  InputGroup,
  InputLeftElement,
  Text,
  useColorModeValue,
  Icon,
  SimpleGrid,
  Button,
  chakra
} from "@chakra-ui/react";
import { SearchIcon } from "@chakra-ui/icons";
import { AnimatePresence, motion } from "framer-motion";
import { useNavigate } from "react-router-dom";

const MotionBox = motion(chakra.div);
import { TOP_COMPANIES } from "../data/companies";


export default function TakeInterviewSelectCompany() {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState(-1);

  const navigate = useNavigate();
  const wrapperRef = useRef(null);

  const bgCard = useColorModeValue("whiteAlpha.200", "gray.800");
  const bgHover = useColorModeValue("whiteAlpha.300", "gray.700");
  const borderClr = useColorModeValue("gray.300", "gray.600");

  // SMART FILTERING
  const filtered =
    query.trim() === ""
      ? []
      : TOP_COMPANIES.filter((c) =>
        c.toLowerCase().includes(query.toLowerCase())
      );

  // CLICK OUTSIDE TO CLOSE
  useEffect(() => {
    const handler = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setOpen(false);
        setHighlightIndex(-1);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleSelection = (company) => {
    if (!company) return;

    if (TOP_COMPANIES.map(c => c.toLowerCase()).includes(company.trim().toLowerCase())) {
      navigate(`/take-interview/known?company=${company}`);
    } else {
      navigate(`/take-interview/custom?company=${company}`);
    }

  };

  const handleKeyDown = (e) => {
    if (!open) return;

    if (e.key === "ArrowDown") {
      setHighlightIndex((prev) =>
        prev < filtered.length - 1 ? prev + 1 : prev
      );
    }

    if (e.key === "ArrowUp") {
      setHighlightIndex((prev) => (prev > 0 ? prev - 1 : prev));
    }

    if (e.key === "Enter") {
      if (highlightIndex >= 0) {
        handleSelection(filtered[highlightIndex]);
      } else {
        handleSelection(query);
      }
    }
  };

  return (
    <Box maxW="600px" mx="auto" mt="60px" ref={wrapperRef} px="2">
      <Heading mb="8" textAlign="center" fontWeight="bold">
        Select Company
      </Heading>

      {/* Search */}
      <InputGroup>
        <InputLeftElement pointerEvents="none">
          <Icon as={SearchIcon} color="gray.500" />
        </InputLeftElement>

        <Input
          placeholder="Start typing…"
          value={query}
          bg="gray.800"
          height="52px"
          borderRadius="lg"
          borderColor={borderClr}
          onFocus={() => setOpen(true)}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onKeyDown={handleKeyDown}
        />
      </InputGroup>

      {/* Dropdown */}
      <AnimatePresence>
        {open && filtered.length > 0 && (
          <MotionBox
            mt="3"
            rounded="lg"
            border="1px solid"
            borderColor={borderClr}
            bg="gray.900"
            overflow="hidden"
            shadow="xl"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 6 }}
            transition={{ duration: 0.15 }}
          >
            {filtered.map((company, index) => {
              const active = index === highlightIndex;
              return (
                <Box
                  key={company}
                  px="4"
                  py="3.5"
                  cursor="pointer"
                  bg={active ? "blue.600" : "gray.900"}
                  _hover={{ bg: "blue.700" }}
                  onMouseDown={() => handleSelection(company)}
                >
                  <Text
                    fontWeight="medium"
                    color={active ? "white" : "gray.200"}
                  >
                    {company}
                  </Text>
                </Box>
              );
            })}
          </MotionBox>
        )}
      </AnimatePresence>

      {/* Button spacing fixed */}
      <Button
        w="full"
        colorScheme="blue"
        size="lg"
        mt="8"
        borderRadius="lg"
        onClick={() => handleSelection(query)}
      >
        Continue
      </Button>

      {/* Suggested Companies */}
      <Heading size="sm" mt="10" mb="4" textAlign="left" w="full">
        Popular Companies
      </Heading>

      <SimpleGrid columns={{ base: 2, md: 3 }} spacing="5" w="full">
        {TOP_COMPANIES.slice(0, 9).map((c) => (
          <MotionBox
            key={c}
            p="5"
            bg={bgCard}
            borderRadius="lg"
            textAlign="center"
            cursor="pointer"
            whileHover={{ scale: 1.05, y: -3 }}
            transition={{ duration: 0.2 }}
            _hover={{ bg: bgHover }}
            onClick={() => handleSelection(c)}
          >
            <Text fontWeight="semibold">{c}</Text>
          </MotionBox>
        ))}
      </SimpleGrid>
    </Box>
  );

}
