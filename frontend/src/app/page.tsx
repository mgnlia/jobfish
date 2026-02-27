"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const BOARDS = ["linkedin", "indeed", "greenhouse", "lever"];

export default function HomePage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [location, setLocation] = useState("Remote");
  const [boards, setBoards] = useState<string[]>(["linkedin", "indeed"]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [streamingUrl, setStreamingUrl] = useState("");

  const toggleBoard = (b: string) =>
    setBoards((prev) => (prev.includes(b) ? prev.filter((x) => x !== b) : [...prev, b]));

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError("");
    setStreamingUrl("");
    try {
      const res = await fetch(`${API}/api/search-jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, location, boards }),
      });
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const data = await res.json();
      if (data.streaming_url) setStreamingUrl(data.streaming_url);
      router.push("/jobs");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-10">
        <h1 className="text-5xl font-bold text-blue-400 mb-3">🐟 JobFish</h1>
        <p className="text-slate-400 text-lg">
          Apply to hundreds of jobs while you sleep.<br />
          Powered by <span className="text-blue-300 font-medium">TinyFish Web Agent API</span>.
        </p>
      </div>

      <form onSubmit={handleSearch} className="bg-slate-800 rounded-2xl p-6 space-y-4 border border-slate-700">
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">Job title or keywords</label>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. Senior Software Engineer, Python Developer"
            className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2.5 text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">Location</label>
          <input
            type="text"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g. Remote, San Francisco CA, New York NY"
            className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2.5 text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">Job boards</label>
          <div className="flex gap-2 flex-wrap">
            {BOARDS.map((b) => (
              <button
                key={b}
                type="button"
                onClick={() => toggleBoard(b)}
                className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                  boards.includes(b)
                    ? "bg-blue-600 text-white"
                    : "bg-slate-700 text-slate-300 hover:bg-slate-600"
                }`}
              >
                {b}
              </button>
            ))}
          </div>
        </div>

        {error && <p className="text-red-400 text-sm">{error}</p>}

        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white font-semibold py-3 rounded-lg transition-colors"
        >
          {loading ? "Agent searching..." : "Search Jobs with AI Agent"}
        </button>
      </form>

      {streamingUrl && (
        <div className="mt-6">
          <h2 className="text-sm font-medium text-slate-400 mb-2">Live agent view</h2>
          <iframe
            src={streamingUrl}
            className="w-full h-96 rounded-xl border border-slate-600"
            title="TinyFish live agent browser"
          />
        </div>
      )}

      <div className="mt-8 grid grid-cols-3 gap-4 text-center">
        {[
          { icon: "🔍", label: "AI-powered search", desc: "Scrapes real job boards" },
          { icon: "📝", label: "Auto-apply", desc: "Fills forms autonomously" },
          { icon: "📡", label: "Live stream", desc: "Watch the agent work" },
        ].map((f) => (
          <div key={f.label} className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
            <div className="text-2xl mb-1">{f.icon}</div>
            <div className="font-medium text-sm text-slate-200">{f.label}</div>
            <div className="text-xs text-slate-400 mt-0.5">{f.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
