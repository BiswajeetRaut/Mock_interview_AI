import api from "./client";

export const executeCode = async (payload) => {
    const res = await api.post("/coding/run", payload);
    return res.data;
};
