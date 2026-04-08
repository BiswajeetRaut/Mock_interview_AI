import api from "./client";

export const startSession = async (payload) => {
  const res = await api.post("/session/start", payload);
  return res.data;
};

export const submitSessionAnswer = async (sessionId, answerText) => {
  const res = await api.post(`/session/${sessionId}/answer`, {
    answer_text: answerText,
  });
  return res.data;
};

export const fetchSessionState = async (sessionId) => {
  const res = await api.get(`/session/${sessionId}/state`);
  return res.data;
};

export const endSession = async (sessionId, reason = "completed") => {
  const res = await api.post(`/session/${sessionId}/end`, { reason });
  return res.data;
};

export const fetchSessionReport = async (sessionId) => {
  const res = await api.get(`/session/${sessionId}/report`);
  return res.data;
};
