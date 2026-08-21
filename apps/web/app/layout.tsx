import type { Metadata } from "next";
import "./styles.css";
import "./review.css";
import "./table.css";
import "./aws-badge.css";
import "./dashboard-history.css";

export const metadata: Metadata = {
  title: "TradeSentry | Trade Finance Intelligence",
  description: "Human-authorized pre-settlement intelligence for simulated GIFT City IBUs.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
