"use client";
import { useState } from "react";
import useSWR from "swr";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const fetcher = (url: string) => fetch(url).then((r) => r.json());

interface Job {
  id: string;
  title: string;
  company: string;
  location: string;
  apply_url: string;
  board: string;
}

interface ResumeData {
  name: string;
  email: string;
  phone: string;
}

export default function JobsPage() {
  const { data: jobs, isLoading, error } = useSWR<Job[]>(`${API}/api/jobs`, fetcher, { refreshInterval: 5000 });
  const [applying, setApplying] = useState<string | null>(null);
  const [streamingUrl, setStreamingUrl] = useState<string | null>(null);
  const [resume] = useState<ResumeData>({ name: "Jane Doe", email: "jane@example.com", phone: "555-0100" });
  const [appliedJobs, setAppliedJobs] = useState<Set<string>>(new Set());

  const handleApply = async (job: Job) => {
    setApplying(job.id);
    setStreamingUrl(null);
    try {
      const res = await fetch(`${API}/api/apply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: job.id, job_url: job.apply_url, resume_data: resume }),
      });
      const data = await res.json();
      if (data.streaming_url) setStreamingUrl(data.streaming_url);
      setAppliedJobs((prev) => new Set([...prev, job.id]));
    } catch {
      alert("Apply failed — check backend connection");
    } finally {
      setApplying(null);
    }
  };

  if (isLoading) return (
    <div className="text-center py-20 text-slate-400">
      <div className="text-4xl mb-4">🐟</div>
      <p>Loading jobs...</p>
    </div>
  );

  if (error) return (
    <div className="text-center py-20 text-red-400">
      <p>Failed to load jobs. Is the backend running?</p>
      <a href="/" className="text-blue-400 underline mt-2 inline-block">Run a search first</a>
    </div>
  );

  if (!jobs?.length) return (
    <div className="text-center py-20 text-slate-400">
      <div className="text-4xl mb-4">🔍</div>
      <p>No jobs found yet.</p>
      <a href="/" className="text-blue-400 underline mt-2 inline-block">Search for jobs</a>
    </div>
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">Job Results <span className="text-slate-400 text-lg font-normal">({jobs.length})</span></h1>
        <a href="/" className="text-sm text-blue-400 hover:text-blue-300">New search</a>
      </div>

      {streamingUrl && (
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-2">
            <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            <span className="text-sm text-green-400 font-medium">Agent applying — live view</span>
          </div>
          <iframe src={streamingUrl} className="w-full h-96 rounded-xl border border-green-700/50" title="Live agent browser" />
        </div>
      )}

      <div className="space-y-3">
        {jobs.map((job) => (
          <div key={job.id} className="bg-slate-800 border border-slate-700 rounded-xl p-4 flex items-center justify-between gap-4">
            <div className="flex-1 min-w-0">
              <h2 className="font-semibold text-white truncate">{job.title}</h2>
              <p className="text-slate-400 text-sm">{job.company} · {job.location}</p>
              <span className="inline-block mt-1 text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full">{job.board}</span>
            </div>
            <div className="flex gap-2 flex-shrink-0">
              <a
                href={job.apply_url}
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-1.5 text-sm border border-slate-600 text-slate-300 rounded-lg hover:bg-slate-700 transition-colors"
              >
                View
              </a>
              <button
                onClick={() => handleApply(job)}
                disabled={applying === job.id || appliedJobs.has(job.id)}
                className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  appliedJobs.has(job.id)
                    ? "bg-green-700 text-green-200 cursor-default"
                    : applying === job.id
                    ? "bg-slate-600 text-slate-300 cursor-wait"
                    : "bg-blue-600 hover:bg-blue-700 text-white"
                }`}
              >
                {appliedJobs.has(job.id) ? "Applied" : applying === job.id ? "Applying..." : "Auto Apply"}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
