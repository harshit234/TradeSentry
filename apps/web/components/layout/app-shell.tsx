"use client";

import { useState, createContext, useContext, type ReactNode } from "react";
import { Sidebar } from "./sidebar";
import { TopNav } from "./top-nav";

interface ShellContextType {
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (v: boolean) => void;
}

const ShellContext = createContext<ShellContextType>({
  sidebarCollapsed: false,
  setSidebarCollapsed: () => {},
});

export function useShell() {
  return useContext(ShellContext);
}

export function AppShell({ children }: { children: ReactNode }) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <ShellContext.Provider value={{ sidebarCollapsed, setSidebarCollapsed }}>
      <div className="flex h-screen overflow-hidden bg-slate-50">
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
        <div className="flex flex-1 flex-col overflow-hidden">
          <TopNav />
          <main className="flex-1 overflow-y-auto overflow-x-hidden">
            {children}
          </main>
        </div>
      </div>
    </ShellContext.Provider>
  );
}
