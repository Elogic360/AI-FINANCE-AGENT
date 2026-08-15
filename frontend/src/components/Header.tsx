import { useState, useRef, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Menu, Bell, Search, Plus, FileText, ArrowLeftRight, Upload } from 'lucide-react';

interface HeaderProps {
  onMenuClick: () => void;
  userName?: string;
  userRole?: string;
  orgName?: string;
}

const breadcrumbMap: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/ai-cfo': 'AI CFO',
  '/transactions': 'Transactions',
  '/accounts': 'Accounts',
  '/journal': 'Journal Entries',
  '/reconciliation': 'Reconciliation',
  '/invoices': 'Invoices',
  '/customers': 'Customers',
  '/payments': 'Payments',
  '/expenses': 'Expenses',
  '/receipts': 'Receipts',
  '/vendors': 'Vendors',
  '/documents': 'Documents',
  '/documents/upload': 'Upload Documents',
  '/documents/knowledge-base': 'Knowledge Base',
  '/analytics/health': 'Business Health',
  '/analytics/profitability': 'Profitability',
  '/analytics/cash-flow': 'Cash Flow Analysis',
  '/analytics/forecasts': 'Forecasts',
  '/reports/pnl': 'Profit & Loss',
  '/reports/balance-sheet': 'Balance Sheet',
  '/reports/cash-flow': 'Cash Flow Report',
  '/reports/trial-balance': 'Trial Balance',
  '/settings': 'Settings',
};

export default function Header({ onMenuClick, userName, userRole, orgName }: HeaderProps) {
  const location = useLocation();
  const [showQuickActions, setShowQuickActions] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const quickRef = useRef<HTMLDivElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);

  const pageTitle = breadcrumbMap[location.pathname] || 'Dashboard';

  // Close dropdowns on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (quickRef.current && !quickRef.current.contains(e.target as Node)) {
        setShowQuickActions(false);
      }
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setShowNotifications(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Keyboard shortcut for search
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setShowSearch((prev) => !prev);
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  return (
    <header className="h-16 border-b border-gray-800/80 flex items-center px-4 md:px-6 gap-3 bg-[#0d0d14]/80 backdrop-blur-xl sticky top-0 z-30">
      {/* Mobile menu button */}
      <button
        className="lg:hidden text-gray-400 hover:text-white p-1.5 rounded-lg hover:bg-gray-800/50 transition"
        onClick={onMenuClick}
        aria-label="Open menu"
      >
        <Menu size={20} />
      </button>

      {/* Page title / breadcrumb */}
      <div className="flex items-center gap-2 min-w-0">
        <h1 className="text-white font-semibold text-base truncate">{pageTitle}</h1>
      </div>

      <div className="flex-1" />

      {/* Search bar (desktop) */}
      <button
        onClick={() => setShowSearch(true)}
        className="hidden md:flex items-center gap-2 bg-gray-800/40 border border-gray-700/50 rounded-lg px-3 py-1.5 text-sm text-gray-500 hover:text-gray-300 hover:border-gray-600 transition min-w-[200px]"
      >
        <Search size={14} />
        <span>Search...</span>
        <kbd className="ml-auto text-[10px] bg-gray-700/50 rounded px-1.5 py-0.5 text-gray-500 font-mono">
          ⌘K
        </kbd>
      </button>

      {/* Quick Actions */}
      <div ref={quickRef} className="relative">
        <button
          onClick={() => setShowQuickActions(!showQuickActions)}
          className="flex items-center gap-1.5 bg-cyan-500 hover:bg-cyan-600 text-white px-3 py-1.5 rounded-lg text-sm font-medium transition shadow-lg shadow-cyan-500/20"
        >
          <Plus size={16} />
          <span className="hidden sm:inline">New</span>
        </button>

        {showQuickActions && (
          <div className="absolute right-0 top-full mt-2 w-52 bg-[#1a1a2e] border border-gray-700/50 rounded-xl shadow-2xl shadow-black/40 py-2 z-50 animate-fade-in">
            {[
              { icon: ArrowLeftRight, label: 'Transaction', to: '/transactions' },
              { icon: FileText, label: 'Invoice', to: '/invoices' },
              { icon: Upload, label: 'Document', to: '/documents/upload' },
            ].map((action) => (
              <button
                key={action.label}
                onClick={() => setShowQuickActions(false)}
                className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-300 hover:bg-gray-800/50 hover:text-white transition"
              >
                <action.icon size={16} className="text-gray-500" />
                New {action.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Notifications */}
      <div ref={notifRef} className="relative">
        <button
          onClick={() => setShowNotifications(!showNotifications)}
          className="relative p-2 text-gray-400 hover:text-white hover:bg-gray-800/50 rounded-lg transition"
          aria-label="Notifications"
        >
          <Bell size={18} />
          <span className="absolute top-1 right-1 w-2 h-2 bg-cyan-400 rounded-full" />
        </button>

        {showNotifications && (
          <div className="absolute right-0 top-full mt-2 w-80 bg-[#1a1a2e] border border-gray-700/50 rounded-xl shadow-2xl shadow-black/40 z-50 animate-fade-in">
            <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
              <span className="text-white font-medium text-sm">Notifications</span>
              <button className="text-xs text-cyan-400 hover:text-cyan-300 transition">Mark all read</button>
            </div>
            <div className="py-2 max-h-80 overflow-y-auto">
              <div className="px-4 py-3 hover:bg-gray-800/30 transition">
                <div className="text-sm text-white">Welcome to FinPilot!</div>
                <div className="text-xs text-gray-500 mt-0.5">Your AI-powered financial copilot is ready.</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Org name (desktop) */}
      {orgName && (
        <div className="hidden lg:flex items-center gap-2 pl-3 border-l border-gray-800">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white text-[10px] font-bold">
            {orgName.charAt(0).toUpperCase()}
          </div>
          <span className="text-sm text-gray-300 font-medium truncate max-w-[140px]">{orgName}</span>
        </div>
      )}

      {/* User avatar */}
      <div className="flex items-center gap-2 pl-2" title={userRole}>
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white text-xs font-bold">
          {userName?.charAt(0).toUpperCase() || 'U'}
        </div>
      </div>

      {/* Search modal overlay */}
      {showSearch && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[60] flex items-start justify-center pt-[15vh]"
          onClick={() => setShowSearch(false)}
        >
          <div
            className="w-full max-w-lg bg-[#1a1a2e] border border-gray-700/50 rounded-2xl shadow-2xl overflow-hidden animate-fade-in"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
              <Search size={18} className="text-gray-500" />
              <input
                autoFocus
                type="text"
                placeholder="Search pages, transactions, documents..."
                className="flex-1 bg-transparent text-white text-sm focus:outline-none placeholder:text-gray-600"
              />
              <kbd className="text-[10px] bg-gray-700/50 rounded px-1.5 py-0.5 text-gray-500 font-mono">
                ESC
              </kbd>
            </div>
            <div className="py-2 px-2 max-h-64 overflow-y-auto">
              <div className="px-3 py-6 text-center text-gray-500 text-sm">
                Type to search across your financial data...
              </div>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
