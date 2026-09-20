import { createContext, useContext, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import type { User } from "@/lib/auth";
import { sessionQueryKey } from "@/lib/session";

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const { data, isPending } = useQuery({
    queryKey: sessionQueryKey,
    queryFn: () => apiGet<User | null>("/auth/me"),
    retry: false,
    staleTime: 60_000,
  });
  return <AuthContext.Provider value={{ user: data ?? null, isLoading: isPending }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used within AuthProvider");
  return value;
}