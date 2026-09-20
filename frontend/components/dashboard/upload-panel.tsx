"use client";

import { useRef, useState } from "react";
import { FileUp, UploadCloud, X } from "lucide-react";

import { useDashboardData } from "@/components/dashboard/dashboard-data-provider";
import { type WorkspaceDocument, formatBytes, formatMoney } from "@/lib/api";

export function UploadPanel() {
  const inputRef = useRef<HTMLInputElement>(null);
  const { documents, uploadFiles, removeDocument, loading } = useDashboardData();
  const [dragActive, setDragActive] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [hasError, setHasError] = useState(false);
  const [latestDocument, setLatestDocument] = useState<WorkspaceDocument | null>(null);

  async function handleFiles(files: FileList | File[] | null) {
    if (busy || !files || files.length === 0) {
      return;
    }
    const selectedFiles = Array.from(files);
    setBusy(true);
    setMessage(null);
    setHasError(false);
    setLatestDocument(null);
    try {
      const uploaded = await uploadFiles(selectedFiles);
      setLatestDocument(uploaded.at(-1) ?? null);
      setMessage(`${selectedFiles.length} file(s) uploaded and analyzed`);
    } catch (error) {
      setHasError(true);
      setMessage(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="glass-card rounded-[28px] p-5 sm:p-6">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div>
          <p className="text-sm text-slate-300">Documents</p>
          <h3 className="text-xl font-semibold text-white">Upload & process</h3>
        </div>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={busy}
          className="glass-button rounded-2xl px-4 py-2 text-sm font-medium text-slate-100 disabled:opacity-60"
        >
          Browse files
        </button>
      </div>

      <input
        ref={inputRef}
        type="file"
        className="hidden"
        multiple
        accept=".pdf,.xlsx,.csv,.docx,.txt,.json"
        onChange={(event) => {
          void handleFiles(event.target.files);
          event.target.value = "";
        }}
      />

      <div
        onDragOver={(event) => {
          event.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragActive(false);
          void handleFiles(event.dataTransfer.files);
        }}
        className={`rounded-[24px] border border-dashed p-6 text-center ${
          dragActive ? "border-emerald-300 bg-emerald-500/10" : "border-emerald-400/30 bg-emerald-500/5"
        }`}
      >
        <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/10 text-emerald-300 ring-1 ring-emerald-400/20">
          <UploadCloud className="h-6 w-6" />
        </div>
        <p className="text-base font-medium text-white">Drag and drop business files</p>
        <p className="mt-2 text-sm text-slate-300">PDF, Excel, CSV, DOCX, TXT, JSON</p>
        <p className="mt-2 text-xs text-slate-400">{busy ? "Uploading, reading, and analyzing data..." : loading ? "Loading workspace..." : "Files are parsed and analyzed by the backend"}</p>
      </div>

      {message ? <p className={`mt-3 text-sm ${hasError ? "text-red-300" : "text-emerald-200"}`}>{message}</p> : null}

      {latestDocument ? (
        <div className="mt-5 rounded-2xl border border-violet-400/20 bg-violet-500/5 p-4">
          <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.16em] text-violet-200">Latest file analysis</p>
              <h4 className="mt-1 text-base font-semibold text-white">{latestDocument.name}</h4>
            </div>
            <span className="text-xs text-emerald-200">{latestDocument.status}</span>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
            <div className="rounded-xl border border-white/10 bg-white/[0.04] p-2">
              <p className="text-[11px] text-slate-400">Type</p>
              <p className="mt-1 text-sm font-medium text-white">{latestDocument.type}</p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.04] p-2">
              <p className="text-[11px] text-slate-400">Rows</p>
              <p className="mt-1 text-sm font-medium text-white">{latestDocument.row_count ?? 0}</p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.04] p-2">
              <p className="text-[11px] text-slate-400">Revenue</p>
              <p className="mt-1 text-sm font-medium text-white">{formatMoney(latestDocument.metrics?.revenue ?? 0)}</p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.04] p-2">
              <p className="text-[11px] text-slate-400">Profit</p>
              <p className="mt-1 text-sm font-medium text-white">{formatMoney(latestDocument.metrics?.profit ?? 0)}</p>
            </div>
          </div>

          <p className="mt-4 text-sm leading-6 text-slate-200">
            {latestDocument.analysis?.summary || "The backend extracted the file, but did not return an AI summary."}
          </p>
          {latestDocument.analysis?.key_insights.length ? (
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-300">
              {latestDocument.analysis.key_insights.map((insight) => <li key={insight}>{insight}</li>)}
            </ul>
          ) : null}
          <p className="mt-3 text-xs text-slate-400">
            Columns: {latestDocument.columns?.join(", ") || "No tabular columns detected"}
          </p>
        </div>
      ) : null}

      <div className="mt-5 space-y-3">
        {documents.length === 0 ? (
          <p className="rounded-2xl border border-white/10 bg-white/[0.03] px-3 py-4 text-sm text-slate-400">
            No files imported yet.
          </p>
        ) : (
          documents.map((file) => (
            <div
              key={file.id}
              className="flex items-center justify-between gap-3 rounded-2xl border border-white/10 bg-white/[0.03] px-3 py-3"
            >
              <div className="flex min-w-0 items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-800/80 text-slate-200 ring-1 ring-white/10">
                  <FileUp className="h-4 w-4" />
                </div>
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-white">{file.name}</p>
                  <p className="text-xs text-slate-400">{formatBytes(file.size_bytes)}</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span
                  className={`rounded-full px-2 py-1 text-[10px] font-medium ${
                    file.status === "Analyzed" || file.status === "Ready" || file.status === "Processed"
                      ? "bg-emerald-500/10 text-emerald-200"
                      : file.status === "Processing"
                        ? "bg-amber-500/10 text-amber-200"
                        : "bg-sky-500/10 text-sky-200"
                  }`}
                >
                  {file.status}
                </span>
                <button
                  type="button"
                  onClick={() => void removeDocument(file.id)}
                  className="rounded-full p-1.5 text-slate-400 transition hover:bg-white/5 hover:text-slate-200"
                  aria-label={`Remove ${file.name}`}
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
