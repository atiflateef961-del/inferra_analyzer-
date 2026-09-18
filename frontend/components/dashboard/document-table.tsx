"use client";

import { useMemo, useState } from "react";
import { ArrowUpRight, FileText, Search, X } from "lucide-react";

import { useDashboardData } from "@/components/dashboard/dashboard-data-provider";

export function DocumentTable() {
  const { documents, searchDocuments, loading } = useDashboardData();
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selected = useMemo(
    () => documents.find((item) => item.id === selectedId) ?? null,
    [documents, selectedId],
  );

  return (
    <div className="glass-card rounded-[28px] p-5 sm:p-6">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm text-slate-300">Documents</p>
          <h3 className="text-xl font-semibold text-white">Document management</h3>
        </div>

        <div className="flex items-center gap-2 rounded-2xl border border-white/10 bg-white/[0.03] px-3 py-2">
          <Search className="h-4 w-4 text-slate-400" />
          <input
            aria-label="Search documents"
            placeholder="Search files"
            value={query}
            onChange={(event) => {
              const value = event.target.value;
              setQuery(value);
              void searchDocuments(value);
            }}
            className="w-40 bg-transparent text-sm text-white placeholder:text-slate-500 focus:outline-none"
          />
        </div>
      </div>

      <div className="overflow-hidden">
        <table className="w-full table-fixed text-left text-sm">
          <thead>
            <tr className="border-b border-white/10 text-slate-400">
              <th className="w-[34%] pb-3 font-medium">Name</th>
              <th className="w-[12%] pb-3 font-medium">Type</th>
              <th className="w-[18%] pb-3 font-medium">Status</th>
              <th className="hidden w-[18%] pb-3 font-medium sm:table-cell">Owner</th>
              <th className="hidden w-[10%] pb-3 font-medium md:table-cell">Date</th>
              <th className="w-[18%] pb-3 font-medium text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {documents.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-6 text-slate-400">
                  {loading ? "Loading documents..." : "No documents match this workspace yet."}
                </td>
              </tr>
            ) : (
              documents.map((item) => (
                <tr key={item.id} className="border-b border-white/5 text-slate-200 last:border-none">
                  <td className="py-3 pr-4">
                    <div className="flex items-center gap-3">
                      <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-800/80 text-slate-200 ring-1 ring-white/10">
                        <FileText className="h-4 w-4" />
                      </div>
                      <span className="block truncate font-medium text-white">{item.name}</span>
                    </div>
                  </td>
                  <td className="py-3 pr-4 text-slate-300">{item.type}</td>
                  <td className="py-3 pr-4">
                    <span
                      className={`rounded-full px-2.5 py-1 text-[10px] font-medium ${
                        item.status === "Processed" || item.status === "Analyzed"
                          ? "bg-emerald-500/10 text-emerald-200"
                          : item.status === "Processing"
                            ? "bg-amber-500/10 text-amber-200"
                            : "bg-sky-500/10 text-sky-200"
                      }`}
                    >
                      {item.status}
                    </span>
                  </td>
                  <td className="hidden truncate py-3 pr-4 text-slate-300 sm:table-cell"><span className="block truncate">{item.owner}</span></td>
                  <td className="hidden py-3 pr-4 text-slate-300 md:table-cell">{item.date}</td>
                  <td className="py-3 text-right">
                    <button
                      type="button"
                      onClick={() => setSelectedId(item.id)}
                      className="inline-flex max-w-full items-center gap-1 rounded-xl border border-white/10 bg-white/5 px-1.5 py-1.5 text-xs font-medium text-slate-200 hover:bg-white/10 sm:gap-2 sm:px-2.5"
                    >
                      Open
                      <ArrowUpRight className="h-3.5 w-3.5" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-4 text-xs text-slate-400">
        Showing {documents.length} file{documents.length === 1 ? "" : "s"}
      </div>

      {selected ? (
        <div className="mt-4 flex items-center justify-between rounded-2xl border border-emerald-400/20 bg-emerald-500/5 p-3">
          <div>
            <p className="text-sm font-medium text-white">Selected file</p>
            <p className="text-xs text-slate-400">{selected.name}</p>
          </div>
          <button
            type="button"
            onClick={() => setSelectedId(selected.id)}
            className="inline-flex items-center gap-2 rounded-xl bg-emerald-400 px-3 py-2 text-xs font-semibold text-slate-950 hover:bg-emerald-300"
          >
            View extracted data
            <ArrowUpRight className="h-3.5 w-3.5" />
          </button>
        </div>
      ) : null}

      {selected ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label={`${selected.name} extracted data`}>
          <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-[28px] border border-white/10 bg-slate-900 p-5 shadow-2xl sm:p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-emerald-300">Extracted document</p>
                <h3 className="mt-1 text-xl font-semibold text-white">{selected.name}</h3>
                <p className="mt-1 text-xs text-slate-400">{selected.type} · {selected.row_count ?? 0} rows · {selected.status}</p>
              </div>
              <button type="button" onClick={() => setSelectedId(null)} className="rounded-xl p-2 text-slate-400 hover:bg-white/10 hover:text-white" aria-label="Close document details">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              {[
                ["Revenue", selected.metrics?.revenue ?? 0],
                ["Expenses", selected.metrics?.expenses ?? 0],
                ["Profit", selected.metrics?.profit ?? 0],
              ].map(([label, value]) => (
                <div key={String(label)} className="rounded-2xl border border-white/10 bg-white/[0.04] p-3">
                  <p className="text-xs text-slate-400">{label}</p>
                  <p className="mt-1 text-lg font-semibold text-white">${Number(value).toLocaleString()}</p>
                </div>
              ))}
            </div>

            {selected.series?.length ? (
              <div className="mt-5 overflow-x-auto rounded-2xl border border-white/10">
                <table className="min-w-full text-left text-xs">
                  <thead className="bg-white/[0.04] text-slate-400"><tr><th className="px-3 py-2">Period</th><th className="px-3 py-2">Revenue</th><th className="px-3 py-2">Expense</th><th className="px-3 py-2">Profit</th></tr></thead>
                  <tbody>{selected.series.map((point) => <tr key={point.month} className="border-t border-white/5 text-slate-200"><td className="px-3 py-2">{point.month}</td><td className="px-3 py-2">${point.revenue.toLocaleString()}</td><td className="px-3 py-2">${point.expense.toLocaleString()}</td><td className="px-3 py-2">${point.profit.toLocaleString()}</td></tr>)}</tbody>
                </table>
              </div>
            ) : null}

            <div className="mt-5 rounded-2xl border border-white/10 bg-slate-950/50 p-4">
              <p className="text-xs font-medium uppercase tracking-[0.16em] text-slate-400">Extracted content</p>
              <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap break-words font-sans text-xs leading-5 text-slate-200">{selected.excerpt || "No readable text was extracted from this file."}</pre>
            </div>

            {selected.analysis ? (
              <div className="mt-5 rounded-2xl border border-violet-400/20 bg-violet-500/5 p-4">
                <p className="text-xs font-medium uppercase tracking-[0.16em] text-violet-200">AI analysis</p>
                <p className="mt-3 text-sm leading-6 text-slate-200">{selected.analysis.summary}</p>
                {selected.analysis.key_insights.length ? <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-300">{selected.analysis.key_insights.map((insight) => <li key={insight}>{insight}</li>)}</ul> : null}
                {selected.analysis.recommendations.length ? <div className="mt-4"><p className="text-xs font-medium text-violet-200">Recommendations</p><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-300">{selected.analysis.recommendations.map((item) => <li key={item}>{item}</li>)}</ul></div> : null}
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
