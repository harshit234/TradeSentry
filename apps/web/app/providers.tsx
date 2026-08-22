"use client";

import { type ReactNode } from "react";
import { ModeProvider } from "@/hooks/use-mode";
import { AppShell } from "@/components/layout/app-shell";

export function ClientProviders({ children }: { children: ReactNode }) {
  return (
    <ModeProvider>
      <AppShell>{children}</AppShell>
    </ModeProvider>
  );
}
