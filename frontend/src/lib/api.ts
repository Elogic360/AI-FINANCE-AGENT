import axios, { AxiosError } from 'axios';
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

// ─── FastAPI / Pydantic v2 error types ───────────────────────────────────────

export interface FastApiValidationError {
  type: string;
  loc: (string | number)[];
  msg: string;
  input?: unknown;
  url?: string;
}

export interface FastApiErrorResponse {
  detail: string | FastApiValidationError[];
}

// ─── Axios instance ──────────────────────────────────────────────────────────

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
});

/**
 * Safely extract a human-readable error message from any error shape.
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
  // Guard: null / undefined
  if (err == null) return fallback;

  // Plain string error
  if (typeof err === 'string') return err || fallback;

  // Standard Error object (network errors, etc.)
  if (err instanceof Error && !isAxiosError(err)) {
    return err.message || fallback;
  }

  // Axios-shaped error — safely extract response data
  const axiosErr = err as AxiosError<FastApiErrorResponse>;
  const detail = axiosErr.response?.data?.detail;

  // 1. detail is a plain string  (most HTTPException cases)
  if (typeof detail === 'string') return detail;

  // 2. detail is an array  (Pydantic v2 422 validation errors)
  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        if (typeof d === 'string') return d;
        if (d != null && typeof d === 'object') {
          const rec = d as unknown as Record<string, unknown>;
          if (typeof rec.msg === 'string') {
            const loc = rec.loc as (string | number)[] | undefined;
            const field = loc && loc.length > 1 ? String(loc[loc.length - 1]) : '';
            return field ? `${field}: ${rec.msg}` : rec.msg;
          }
        }
        return String(d);
      })
      .filter(Boolean)
      .join('\n');
  }

  // 3. detail is a single object  (rare, but possible)
  if (detail != null && typeof detail === 'object' && !Array.isArray(detail)) {
    const d = detail as unknown as Record<string, unknown>;
    if (typeof d.msg === 'string') return d.msg;
    if (typeof d.message === 'string') return d.message;
    try { return JSON.stringify(detail); } catch { return String(detail); }
  }

  // 4. No detail – try the generic message field
  const data = axiosErr.response?.data as Record<string, unknown> | undefined;
  if (typeof data?.message === 'string') return data.message;

  // 5. Axios error message (network / timeout errors)
  if (typeof axiosErr.message === 'string') return axiosErr.message;

  // 6. Last resort
  try { return JSON.stringify(err); } catch { return fallback; }
}

function isAxiosError(err: unknown): err is AxiosError {
  return err != null && typeof err === 'object' && 'isAxiosError' in err;
}

/**
 * Extract per-field validation errors from a FastAPI 422 response.
 * Returns a map of field name → error message.
 */
export function extractFieldErrors(err: unknown): Record<string, string> {
  const axiosErr = err as AxiosError<FastApiErrorResponse> | undefined;
  const detail = axiosErr?.response?.data?.detail;

  if (!Array.isArray(detail)) return {};

  const fieldErrors: Record<string, string> = {};
  for (const d of detail) {
    if (d != null && typeof d === 'object') {
      const rec = d as unknown as Record<string, unknown>;
      if (typeof rec.msg === 'string') {
        const loc = rec.loc as (string | number)[] | undefined;
        const field = loc && loc.length > 1 ? String(loc[loc.length - 1]) : '';
        if (field) fieldErrors[field] = rec.msg;
      }
    }
  }
  return fieldErrors;
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
      // Avoid redirect loop: only navigate if not already on a public route
      const path = window.location.pathname;
      if (path !== '/login' && path !== '/register') {
        window.location.href = '/login';
      }
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
  const res = await api.post('/ai/suggest', {});
  const questions = res.data.questions ?? res.data;
  // Map backend format to frontend format
  return questions.map((q: string | SuggestedQuestion, i: number) => {
    if (typeof q === 'string') {
      return { id: String(i), text: q, category: 'general' };
    }
    return q;
  });
}

export async function sendChatMessage(message: string): Promise<ChatMessageData> {
  const res = await api.post('/ai/chat', { message });
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
      const res = await fetch('/api/v1/ai/chat', {
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
              const event = parsed.event ?? (parsed.done ? 'done' : parsed.chunk ? 'message' : undefined);
              const chunk = typeof parsed.data === 'string' ? parsed.data : parsed.chunk;

              if (event === 'message' && chunk) {
                fullText += chunk;
                onChunk(chunk);
              }

              if (event === 'done') {
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
