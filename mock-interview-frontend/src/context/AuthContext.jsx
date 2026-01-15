// src/context/AuthContext.jsx
import React, { createContext, useContext, useState, useEffect } from "react";
import { signOut } from "firebase/auth";
import { auth } from "../firebase";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null); // Firestore user

  // Restore user from localStorage
  useEffect(() => {
    const savedUser = localStorage.getItem("mock_user");
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }
  }, []);

  // Save user to localStorage when it changes
  useEffect(() => {
    if (user) {
      localStorage.setItem("mock_user", JSON.stringify(user));
    } else {
      localStorage.removeItem("mock_user");
    }
  }, [user]);

  const logout = async () => {
    await signOut(auth); // Firebase logout
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        setUser,
        logout,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
