import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import ReportViewer from '../components/ReportViewer';
import { BarChart3, FileSpreadsheet, ArrowDownUp, Scale, Users, CreditCard, Calendar } from 'lucide-react';
import type { PnLData, BalanceSheetData } from '../types';

type ReportType = 'pnl' | 'balance-sheet' | 'cash-flow' | 'trial-balance' | 'ar-aging' | 'ap-aging';

const REPORT_TYPES: { key: ReportType; label: string; icon: typeof BarChart3; description: string }[] = [
  { key: 'pnl', label: 'Profit & Loss', icon: BarChart3, description: 'Revenue, expenses, and net income' },
  { key: 'balance-sheet', label: 'Balance Sheet', icon: Scale, description: 'Assets, liabilities, and equity' },
  { key: 'cash-flow', label: 'Cash Flow', icon: ArrowDownUp, description: 'Cash inflows and outflows' },
  { key: 'trial-balance', label: 'Trial Balance', icon: FileSpreadsheet, description: 'Debit and credit balances' },
  { key: 'ar-aging', label: 'AR Aging', icon: Users, description: 'Accounts receivable aging' },
  { key: 'ap-aging', label: 'AP Aging', icon: CreditCard, description: 'Accounts payable aging' },
];

function formatTZS(val: string | number): string {
  const num = typeof val === 'string' ? parseFloat(val) : val;
  return `TZS ${num.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

export default function ReportsPage() {
  const [reportType, setReportType] = useState<ReportType>('pnl');
  const [startDate, setStartDate] = useState('2026-01-01');
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
  const { data: pnl, isLoading: pnlLoading } = useQuery<PnLData>({
    queryKey: ['pnl', startDate, endDate],
    queryFn: () => api.get('/reports/pnl', { params: { start_date: startDate, end_date: endDate } }).then(r => r.data),
    enabled: reportType === 'pnl',
  });

  const { data: bs, isLoading: bsLoading } = useQuery<BalanceSheetData>({
    queryKey: ['bs', endDate],
    queryFn: () => api.get('/reports/balance-sheet', { params: { as_of_date: endDate } }).then(r => r.data),
    enabled: reportType === 'balance-sheet',
  });

  const { data: tb, isLoading: tbLoading } = useQuery({
    queryKey: ['tb', endDate],
    queryFn: () => api.get('/reports/trial-balance', { params: { as_of_date: endDate } }).then(r => r.data),
    enabled: reportType === 'trial-balance',
  });

  const { data: cf, isLoading: cfLoading } = useQuery({
    queryKey: ['cash-flow', startDate, endDate],
    queryFn: () => api.get('/reports/cash-flow', { params: { start_date: startDate, end_date: endDate } }).then(r => r.data),
    enabled: reportType === 'cash-flow',
  });

  const { data: arAging, isLoading: arLoading } = useQuery({
    queryKey: ['ar-aging', endDate],
    queryFn: () => api.get('/reports/ar-aging', { params: { as_of_date: endDate } }).then(r => r.data),
    enabled: reportType === 'ar-aging',
  });

  const { data: apAging, isLoading: apLoading } = useQuery({
    queryKey: ['ap-aging', endDate],
    queryFn: () => api.get('/reports/ap-aging', { params: { as_of_date: endDate } }).then(r => r.data),
    enabled: reportType === 'ap-aging',
  });

  const currentReport = REPORT_TYPES.find(r => r.key === reportType)!;

  const isLoading = pnlLoading || bsLoading || tbLoading || cfLoading || arLoading || apLoading;

  const getReportContent = () => {
    switch (reportType) {
      case 'pnl':
        if (!pnl) return null;
        return (
          <ReportViewer
            title="Profit & Loss Statement"
            subtitle={`${pnl.period_start} to ${pnl.period_end}`}
            currency={pnl.currency}
            onExport={() => alert('Export functionality coming soon')}
            sections={[
              {
                title: 'Summary',
                type: 'summary',
                summaryItems: [
                  { label: 'Total Revenue', value: formatTZS(pnl.total_revenue), color: 'text-green-400' },
                  { label: 'Total Expenses', value: formatTZS(pnl.total_expenses), color: 'text-red-400' },
                  { label: 'Net Income', value: formatTZS(pnl.net_income), color: parseFloat(pnl.net_income) >= 0 ? 'text-green-400' : 'text-red-400' },
                ],
              },
              {
                title: 'Revenue',
                type: 'table',
                headers: ['Account Code', 'Account Name', 'Amount (TZS)'],
                rows: pnl.revenue.map(r => [r.account_code, r.account_name, formatTZS(r.balance)]),
              },
              {
                title: 'Expenses',
                type: 'table',
                headers: ['Account Code', 'Account Name', 'Amount (TZS)'],
                rows: pnl.expenses.map(e => [e.account_code, e.account_name, formatTZS(e.balance)]),
              },
            ]}
          />
        );

      case 'balance-sheet':
        if (!bs) return null;
        return (
          <ReportViewer
            title="Balance Sheet"
            subtitle={`As of ${bs.as_of_date}`}
            currency={bs.currency}
            onExport={() => alert('Export functionality coming soon')}
            sections={[
              {
                title: 'Summary',
                type: 'summary',
                summaryItems: [
                  { label: 'Total Assets', value: formatTZS(bs.total_assets), color: 'text-blue-400' },
                  { label: 'Total Liabilities', value: formatTZS(bs.total_liabilities), color: 'text-amber-400' },
                  { label: 'Total Equity', value: formatTZS(bs.total_equity), color: 'text-purple-400' },
                ],
              },
              {
                title: 'Assets',
                type: 'table',
                headers: ['Account Code', 'Account Name', 'Balance (TZS)'],
                rows: bs.assets.map(a => [a.account_code, a.account_name, formatTZS(a.balance)]),
              },
              {
                title: 'Liabilities',
                type: 'table',
                headers: ['Account Code', 'Account Name', 'Balance (TZS)'],
                rows: bs.liabilities.map(l => [l.account_code, l.account_name, formatTZS(l.balance)]),
              },
              {
                title: 'Equity',
                type: 'table',
                headers: ['Account Code', 'Account Name', 'Balance (TZS)'],
                rows: bs.equity.map(e => [e.account_code, e.account_name, formatTZS(e.balance)]),
              },
            ]}
          />
        );

      case 'trial-balance':
        if (!tb) return null;
        return (
          <ReportViewer
            title="Trial Balance"
            subtitle={`As of ${endDate}`}
            onExport={() => alert('Export functionality coming soon')}
            sections={[
              {
                title: 'Trial Balance',
                type: 'table',
                headers: ['Account Code', 'Account Name', 'Debit (TZS)', 'Credit (TZS)'],
                rows: (tb.accounts || []).map((a: any) => [
                  a.account_code,
                  a.account_name,
                  a.debit > 0 ? formatTZS(a.debit) : '—',
                  a.credit > 0 ? formatTZS(a.credit) : '—',
                ]),
              },
              {
                title: 'Verification',
                type: 'summary',
                summaryItems: [
                  { label: 'Total Debits', value: formatTZS(tb.total_debits || 0) },
                  { label: 'Total Credits', value: formatTZS(tb.total_credits || 0) },
                  { label: 'Status', value: tb.balanced ? 'Balanced ✓' : 'Unbalanced ✗', color: tb.balanced ? 'text-green-400' : 'text-red-400' },
                ],
              },
            ]}
          />
        );

      case 'cash-flow':
        if (!cf) return null;
        return (
          <ReportViewer
            title="Cash Flow Statement"
            subtitle={`${startDate} to ${endDate}`}
            onExport={() => alert('Export functionality coming soon')}
            sections={[
              {
                title: 'Cash Flow Summary',
                type: 'summary',
                summaryItems: [
                  { label: 'Operating', value: formatTZS(cf.operating || 0) },
                  { label: 'Investing', value: formatTZS(cf.investing || 0) },
                  { label: 'Financing', value: formatTZS(cf.financing || 0) },
                  { label: 'Net Change', value: formatTZS(cf.net_change || 0), color: (cf.net_change || 0) >= 0 ? 'text-green-400' : 'text-red-400' },
                ],
              },
              {
                title: 'Details',
                type: 'table',
                headers: ['Category', 'Description', 'Amount (TZS)'],
                rows: (cf.items || []).map((item: any) => [item.category, item.description, formatTZS(item.amount)]),
              },
            ]}
          />
        );

      case 'ar-aging':
        if (!arAging) return null;
        return (
          <ReportViewer
            title="Accounts Receivable Aging"
            subtitle={`As of ${endDate}`}
            onExport={() => alert('Export functionality coming soon')}
            sections={[
              {
                title: 'Aging Summary',
                type: 'summary',
                summaryItems: [
                  { label: 'Current', value: formatTZS(arAging.current || 0), color: 'text-green-400' },
                  { label: '1-30 Days', value: formatTZS(arAging.days_1_30 || 0), color: 'text-amber-400' },
                  { label: '31-60 Days', value: formatTZS(arAging.days_31_60 || 0), color: 'text-orange-400' },
                  { label: '61-90 Days', value: formatTZS(arAging.days_61_90 || 0), color: 'text-red-400' },
                  { label: '90+ Days', value: formatTZS(arAging.days_90_plus || 0), color: 'text-red-600' },
                  { label: 'Total AR', value: formatTZS(arAging.total || 0) },
                ],
              },
              {
                title: 'Receivables Detail',
                type: 'table',
                headers: ['Customer', 'Invoice #', 'Due Date', 'Amount (TZS)', 'Days Overdue'],
                rows: (arAging.items || []).map((item: any) => [
                  item.customer_name,
                  item.invoice_number,
                  item.due_date,
                  formatTZS(item.amount),
                  item.days_overdue,
                ]),
              },
            ]}
          />
        );

      case 'ap-aging':
        if (!apAging) return null;
        return (
          <ReportViewer
            title="Accounts Payable Aging"
            subtitle={`As of ${endDate}`}
            onExport={() => alert('Export functionality coming soon')}
            sections={[
              {
                title: 'Aging Summary',
                type: 'summary',
                summaryItems: [
                  { label: 'Current', value: formatTZS(apAging.current || 0), color: 'text-green-400' },
                  { label: '1-30 Days', value: formatTZS(apAging.days_1_30 || 0), color: 'text-amber-400' },
                  { label: '31-60 Days', value: formatTZS(apAging.days_31_60 || 0), color: 'text-orange-400' },
                  { label: '61-90 Days', value: formatTZS(apAging.days_61_90 || 0), color: 'text-red-400' },
                  { label: '90+ Days', value: formatTZS(apAging.days_90_plus || 0), color: 'text-red-600' },
                  { label: 'Total AP', value: formatTZS(apAging.total || 0) },
                ],
              },
              {
                title: 'Payables Detail',
                type: 'table',
                headers: ['Vendor', 'Invoice #', 'Due Date', 'Amount (TZS)', 'Days Overdue'],
                rows: (apAging.items || []).map((item: any) => [
                  item.vendor_name,
                  item.invoice_number,
                  item.due_date,
                  formatTZS(item.amount),
                  item.days_overdue,
                ]),
              },
            ]}
          />
        );

      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Reports</h1>
          <p className="text-gray-400 text-sm mt-1">Generate and view financial reports</p>
        </div>
      </div>

      {/* Report Type Selector */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {REPORT_TYPES.map(rt => (
          <button
            key={rt.key}
            onClick={() => setReportType(rt.key)}
            className={`p-3 rounded-xl border text-left transition ${
              reportType === rt.key
                ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400'
                : 'bg-[#1a1a2e] border-gray-800 text-gray-400 hover:border-gray-700 hover:text-white'
            }`}
          >
            <rt.icon size={20} className="mb-2" />
            <div className="text-sm font-medium">{rt.label}</div>
            <div className="text-xs opacity-60 mt-0.5 hidden sm:block">{rt.description}</div>
          </button>
        ))}
      </div>

      {/* Date Range Picker */}
      <div className="bg-[#1a1a2e] rounded-xl border border-gray-800 p-4">
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <Calendar size={16} className="text-gray-500" />
            <span className="text-gray-400 text-sm">Period:</span>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="date"
              value={startDate}
              onChange={e => setStartDate(e.target.value)}
              className="bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-cyan-500"
            />
            <span className="text-gray-500 text-sm">to</span>
            <input
              type="date"
              value={endDate}
              onChange={e => setEndDate(e.target.value)}
              className="bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-cyan-500"
            />
          </div>
          <div className="flex gap-2">
            {[
              { label: 'This Month', start: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0] },
              { label: 'This Quarter', start: new Date(new Date().getFullYear(), Math.floor(new Date().getMonth() / 3) * 3, 1).toISOString().split('T')[0] },
              { label: 'This Year', start: `${new Date().getFullYear()}-01-01` },
            ].map(preset => (
              <button
                key={preset.label}
                onClick={() => setStartDate(preset.start)}
                className="px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-xs transition"
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Report Content */}
      {isLoading ? (
        <div className="bg-[#1a1a2e] rounded-xl border border-gray-800 p-12 text-center">
          <div className="text-cyan-400 animate-pulse">Loading report...</div>
        </div>
      ) : (
        getReportContent() || (
          <div className="bg-[#1a1a2e] rounded-xl border border-gray-800 p-12 text-center">
            <currentReport.icon size={40} className="mx-auto text-gray-600 mb-3" />
            <p className="text-gray-400">No data available for this report</p>
            <p className="text-gray-500 text-sm mt-1">Try adjusting the date range or add more transactions</p>
          </div>
        )
      )}
    </div>
  );
}
