import React, { createContext, useContext, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Organization, User } from '../types';
import { storeOrganization, storeUser } from '../utils/storage';

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
        const orgData = JSON.parse(storedOrg);
        const userData = JSON.parse(storedUser);
        
        // Reconstruct Organization object with empty arrays for documents and users
        // since we only store minimal data in localStorage
        const org: Organization = {
          ...orgData,
          documents: [],
          users: [],
        };
        
        setCurrentOrganization(org);
        setCurrentUser(userData as User);
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
    
    // Store only essential fields to avoid quota errors
    const orgStored = storeOrganization(organization);
    const userStored = storeUser(user);
    
    if (!orgStored || !userStored) {
      console.warn('Failed to store authentication data in localStorage. Session may not persist after page refresh.');
    }
    
    // Only navigate on initial login, not on data refresh
    if (!isAuthenticated) {
      window.location.href = '/chat';
    }
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