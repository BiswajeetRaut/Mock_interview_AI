import React from "react";
import { SimpleGrid, Box, Text, useColorModeValue, chakra } from "@chakra-ui/react";
import { motion } from "framer-motion";

const MotionBox = motion(chakra.div);

export default function TypeSelector({ types, selected, toggle }) {
    const bg = useColorModeValue("gray.200", "gray.800");
    const activeBg = useColorModeValue("blue.500", "blue.600");

    return (
        <SimpleGrid columns={{ base: 1, md: 2 }} spacing="4" mt="4">
            {types.map((t) => {
                const active = selected.includes(t.id);
                return (
                    <MotionBox
                        key={t.id}
                        p="5"
                        rounded="lg"
                        cursor="pointer"
                        bg={active ? activeBg : bg}
                        color={active ? "white" : "gray.300"}
                        whileHover={{ scale: 1.03 }}
                        whileTap={{ scale: 0.97 }}
                        shadow={active ? "lg" : "md"}
                        onClick={() => toggle(t.id)}
                    >
                        <Text fontSize="lg" fontWeight="semibold">
                            {t.label}
                        </Text>
                        <Text fontSize="sm" opacity="0.8">
                            {t.desc}
                        </Text>
                    </MotionBox>
                );
            })}
        </SimpleGrid>
    );
}
