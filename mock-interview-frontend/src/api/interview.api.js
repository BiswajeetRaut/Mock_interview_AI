import api from "./client";

export const createInterview = async (payload) => {
    const res = await api.post("/interview/create", payload);
    return res.data.interview;
};

export const fetchInterview = async (id) => {
    const res = await api.get(`/interview/${id}`);
    return res.data;
};

export const fetchInterviews = async () => {
    const res = await api.get("/interview");
    return res.data.interviews || [];
};

export const sendReply = async (id, userMessage) => {
    const res = await api.post(`/interview/${id}/reply`, {
        user_message: userMessage
    });
    return res.data;
};

export const completeInterview = async (id, durationSeconds) => {
    const res = await api.post(`/interview/${id}/complete`, {
        duration_seconds: durationSeconds
    });
    return res.data.interview;
};
