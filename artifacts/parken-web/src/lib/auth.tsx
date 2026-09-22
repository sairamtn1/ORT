import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, type Role, type User } from "./api";

interface AuthValue {
  user: User | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<User>;
  register: (body: { email: string; password: string; full_name: string; role: Role }) => Promise<User>;
  logout: () => void;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!localStorage.getItem("parken_access_token")) {
      setLoading(false);
      return;
    }
    api.me().then(setUser).catch(() => localStorage.removeItem("parken_access_token")).finally(() => setLoading(false));
  }, []);

  const value = useMemo<AuthValue>(() => ({
    user,
    loading,
    error,
    async login(email, password) {
      setError(null);
      try {
        const token = await api.login({ email, password });
        localStorage.setItem("parken_access_token", token.access_token);
        const nextUser = await api.me();
        setUser(nextUser);
        return nextUser;
      } catch (cause) {
        const message = cause instanceof Error ? cause.message : "Unable to sign in";
        setError(message);
        throw cause;
      }
    },
    async register(body) {
      setError(null);
      try {
        await api.register(body);
        const token = await api.login({ email: body.email, password: body.password });
        localStorage.setItem("parken_access_token", token.access_token);
        const nextUser = await api.me();
        setUser(nextUser);
        return nextUser;
      } catch (cause) {
        const message = cause instanceof Error ? cause.message : "Unable to create account";
        setError(message);
        throw cause;
      }
    },
    logout() {
      localStorage.removeItem("parken_access_token");
      setUser(null);
    },
  }), [user, loading, error]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}