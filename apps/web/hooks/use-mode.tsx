"use client";

import { createContext, useContext, useState, useCallback, type ReactNode } from "react";

type AppMode = "demo" | "live";

interface ModeContextType {
  mode: AppMode;
  setMode: (mode: AppMode) => void;
  isDemo: boolean;
  isLive: boolean;
  toggleMode: () => void;
}

const ModeContext = createContext<ModeContextType | null>(null);

export function ModeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<AppMode>("demo");

  const toggleMode = useCallback(() => {
    setMode((prev) => (prev === "demo" ? "live" : "demo"));
  }, []);

  return (
    <ModeContext.Provider
      value={{
        mode,
        setMode,
        isDemo: mode === "demo",
        isLive: mode === "live",
        toggleMode,
      }}
    >
      {children}
    </ModeContext.Provider>
  );
}

export function useMode(): ModeContextType {
  const ctx = useContext(ModeContext);
  if (!ctx) throw new Error("useMode must be used within ModeProvider");
  return ctx;
}
