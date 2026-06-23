"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { authApi } from "@/lib/api/endpoints";
import { clearAuthTokens, getAccessToken, setAuthTokens } from "@/lib/auth-tokens";
import type { LoginRequest, RegisterRequest, UserResponse } from "@/types/api";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  status: AuthStatus;
  user: UserResponse | null;
  login: (payload: LoginRequest) => Promise<void>;
  register: (payload: RegisterRequest) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: Readonly<{ children: React.ReactNode }>): JSX.Element {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<UserResponse | null>(null);

  const refreshUser = useCallback(async () => {
    const token = getAccessToken();

    if (!token) {
      setUser(null);
      setStatus("unauthenticated");
      return;
    }

    try {
      const profile = await authApi.me();
      setUser(profile);
      setStatus("authenticated");
    } catch {
      clearAuthTokens();
      setUser(null);
      setStatus("unauthenticated");
    }
  }, []);

  useEffect(() => {
    void refreshUser();
  }, [refreshUser]);

  const login = useCallback(
    async (payload: LoginRequest) => {
      const tokens = await authApi.login(payload);
      setAuthTokens(tokens);
      await refreshUser();
    },
    [refreshUser]
  );

  const register = useCallback(
    async (payload: RegisterRequest) => {
      const tokens = await authApi.register(payload);
      setAuthTokens(tokens);
      await refreshUser();
    },
    [refreshUser]
  );

  const logout = useCallback(() => {
    clearAuthTokens();
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      login,
      register,
      logout,
      refreshUser
    }),
    [status, user, login, register, logout, refreshUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuthContext(): AuthContextValue {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuthContext must be used within AuthProvider");
  }

  return context;
}
