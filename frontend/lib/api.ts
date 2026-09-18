export type BackendHealth = {
  status: string;
  service: string;
  version: string;
  environment: string;
  database?: {
    status: string;
    name: string;
  };
  ai?: {
    provider: string;
    configured: boolean;
    model: string;
  };
  auth?: {
    status: string;
  };
};

export type WorkspaceDocument = {
  id: string;
  name: string;
  type: string;
  status: string;
  owner: string;
  date: string;
  size_bytes: number;
  excerpt?: string;
  row_count?: number;
  columns?: string[];
  metrics?: { revenue: number; expenses: number; profit: number };
  series?: Array<{ month: string; revenue: number; expense: number; profit: number }>;
  categories?: Array<{ category: string; sales: number }>;
  locations?: Array<{ name: string; revenue: number; expense: number; profit: number }>;
  alerts?: Array<{ label: string; status: string }>;
  analysis?: {
    summary: string;
    key_insights: string[];
    recommendations: string[];
    provider: string;
    model: string;
  };
};

export type WorkspaceAnalytics = {
  kpis: {
    revenue: number;
    expenses: number;
    profit: number;
    margin: number;
    revenue_delta: string;
    revenue_trend: "up" | "down";
    expense_delta: string;
    expense_trend: "up" | "down";
    profit_delta: string;
    profit_trend: "up" | "down";
    margin_delta: string;
    margin_trend: "up" | "down";
  };
  summary: {
    documents_analyzed: number;
    alerts_tracked: number;
    system_health: string;
    ai_signal: string;
  };
  series: Array<{ month: string; revenue: number; expense: number; profit: number }>;
  categories: Array<{ category: string; sales: number }>;
  locations: Array<{ name: string; revenue: number; expense: number; profit: number }>;
  insights: Array<{ title: string; detail: string; tone: string }>;
  alerts: Array<{ label: string; status: string }>;
  reports: Array<{ title: string; description: string; value: string; accent: string }>;
  headline_insights: string[];
};

async function readError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.trim()) {
      return payload.detail;
    }
    if (Array.isArray(payload.detail)) {
      const parts = payload.detail
        .map((item) => {
          if (typeof item === "string") {
            return item;
          }
          if (item && typeof item === "object" && "msg" in item) {
            return String((item as { msg: string }).msg);
          }
          return "";
        })
        .filter(Boolean);
      if (parts.length) {
        return parts.join("; ");
      }
    }
  } catch {
    // Fall through to status text.
  }
  return response.statusText;
}

async function request(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  let lastError: unknown;
  for (const delay of [0, 500, 1000]) {
    if (delay) {
      await new Promise((resolve) => window.setTimeout(resolve, delay));
    }
    try {
      return await fetch(input, init);
    } catch (error) {
      lastError = error;
    }
  }

  if (lastError instanceof TypeError) {
    throw new Error("Cannot reach the Inferra backend. Start FastAPI on port 8000 and try Analyze again.");
  }
  throw lastError;
}

export async function getBackendHealth(): Promise<BackendHealth> {
  const response = await request("/api/health", {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Backend health request failed with status ${response.status}`);
  }

  return response.json() as Promise<BackendHealth>;
}

export async function listDocuments(query = ""): Promise<WorkspaceDocument[]> {
  const params = query.trim() ? `?q=${encodeURIComponent(query.trim())}` : "";
  const response = await request(`/api/documents${params}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  const payload = (await response.json()) as { items: WorkspaceDocument[] };
  return payload.items;
}

export async function uploadDocument(file: File): Promise<WorkspaceDocument> {
  const body = new FormData();
  body.append("file", file);
  const response = await request("/api/documents", {
    method: "POST",
    body,
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  const payload = (await response.json()) as { success?: boolean; document?: WorkspaceDocument; error?: string };
  if (!payload.success || !payload.document) {
    throw new Error(payload.error || "The backend did not return an analysis result.");
  }
  return payload.document;
}

export async function deleteDocument(id: string): Promise<void> {
  const response = await request(`/api/documents/${id}`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
}

export async function getAnalytics(): Promise<WorkspaceAnalytics> {
  const response = await request("/api/analytics", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return response.json() as Promise<WorkspaceAnalytics>;
}

export async function sendAgentMessage(
  message: string,
  history: Array<{ role: string; content: string }>,
): Promise<{ content: string; model: string; documents_used: number }> {
  const response = await request("/api/agent/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return response.json() as Promise<{ content: string; model: string; documents_used: number }>;
}

export function formatBytes(size: number): string {
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatMoney(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: value >= 1000 ? 0 : 2,
  }).format(value);
}
