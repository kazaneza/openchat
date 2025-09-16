import React, { createContext, useContext, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Organization, User } from '../types';

interface AuthContextType {
  isAuthenticated: boolean;
  currentOrganization: Organization | null;
  currentUser: User | null;
  login: (organization: Organization, user: User) => void;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentOrganization, setCurrentOrganization] = useState<Organization | null>(null);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for stored authentication
    const storedOrg = localStorage.getItem('currentOrganization');
    const storedUser = localStorage.getItem('currentUser');
    if (storedOrg && storedUser) {
      try {
        const org = JSON.parse(storedOrg);
        const user = JSON.parse(storedUser);
        setCurrentOrganization(org);
        setCurrentUser(user);
        setIsAuthenticated(true);
      } catch (error) {
        console.error('Failed to parse stored organization:', error);
        localStorage.removeItem('currentOrganization');
        localStorage.removeItem('currentUser');
      }
    }
    setLoading(false);
  }, []);

  const login = (organization: Organization, user: User) => {
    setCurrentOrganization(organization);
    setCurrentUser(user);
    setIsAuthenticated(true);
    localStorage.setItem('currentOrganization', JSON.stringify(organization));
    localStorage.setItem('currentUser', JSON.stringify(user));
    // Navigate to chat page after successful login
    window.location.href = '/chat';
  };

  const logout = () => {
    setCurrentOrganization(null);
    setCurrentUser(null);
    setIsAuthenticated(false);
    localStorage.removeItem('currentOrganization');
    localStorage.removeItem('currentUser');
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, currentOrganization, currentUser, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};