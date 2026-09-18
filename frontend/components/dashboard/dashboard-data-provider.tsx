"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import {
  type BackendHealth,
  type WorkspaceAnalytics,
  type WorkspaceDocument,
  deleteDocument,
  getAnalytics,
  getBackendHealth,
  listDocuments,
  uploadDocument,
} from "@/lib/api";

type DashboardData = {
  health: BackendHealth | null;
  backendStatus: "checking" | "connected" | "offline";
  documents: WorkspaceDocument[];
  analytics: WorkspaceAnalytics | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  uploadFiles: (files: FileList | File[]) => Promise<WorkspaceDocument[]>;
  removeDocument: (id: string) => Promise<void>;
  searchDocuments: (query: string) => Promise<void>;
};

const DashboardDataContext = createContext<DashboardData | null>(null);

const emptyAnalytics = (): WorkspaceAnalytics => ({
  kpis: {
    revenue: 0,
    expenses: 0,
    profit: 0,
    margin: 0,
    revenue_delta: "0.0%",
    revenue_trend: "up",
    expense_delta: "0.0%",
    expense_trend: "down",
    profit_delta: "0.0%",
    profit_trend: "up",
    margin_delta: "0.0%",
    margin_trend: "up",
  },
  summary: {
    documents_analyzed: 0,
    alerts_tracked: 0,
    system_health: "Waiting",
    ai_signal: "Idle",
  },
  series: [],
  categories: [],
  locations: [],
  insights: [],
  alerts: [],
  reports: [],
  headline_insights: [],
});

export function DashboardDataProvider({ children }: { children: React.ReactNode }) {
  const [health, setHealth] = useState<BackendHealth | null>(null);
  const [backendStatus, setBackendStatus] = useState<DashboardData["backendStatus"]>("checking");
  const [documents, setDocuments] = useState<WorkspaceDocument[]>([]);
  const [analytics, setAnalytics] = useState<WorkspaceAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    const [healthResult, documentsResult, analyticsResult] = await Promise.allSettled([
      getBackendHealth(),
      listDocuments(),
      getAnalytics(),
    ]);
    const failures = [healthResult, documentsResult, analyticsResult].filter(
      (result): result is PromiseRejectedResult => result.status === "rejected",
    );
    if (healthResult.status === "fulfilled") setHealth(healthResult.value);
    if (documentsResult.status === "fulfilled") setDocuments(documentsResult.value);
    if (analyticsResult.status === "fulfilled") setAnalytics(analyticsResult.value);
    setBackendStatus(failures.length === 3 ? "offline" : "connected");
    setError(failures.length ? String(failures[0].reason?.message ?? "Some workspace data could not be loaded") : null);
    setLoading(false);
  }, []);

  useEffect(() => {
    const refreshTimer = window.setTimeout(() => {
      void refresh();
    }, 0);
    return () => window.clearTimeout(refreshTimer);
  }, [refresh]);

  const uploadFiles = useCallback(
    async (files: FileList | File[]) => {
      const selected = Array.from(files);
      const uploaded: WorkspaceDocument[] = [];
      for (const file of selected) {
        uploaded.push(await uploadDocument(file));
      }
      await refresh();
      return uploaded;
    },
    [refresh],
  );

  const removeDocument = useCallback(
    async (id: string) => {
      await deleteDocument(id);
      await refresh();
    },
    [refresh],
  );

  const searchDocuments = useCallback(async (query: string) => {
    const items = await listDocuments(query);
    setDocuments(items);
  }, []);

  const value = useMemo(
    () => ({
      health,
      backendStatus,
      documents,
      analytics: analytics ?? emptyAnalytics(),
      loading,
      error,
      refresh,
      uploadFiles,
      removeDocument,
      searchDocuments,
    }),
    [analytics, backendStatus, documents, error, health, loading, refresh, removeDocument, searchDocuments, uploadFiles],
  );

  return <DashboardDataContext.Provider value={value}>{children}</DashboardDataContext.Provider>;
}

export function useDashboardData() {
  const context = useContext(DashboardDataContext);
  if (!context) {
    throw new Error("useDashboardData must be used inside DashboardDataProvider");
  }
  return context;
}
