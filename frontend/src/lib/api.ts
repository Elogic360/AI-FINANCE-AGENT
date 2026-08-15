import axios from 'axios';
import type {
  DashboardSummary,
  Alert,
  Transaction,
  HealthScoreData,
  MonthlyFinancials,
  ChatMessageData,
  SuggestedQuestion,
  PnLData,
  BalanceSheetData,
} from '../types';

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
});

/**
 * Safely extract a human-readable error message from an Axios error.
 *
 * FastAPI / Pydantic v2 validation errors come back as:
 *   { detail: [ { type, loc, msg, input, url }, ... ] }
 * Other HTTP errors use:
 *   { detail: "string message" }
 *
 * This helper normalises every shape into a plain string so callers
 * never accidentally render an object as a React child.
 */
export function extractErrorMessage(err: unknown, fallback = 'An unexpected error occurred'): string {
  // Guard: make sure we have something shaped like an Axios error
  const axiosErr = err as any;
  const detail = axiosErr?.response?.data?.detail;

  // 1. detail is a plain string  (most HTTPException cases)
  if (typeof detail === 'string') return detail;

  // 2. detail is an array  (Pydantic v2 422 validation errors)
  if (Array.isArray(detail)) {
    return detail
      .map((d: any) => {
        if (typeof d === 'string') return d;
        if (d && typeof d === 'object' && typeof d.msg === 'string') return d.msg;
        return String(d);
      })
      .filter(Boolean)
      .join('. ');
  }

  // 3. detail is a single object  (rare, but possible)
  if (detail && typeof detail === 'object') {
    if (typeof detail.msg === 'string') return detail.msg;
    if (typeof detail.message === 'string') return detail.message;
    try { return JSON.stringify(detail); } catch { return String(detail); }
  }

  // 4. No detail – try the generic message field
  const msg = axiosErr?.response?.data?.message;
  if (typeof msg === 'string') return msg;

  // 5. Network / timeout errors (no response)
  if (axiosErr?.message && typeof axiosErr.message === 'string') return axiosErr.message;

  return fallback;
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('finpilot_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('finpilot_token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

// ─── Dashboard ──────────────────────────────────────────────────────────────

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  const res = await api.get('/dashboard/summary');
  return res.data;
}

export async function fetchHealthScore(): Promise<HealthScoreData> {
  const res = await api.get('/dashboard/health-score');
  return res.data;
}

export async function fetchMonthlyFinancials(): Promise<MonthlyFinancials[]> {
  const res = await api.get('/dashboard/monthly-financials');
  return res.data;
}

export async function fetchRecentTransactions(limit = 10): Promise<Transaction[]> {
  const res = await api.get('/transactions', { params: { page_size: limit, page: 1 } });
  return res.data.items ?? res.data;
}

export async function fetchAlerts(): Promise<Alert[]> {
  const res = await api.get('/alerts', { params: { page: 1, page_size: 10 } });
  // Backend returns PaginatedResponse — extract the items array
  return res.data.items ?? res.data;
}

// ─── AI CFO ─────────────────────────────────────────────────────────────────

export async function fetchSuggestedQuestions(): Promise<SuggestedQuestion[]> {
  const res = await api.get('/ai-cfo/suggested-questions');
  return res.data;
}

export async function sendChatMessage(message: string): Promise<ChatMessageData> {
  const res = await api.post('/ai-cfo/chat', { message });
  return res.data;
}

/**
 * Stream an AI CFO response via SSE. Calls `onChunk` for each text chunk
 * and `onComplete` with the full structured response when done.
 */
export function streamChatMessage(
  message: string,
  onChunk: (chunk: string) => void,
  onComplete: (response: ChatMessageData) => void,
  onError: (err: Error) => void,
): () => void {
  const token = localStorage.getItem('finpilot_token');
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch('/api/v1/ai-cfo/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ message }),
        signal: controller.signal,
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      if (!res.body) throw new Error('No response body');

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let fullText = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value, { stream: true });
        const lines = text.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const payload = line.slice(6).trim();
            if (payload === '[DONE]') continue;
            try {
              const parsed = JSON.parse(payload);
              if (parsed.chunk) {
                fullText += parsed.chunk;
                onChunk(parsed.chunk);
              }
              if (parsed.done) {
                onComplete(parsed.response ?? {
                  id: crypto.randomUUID(),
                  role: 'assistant' as const,
                  content: fullText,
                  timestamp: new Date().toISOString(),
                });
                return;
              }
            } catch {
              // plain text chunk
              fullText += payload;
              onChunk(payload);
            }
          }
        }
      }

      onComplete({
        id: crypto.randomUUID(),
        role: 'assistant' as const,
        content: fullText,
        timestamp: new Date().toISOString(),
      });
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        onError(err as Error);
      }
    }
  })();

  return () => controller.abort();
}

// ─── Reports ────────────────────────────────────────────────────────────────

export async function fetchPnL(startDate?: string, endDate?: string): Promise<PnLData> {
  const today = new Date().toISOString().split('T')[0];
  const params: Record<string, string> = {
    start_date: startDate || `${new Date().getFullYear()}-01-01`,
    end_date: endDate || today,
  };
  const res = await api.get('/reports/pnl', { params });
  return res.data;
}

export async function fetchBalanceSheet(asOfDate?: string): Promise<BalanceSheetData> {
  const today = asOfDate || new Date().toISOString().split('T')[0];
  const res = await api.get('/reports/balance-sheet', { params: { as_of_date: today } });
  return res.data;
}

export default api;
