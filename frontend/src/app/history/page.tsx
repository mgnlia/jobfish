"use client";
import useSWR from "swr";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const fetcher = (url: string) => fetch(url).then((r) => r.json());

interface Application {
  id: string;
  job_id: string;
  status: string;
  streaming_url: string | null;
  created_at: string;
}

const STATUS_COLORS: Record<string, string> = {
  submitted: "bg-green-700 text-green-200",
  pending: "bg-yellow-700 text-yellow-200",
  failed: "bg-red-700 text-red-200",
};

export default function HistoryPage() {
  const { data: apps, isLoading } = useSWR<Application[]>(`${API}/api/applications`, fetcher, { refreshInterval: 10000 });

  if (isLoading) return <div className="text-center py-20 text-slate-400">Loading applications...</div>;

  if (!apps?.length) return (
    <div className="text-center py-20 text-slate-400">
      <div className="text-4xl mb-4">📋</div>
      <p>No applications yet.</p>
      <a href="/jobs" className="text-blue-400 underline mt-2 inline-block">Browse jobs</a>
    </div>
  );

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Application History <span className="text-slate-400 text-lg font-normal">({apps.length})</span></h1>
      <div className="space-y-3">
        {apps.map((app) => (
          <div key={app.id} className="bg-slate-800 border border-slate-700 rounded-xl p-4 flex items-center justify-between gap-4">
            <div>
              <p className="text-sm text-slate-300 font-mono">{app.id.slice(0, 8)}...</p>
              <p className="text-xs text-slate-500 mt-0.5">{new Date(app.created_at).toLocaleString()}</p>
            </div>
            <div className="flex items-center gap-3">
              {app.streaming_url && (
                <a href={app.streaming_url} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-400 hover:underline">
                  View replay
                </a>
              )}
              <span className={`text-xs font-medium px-2 py-1 rounded-full ${STATUS_COLORS[app.status] || "bg-slate-700 text-slate-300"}`}>
                {app.status}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
