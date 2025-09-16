import React, { createContext, useContext, useEffect, useState } from 'react';
import { Organization } from '../types';

interface AuthContextType {
  isAuthenticated: boolean;
  currentOrganization: Organization | null;
  login: (organization: Organization) => void;
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
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for stored authentication
    const storedOrg = localStorage.getItem('currentOrganization');
    if (storedOrg) {
      try {
        const org = JSON.parse(storedOrg);
        setCurrentOrganization(org);
        setIsAuthenticated(true);
      } catch (error) {
        console.error('Failed to parse stored organization:', error);
        localStorage.removeItem('currentOrganization');
      }
    }
    setLoading(false);
  }, []);

  const login = (organization: Organization) => {
    setCurrentOrganization(organization);
    setIsAuthenticated(true);
    localStorage.setItem('currentOrganization', JSON.stringify(organization));
  };

  const logout = () => {
    setCurrentOrganization(null);
    setIsAuthenticated(false);
    localStorage.removeItem('currentOrganization');
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, currentOrganization, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};