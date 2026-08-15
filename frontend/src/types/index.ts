export interface User {
  id: string;
  email: string;
  role: string;
  business_id: string;
  created_at: string;
}

export interface Business {
  id: string;
  name: string;
  currency: string;
  country: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Transaction {
  id: string;
  txn_date: string;
  description: string | null;
  amount: string;
  currency: string;
  counterparty: string | null;
  ai_category: string | null;
  status: string;
  source: string;
}

export interface JournalEntry {
  id: string;
  entry_date: string;
  memo: string | null;
  is_draft: boolean;
  created_by: string;
  created_at: string;
  lines?: JournalLine[];
}

export interface JournalLine {
  id: string;
  account_id: string;
  debit: string;
  credit: string;
  account_code?: string;
  account_name?: string;
}

export interface AccountBalance {
  account_id: string;
  account_code: string;
  account_name: string;
  account_type: string;
  balance: string;
}

export interface PnLData {
  period_start: string;
  period_end: string;
  currency: string;
  revenue: AccountBalance[];
  total_revenue: string;
  expenses: AccountBalance[];
  total_expenses: string;
  net_income: string;
}

export interface BalanceSheetData {
  as_of_date: string;
  currency: string;
  assets: AccountBalance[];
  total_assets: string;
  liabilities: AccountBalance[];
  total_liabilities: string;
  equity: AccountBalance[];
  total_equity: string;
}

export interface DashboardSummary {
  currency: string;
  period_label: string;
  total_revenue: string;
  total_expenses: string;
  net_income: string;
  cash_balance: string;
  accounts_receivable: string;
  accounts_payable: string;
  transaction_count: number;
  pending_invoices: number;
  overdue_invoices: number;
  active_alerts: number;
}

export interface Alert {
  id: string;
  severity: string;
  title: string;
  detail: string;
  created_at: string;
  acknowledged: boolean;
}

export interface Document {
  id: string;
  file_type: string;
  original_filename: string;
  parse_status: string;
  uploaded_at: string;
  file_size?: number;
  analysis_result?: Record<string, unknown>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface Invoice {
  id: string;
  invoice_number: string;
  customer_name: string;
  customer_email: string;
  issue_date: string;
  due_date: string;
  status: 'draft' | 'sent' | 'paid' | 'overdue' | 'cancelled';
  subtotal: string;
  tax_amount: string;
  total_amount: string;
  currency: string;
  notes: string | null;
  items: InvoiceItem[];
  payments: Payment[];
}

export interface InvoiceItem {
  id: string;
  description: string;
  quantity: number;
  unit_price: string;
  amount: string;
}

export interface Payment {
  id: string;
  payment_date: string;
  amount: string;
  method: string;
  reference: string | null;
}

export interface Expense {
  id: string;
  expense_date: string;
  description: string;
  amount: string;
  currency: string;
  category: string;
  vendor: string | null;
  receipt_url: string | null;
  status: 'pending' | 'approved' | 'rejected';
  notes: string | null;
}

export interface ExpenseCategory {
  category: string;
  total: string;
  count: number;
}

export type PipelineStep = 'ingestion' | 'extraction' | 'normalization' | 'validation' | 'reconciliation' | 'metrics';

export interface PipelineState {
  currentStep: PipelineStep;
  steps: {
    name: PipelineStep;
    label: string;
    status: 'pending' | 'processing' | 'completed' | 'error';
    message?: string;
  }[];
}

// ─── Health Score ────────────────────────────────────────────────────────────

export interface HealthScoreBreakdown {
  category: string;
  score: number;
  max_score: number;
  detail: string;
}

export interface HealthScoreData {
  overall_score: number;
  cash_health: number;
  revenue_trend: number;
  expense_control: number;
  receivables: number;
  recommendation: string;
  // Optional enriched fields (may come from a more advanced endpoint)
  breakdown?: HealthScoreBreakdown[];
  trend?: 'improving' | 'stable' | 'declining';
  previous_score?: number;
}

// ─── AI CFO ──────────────────────────────────────────────────────────────────

export interface ChatMessageData {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  structured?: StructuredResponse;
  is_streaming?: boolean;
}

export interface StructuredResponse {
  summary: string;
  metrics?: ResponseMetric[];
  recommendations?: ResponseRecommendation[];
  risks?: ResponseRisk[];
  evidence?: ResponseEvidence[];
}

export interface ResponseMetric {
  label: string;
  value: string;
  change?: string;
  trend?: 'up' | 'down' | 'flat';
}

export interface ResponseRecommendation {
  title: string;
  description: string;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  evidence_id?: string;
}

export interface ResponseRisk {
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  category: string;
  title: string;
  description: string;
  recommendation: string;
}

export interface ResponseEvidence {
  id: string;
  source: string;
  data: Record<string, unknown>;
  relevance: string;
}

export interface SuggestedQuestion {
  id: string;
  text: string;
  text_sw?: string;
  category: string;
}

// ─── Revenue/Expense Chart ───────────────────────────────────────────────────

export interface MonthlyFinancials {
  month: string;
  revenue: number;
  expenses: number;
  net: number;
}
