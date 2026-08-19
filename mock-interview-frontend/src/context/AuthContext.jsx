// src/context/AuthContext.jsx
import React, { createContext, useContext, useState, useEffect } from "react";
import { signOut } from "firebase/auth";
import { auth } from "../firebase";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  // Read synchronously as the initial state, not in a useEffect — an effect
  // runs after the first render/commit, which is too late for RequireAuth's
  // redirect decision (it reads `user` on that same first render). Reading
  // it lazily here means an already-logged-in user is recognized on the very
  // first paint, including on a hard reload of a protected route.
  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem("mock_user");
    return savedUser ? JSON.parse(savedUser) : null;
  });

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
