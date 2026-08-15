import { NavLink, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import {
  LayoutDashboard,
  Bot,
  ArrowLeftRight,
  Wallet,
  BookOpen,
  GitCompareArrows,
  FileText,
  Users,
  CreditCard,
  Receipt,
  Camera,
  Store,
  Upload,
  Files,
  Brain,
  Activity,
  TrendingUp,
  DollarSign,
  LineChart,
  BarChart3,
  Scale,
  Droplets,
  ClipboardList,
  Settings,
  LogOut,
  ChevronDown,
  ChevronRight,
  X,
  type LucideIcon,
} from 'lucide-react';

interface NavChild {
  to: string;
  label: string;
  icon: LucideIcon;
}

interface NavSection {
  label: string;
  icon: LucideIcon;
  children?: NavChild[];
  to?: string;
}

const navSections: NavSection[] = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/ai-cfo', label: 'AI CFO', icon: Bot },
  {
    label: 'Money',
    icon: Wallet,
    children: [
      { to: '/transactions', label: 'Transactions', icon: ArrowLeftRight },
      { to: '/accounts', label: 'Accounts', icon: Wallet },
      { to: '/journal', label: 'Journal', icon: BookOpen },
      { to: '/reconciliation', label: 'Reconciliation', icon: GitCompareArrows },
    ],
  },
  {
    label: 'Sales',
    icon: FileText,
    children: [
      { to: '/invoices', label: 'Invoices', icon: FileText },
      { to: '/customers', label: 'Customers', icon: Users },
      { to: '/payments', label: 'Payments', icon: CreditCard },
    ],
  },
  {
    label: 'Expenses',
    icon: Receipt,
    children: [
      { to: '/expenses', label: 'Expenses', icon: Receipt },
      { to: '/receipts', label: 'Receipts', icon: Camera },
      { to: '/vendors', label: 'Vendors', icon: Store },
    ],
  },
  {
    label: 'Documents',
    icon: Files,
    children: [
      { to: '/documents/upload', label: 'Upload', icon: Upload },
      { to: '/documents', label: 'All Documents', icon: Files },
      { to: '/documents/knowledge-base', label: 'Knowledge Base', icon: Brain },
    ],
  },
  {
    label: 'Analytics',
    icon: Activity,
    children: [
      { to: '/analytics/health', label: 'Business Health', icon: Activity },
      { to: '/analytics/profitability', label: 'Profitability', icon: TrendingUp },
      { to: '/analytics/cash-flow', label: 'Cash Flow', icon: Droplets },
      { to: '/analytics/forecasts', label: 'Forecasts', icon: LineChart },
    ],
  },
  {
    label: 'Reports',
    icon: BarChart3,
    children: [
      { to: '/reports/pnl', label: 'P&L', icon: DollarSign },
      { to: '/reports/balance-sheet', label: 'Balance Sheet', icon: Scale },
      { to: '/reports/cash-flow', label: 'Cash Flow', icon: Droplets },
      { to: '/reports/trial-balance', label: 'Trial Balance', icon: ClipboardList },
    ],
  },
  { to: '/settings', label: 'Settings', icon: Settings },
];

interface SidebarProps {
  open: boolean;
  onClose: () => void;
  onLogout: () => void;
  userEmail?: string;
  userRole?: string;
}

export default function Sidebar({ open, onClose, onLogout, userEmail, userRole }: SidebarProps) {
  const location = useLocation();
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  // Auto-expand sections that contain the active route
  useEffect(() => {
    const newExpanded: Record<string, boolean> = {};
    navSections.forEach((section) => {
      if (section.children) {
        const isActive = section.children.some((child) => location.pathname.startsWith(child.to));
        if (isActive) newExpanded[section.label] = true;
      }
    });
    setExpanded((prev) => ({ ...prev, ...newExpanded }));
  }, [location.pathname]);

  const toggleSection = (label: string) => {
    setExpanded((prev) => ({ ...prev, [label]: !prev[label] }));
  };

  const linkBase = 'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all duration-200';
  const linkActive = 'bg-cyan-500/10 text-cyan-400 font-medium';
  const linkInactive = 'text-gray-400 hover:bg-gray-800/50 hover:text-white';

  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-50 w-64 bg-[#0d0d14] border-r border-gray-800/80 flex flex-col transition-transform duration-300 ease-in-out ${
          open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Logo */}
        <div className="h-16 px-5 border-b border-gray-800/80 flex items-center justify-between shrink-0">
          <NavLink to="/dashboard" className="flex items-center gap-2.5" onClick={onClose}>
            <div className="w-8 h-8 bg-gradient-to-br from-cyan-400 to-cyan-600 rounded-lg flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <span className="text-white font-bold text-sm">F</span>
            </div>
            <span className="text-white font-bold text-lg tracking-tight">FinPilot</span>
          </NavLink>
          <button
            className="lg:hidden text-gray-400 hover:text-white p-1 rounded transition"
            onClick={onClose}
            aria-label="Close sidebar"
          >
            <X size={20} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-3 px-3 space-y-0.5 scrollbar-thin">
          {navSections.map((section) => {
            if (section.to) {
              // Single link
              return (
                <NavLink
                  key={section.to}
                  to={section.to}
                  onClick={onClose}
                  className={({ isActive }) =>
                    `${linkBase} ${isActive ? linkActive : linkInactive}`
                  }
                >
                  <section.icon size={18} className="shrink-0" />
                  <span>{section.label}</span>
                </NavLink>
              );
            }

            // Collapsible section
            const isSectionOpen = expanded[section.label] ?? false;
            const hasActiveChild = section.children?.some((c) =>
              location.pathname.startsWith(c.to)
            );

            return (
              <div key={section.label}>
                <button
                  onClick={() => toggleSection(section.label)}
                  className={`${linkBase} w-full justify-between ${
                    hasActiveChild ? 'text-white' : linkInactive
                  }`}
                >
                  <span className="flex items-center gap-3">
                    <section.icon size={18} className="shrink-0" />
                    <span>{section.label}</span>
                  </span>
                  {isSectionOpen ? (
                    <ChevronDown size={14} className="shrink-0 opacity-60" />
                  ) : (
                    <ChevronRight size={14} className="shrink-0 opacity-60" />
                  )}
                </button>

                {/* Sub-items */}
                <div
                  className={`overflow-hidden transition-all duration-200 ease-in-out ${
                    isSectionOpen ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
                  }`}
                >
                  <div className="ml-4 mt-0.5 space-y-0.5 border-l border-gray-800 pl-3">
                    {section.children?.map((child) => (
                      <NavLink
                        key={child.to}
                        to={child.to}
                        onClick={onClose}
                        className={({ isActive }) =>
                          `flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-[13px] transition-all duration-200 ${
                            isActive
                              ? 'bg-cyan-500/10 text-cyan-400 font-medium'
                              : 'text-gray-400 hover:bg-gray-800/40 hover:text-white'
                          }`
                        }
                      >
                        <child.icon size={15} className="shrink-0" />
                        <span>{child.label}</span>
                      </NavLink>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
        </nav>

        {/* User section */}
        <div className="p-3 border-t border-gray-800/80 shrink-0">
          <div className="px-3 py-2 flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white text-xs font-bold shrink-0">
              {userEmail?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-sm text-white truncate">{userEmail || 'User'}</div>
              <div className="text-xs text-gray-500 truncate">{userRole || 'Member'}</div>
            </div>
          </div>
          <button
            onClick={onLogout}
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-400 hover:bg-red-500/10 hover:text-red-400 transition w-full mt-1"
          >
            <LogOut size={18} />
            <span>Sign out</span>
          </button>
        </div>
      </aside>
    </>
  );
}
