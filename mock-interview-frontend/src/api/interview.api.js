import api from "./client";

export const createInterview = async (payload) => {
    console.log(payload)
    const res = await api.post("/interview/create", payload);
    return res.data.interview;
};

export const fetchInterview = async (id) => {
    const res = await api.get(`/interview/${id}`);
    return res.data;
};

export const sendReply = async (id, userMessage) => {
    const res = await api.post(`/interview/${id}/reply`, {
        user_message: userMessage
    });
    return res.data;
};
