import { createBrowserRouter, Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import Layout from '../components/Layout';
import LoginPage from '../pages/LoginPage';
import RegisterPage from '../pages/RegisterPage';
import DashboardPage from '../pages/DashboardPage';
import TransactionsPage from '../pages/TransactionsPage';
import JournalPage from '../pages/JournalPage';
import ReportsPage from '../pages/ReportsPage';
import DocumentsPage from '../pages/DocumentsPage';
import SettingsPage from '../pages/SettingsPage';

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
  { path: '/login', element: <PublicRoute><LoginPage /></PublicRoute> },
  { path: '/register', element: <PublicRoute><RegisterPage /></PublicRoute> },
  {
    element: <ProtectedRoute />,
    children: [
      { path: '/', element: <DashboardPage /> },
      { path: '/dashboard', element: <DashboardPage /> },
      { path: '/transactions', element: <TransactionsPage /> },
      { path: '/journal', element: <JournalPage /> },
      { path: '/reports', element: <ReportsPage /> },
      { path: '/documents', element: <DocumentsPage /> },
      { path: '/settings', element: <SettingsPage /> },
    ],
  },
]);
