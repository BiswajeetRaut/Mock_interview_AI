// src/context/AuthContext.jsx
import React, { createContext, useContext, useState, useEffect } from "react";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null); // { id, name, email, picture }
    const [token, setToken] = useState(null);

    useEffect(() => {
        const saved = localStorage.getItem("mock_auth");
        if (saved) {
            const parsed = JSON.parse(saved);
            setUser(parsed.user);
            setToken(parsed.access_token);
        }
    }, []);

    const loginWithFakeGoogle = (authResponse) => {
        setUser(authResponse.user);
        setToken(authResponse.access_token);
        localStorage.setItem("mock_auth", JSON.stringify(authResponse));
    };

    const logout = () => {
        setUser(null);
        setToken(null);
        localStorage.removeItem("mock_auth");
    };

    return (
        <AuthContext.Provider value={{ user, token, loginWithFakeGoogle, logout }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext);
