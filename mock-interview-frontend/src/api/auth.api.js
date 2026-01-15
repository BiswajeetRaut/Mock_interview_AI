// src/api/auth.api.js
import api from "./client";

export const fakeGoogleLogin = async () => {
    const res = await api.post("/auth/google/fake", {
        demo: "frontend-demo", // optional
    });
    return res.data; // { access_token, token_type, user }
};

export async function googleAuth(token) {
    const res = await fetch("http://localhost:8000/auth/google", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  
    if (!res.ok) {
      throw new Error("Auth failed");
    }
  
    return res.json(); // { success, user, isNew }
  }
  
