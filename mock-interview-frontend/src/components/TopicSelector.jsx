import React, { useState } from "react";
import {
  Box,
  Text,
  SimpleGrid,
  useColorModeValue,
  chakra
} from "@chakra-ui/react";
import { motion } from "framer-motion";

const MotionBox = motion(chakra.div);

export default function TopicSelector({ topics, selected, setSelected }) {
  const cardBg = useColorModeValue("gray.200", "gray.800");
  const activeBg = useColorModeValue("blue.500", "blue.600");

  const toggle = (t) => {
    if (selected.includes(t)) {
      setSelected(selected.filter((s) => s !== t));
    } else {
      setSelected([...selected, t]);
    }
  };

  return (
    <SimpleGrid columns={{ base: 2, md: 3 }} spacing="4" mt="4">
      {(topics || []).map((topic) => {
        const active = selected.includes(topic);

        return (
          <MotionBox
            key={topic}
            p="4"
            rounded="lg"
            cursor="pointer"
            bg={active ? activeBg : cardBg}
            color={active ? "white" : "gray.300"}
            textAlign="center"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => toggle(topic)}
            transition="0.2s"
          >
            <Text fontWeight="medium">{topic}</Text>
          </MotionBox>
        );
      })}
    </SimpleGrid>
  );
}
