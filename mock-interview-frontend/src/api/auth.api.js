// src/api/auth.api.js
import api from "./client";

export const fakeGoogleLogin = async () => {
    const res = await api.post("/auth/google/fake", {
        demo: "frontend-demo", // optional
    });
    return res.data; // { access_token, token_type, user }
};
