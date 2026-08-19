import axios from "axios";
import { auth } from "../firebase";

const api = axios.create({
    baseURL: "http://127.0.0.1:8000", // FastAPI backend
    headers: { "Content-Type": "application/json" }
});

// Attach a fresh Firebase ID token to every request. getIdToken() returns
// the SDK's cached token and only round-trips to Firebase to refresh it
// when it's near expiry — so this is cheap on the common path.
api.interceptors.request.use(async (config) => {
    // On first load after a page refresh, Firebase rehydrates its session
    // asynchronously — auth.currentUser can be briefly null even though the
    // user is logged in. authStateReady() waits for that to settle once;
    // after the first call it resolves immediately.
    await auth.authStateReady();
    const user = auth.currentUser;
    if (user) {
        const token = await user.getIdToken();
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

export default api;
