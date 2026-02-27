import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "JobFish — Autonomous Job Application Agent",
  description:
    "Apply to hundreds of jobs while you sleep. Powered by TinyFish Web Agent API.",
  icons: { icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🐟</text></svg>" },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
