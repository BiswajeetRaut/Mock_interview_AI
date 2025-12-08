import api from "./client";

export const fetchTranscript = async (id) => {
  const res = await api.get(`/interview/${id}/transcript`);
  return res.data;
};
