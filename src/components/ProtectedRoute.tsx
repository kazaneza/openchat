import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import ChangePassword from '../pages/ChangePassword';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, loading, currentUser } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-gray-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-slate-200 dark:border-gray-700 border-t-deep-blue dark:border-t-blue-400 rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Check if user must change password (but not if already on change-password page)
  if (currentUser?.must_change_password && location.pathname !== '/change-password') {
    return <ChangePassword />;
  }
  return <>{children}</>;
};

export default ProtectedRoute;