import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "JobFish — Autonomous Job Application Agent",
  description: "Apply to hundreds of jobs while you sleep. Powered by TinyFish Web Agent API.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-900 text-slate-100">
        <nav className="border-b border-slate-700 bg-slate-800/50 backdrop-blur">
          <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
            <a href="/" className="flex items-center gap-2 font-bold text-xl text-blue-400">
              🐟 JobFish
            </a>
            <div className="flex gap-6 text-sm text-slate-300">
              <a href="/" className="hover:text-white transition-colors">Search</a>
              <a href="/jobs" className="hover:text-white transition-colors">Jobs</a>
              <a href="/history" className="hover:text-white transition-colors">Applications</a>
            </div>
          </div>
        </nav>
        <main className="max-w-6xl mx-auto px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
