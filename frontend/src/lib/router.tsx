import { createBrowserRouter, Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import Layout from '../components/Layout';
import { RouteErrorElement } from '../components/ErrorBoundary';
import LoginPage from '../pages/LoginPage';
import RegisterPage from '../pages/RegisterPage';
import DashboardPage from '../pages/DashboardPage';
import TransactionsPage from '../pages/TransactionsPage';
import JournalPage from '../pages/JournalPage';
import ReportsPage from '../pages/ReportsPage';
import DocumentsPage from '../pages/DocumentsPage';
import SettingsPage from '../pages/SettingsPage';
import InvoicesPage from '../pages/InvoicesPage';
import ExpensesPage from '../pages/ExpensesPage';
import AICFOPage from '../pages/AICFOPage';

function ProtectedRoute() {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center"><div className="text-cyan-400 animate-pulse">Loading...</div></div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <Layout />;
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return null;
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

export const router = createBrowserRouter([
  { path: '/login', element: <PublicRoute><LoginPage /></PublicRoute>, errorElement: <RouteErrorElement /> },
  { path: '/register', element: <PublicRoute><RegisterPage /></PublicRoute>, errorElement: <RouteErrorElement /> },
  {
    element: <ProtectedRoute />,
    errorElement: <RouteErrorElement />,
    children: [
      { path: '/', element: <DashboardPage />, errorElement: <RouteErrorElement /> },
      { path: '/dashboard', element: <DashboardPage />, errorElement: <RouteErrorElement /> },
      { path: '/transactions', element: <TransactionsPage />, errorElement: <RouteErrorElement /> },
      { path: '/journal', element: <JournalPage />, errorElement: <RouteErrorElement /> },
      { path: '/invoices', element: <InvoicesPage />, errorElement: <RouteErrorElement /> },
      { path: '/expenses', element: <ExpensesPage />, errorElement: <RouteErrorElement /> },
      { path: '/reports', element: <ReportsPage />, errorElement: <RouteErrorElement /> },
      { path: '/documents', element: <DocumentsPage />, errorElement: <RouteErrorElement /> },
      { path: '/ai-cfo', element: <AICFOPage />, errorElement: <RouteErrorElement /> },
      { path: '/settings', element: <SettingsPage />, errorElement: <RouteErrorElement /> },
    ],
  },
]);
