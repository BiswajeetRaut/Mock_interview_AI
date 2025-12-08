import React, { useState, useRef, useEffect } from "react";
import {
    VStack,
    FormControl,
    FormLabel,
    Input,
    Textarea,
    NumberInput,
    NumberInputField,
    Select,
    Text,
    Box,
    chakra,
    useColorModeValue,
    Button,
    CloseButton
} from "@chakra-ui/react";
import { motion, AnimatePresence } from "framer-motion";

const MotionBox = motion(chakra.div);

const ROLE_LIST = [
    "Software Engineer", "SDE I", "SDE II", "Senior Software Engineer",
    "Backend Engineer", "Frontend Engineer", "Full Stack Engineer",
    "Machine Learning Engineer", "Data Engineer", "SRE", "DevOps Engineer",
    "Mobile Engineer", "AI Engineer", "Technical Lead", "Engineering Manager",
    "Intern", "UI Engineer", "Platform Engineer"
];

export default function InterviewForm({ company, custom = false, onSubmit }) {
    const [role, setRole] = useState("");
    const [exp, setExp] = useState(2);
    const [types, setType] = useState("tech-dsa");
    const [jd, setJd] = useState("");
    const [resume, setResume] = useState(null);
    const fileInputRef = useRef();

    const [open, setOpen] = useState(false);
    const [highlightIndex, setHighlightIndex] = useState(-1);
    const wrapperRef = useRef(null);

    const borderClr = useColorModeValue("gray.300", "gray.600");

    const filtered =
        role.trim() === ""
            ? []
            : ROLE_LIST.filter((r) =>
                r.toLowerCase().includes(role.toLowerCase())
            );

    useEffect(() => {
        const handler = (e) => {
            if (!wrapperRef.current || !wrapperRef.current.contains(e.target)) {
                setOpen(false);
                setHighlightIndex(-1);
            }
        };
        document.addEventListener("mousedown", handler);
        return () => document.removeEventListener("mousedown", handler);
    }, []);

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
                setRole(filtered[highlightIndex]);
                setOpen(false);
            }
        }
    };

    const handleContinue = () => {
        const topics = { [types]: true }; // Convert `types` to a dictionary

        onSubmit({
            company,
            role,
            experience: exp,
            topics,
            jd: custom ? jd : null,
            resume
        });
    };

    const isFormValid = () => {
        if (!role.trim() || exp < 0 || (!custom && !types) || (custom && !jd.trim())) {
            return false;
        }
        return true;
    };

    return (
        <VStack spacing="5" align="stretch" ref={wrapperRef}>
            {/* ROLE AUTOCOMPLETE FIELD */}
            <FormControl>
                <FormLabel fontWeight="semibold">Role</FormLabel>

                <Input
                    placeholder="Type your role..."
                    bg="gray.900"
                    value={role}
                    height="48px"
                    onFocus={() => setOpen(true)}
                    onChange={(e) => {
                        setRole(e.target.value);
                        setOpen(true);
                    }}
                    onKeyDown={handleKeyDown}
                    autoComplete="off"
                />

                <AnimatePresence>
                    {open && filtered.length > 0 && (
                        <MotionBox
                            mt="2"
                            rounded="md"
                            border="1px solid"
                            borderColor={borderClr}
                            bg="gray.900"
                            overflow="hidden"
                            shadow="xl"
                            initial={{ opacity: 0, y: 6 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: 6 }}
                        >
                            {filtered.map((item, index) => (
                                <Box
                                    key={item}
                                    px="4"
                                    py="3"
                                    cursor="pointer"
                                    bg={index === highlightIndex ? "blue.600" : "gray.900"}
                                    _hover={{ bg: "blue.700" }}
                                    onMouseDown={() => {
                                        setRole(item);
                                        setOpen(false);
                                    }}
                                >
                                    <Text color={index === highlightIndex ? "white" : "gray.200"}>
                                        {item}
                                    </Text>
                                </Box>
                            ))}
                        </MotionBox>
                    )}
                </AnimatePresence>
            </FormControl>

            {/* EXPERIENCE */}
            <FormControl>
                <FormLabel fontWeight="semibold">Experience (years)</FormLabel>
                <NumberInput value={exp} min={0} onChange={(v) => setExp(v)}>
                    <NumberInputField bg="gray.900" />
                </NumberInput>
            </FormControl>

            {/* INTERVIEW TYPE */}
            {!custom && <FormControl>
                <FormLabel fontWeight="semibold">Interview Type</FormLabel>
                <Select
                    value={types}
                    onChange={(e) => setType(e.target.value)}
                    bg="gray.900"
                >
                    <option value="tech-dsa">Technical — DSA</option>
                    <option value="tech-resume">Resume Based</option>
                    <option value="system-design">System Design</option>
                    <option value="managerial">Managerial</option>
                </Select>
            </FormControl>}

            {/* OPTIONAL JD FIELD */}
            {custom && (
                <FormControl>
                    <FormLabel fontWeight="semibold">Job Description</FormLabel>
                    <Textarea
                        bg="gray.900"
                        placeholder="Paste the JD or describe..."
                        value={jd}
                        onChange={(e) => setJd(e.target.value)}
                    />
                </FormControl>
            )}
            {/* RESUME UPLOAD FIELD */}
            <FormControl>
                <FormLabel fontWeight="semibold">Resume (optional)</FormLabel>

                {/* Drag + Drop container */}
                <Box
                    bg="gray.900"
                    p="5"
                    rounded="lg"
                    border="2px dashed"
                    borderColor="gray.600"
                    textAlign="center"
                    cursor="pointer"
                    _hover={{ borderColor: "blue.400" }}
                    onDragOver={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                    }}
                    onDrop={(e) => {
                        e.preventDefault();
                        const file = e.dataTransfer.files[0];
                        if (file) setResume(file);
                    }}
                    onClick={() => fileInputRef.current.click()}
                >
                    {!resume && <Text color="gray.400">
                        Drag & Drop Resume here, or <strong>click to browse</strong>
                    </Text>}

                    {resume && (
                        <Box display="flex" alignItems="center" justifyContent="center">
                            <Text color="blue.300" mr="2">
                                Uploaded: {resume.name}
                            </Text>
                            <CloseButton
                                size="sm"
                                onClick={() => setResume(null)}
                                aria-label="Remove uploaded resume"
                            />
                        </Box>
                    )}
                </Box>

                {/* Hidden file input */}
                <input
                    type="file"
                    accept=".pdf,.doc,.docx,.txt"
                    style={{ display: "none" }}
                    ref={fileInputRef}
                    onChange={(e) => {
                        if (e.target.files[0]) setResume(e.target.files[0]);
                    }}
                />
            </FormControl>

            <Button
                colorScheme="blue"
                size="lg"
                onClick={handleContinue}
                isDisabled={!isFormValid()}
            >
                {custom ? "Continue" : "Start Interview"}
            </Button>
        </VStack>
    );
}
