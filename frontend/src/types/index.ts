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
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}
