import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Building2, MessageSquare, Upload, Settings, Moon, Sun } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const { isDark, toggleTheme } = useTheme();

  const navigation = [
    { name: 'Organizations', href: '/', icon: Building2 },
    { name: 'Chat', href: '/chat', icon: MessageSquare },
    { name: 'Upload', href: '/upload', icon: Upload },
    { name: 'Settings', href: '/settings', icon: Settings },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-gray-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 transition-colors duration-300">
      {/* Sidebar */}
      <div className="fixed inset-y-0 left-0 z-50 w-64 bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl border-r border-silver dark:border-gray-700 transition-colors duration-300">
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center px-6 py-8">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-r from-deep-blue to-slate-gray rounded-lg flex items-center justify-center">
                <MessageSquare className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold bg-gradient-to-r from-deep-blue to-slate-gray dark:from-blue-400 dark:to-slate-300 bg-clip-text text-transparent">
                PDF Chat
              </span>
              <div className="ml-2 px-2 py-1 bg-gradient-to-r from-deep-blue to-slate-gray text-white text-xs rounded-full font-medium">
                AI Powered
              </div>
            </div>
          </div>

          {/* Theme Toggle */}
          <div className="px-4 mb-4">
            <button
              onClick={toggleTheme}
              className="w-full flex items-center px-4 py-3 text-sm font-medium rounded-xl transition-all duration-200 text-gray-600 dark:text-gray-300 hover:bg-slate-50 dark:hover:bg-gray-800 hover:text-deep-blue dark:hover:text-blue-400"
            >
              {isDark ? <Sun className="w-5 h-5 mr-3" /> : <Moon className="w-5 h-5 mr-3" />}
              {isDark ? 'Light Mode' : 'Dark Mode'}
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 space-y-2">
            {navigation.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.href;
              
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center px-4 py-3 text-sm font-medium rounded-xl transition-all duration-200 ${
                    isActive
                      ? 'bg-gradient-to-r from-deep-blue to-slate-gray text-white shadow-lg shadow-deep-blue/30'
                      : 'text-gray-600 dark:text-gray-300 hover:bg-slate-50 dark:hover:bg-gray-800 hover:text-deep-blue dark:hover:text-blue-400'
                  }`}
                >
                  <Icon className="w-5 h-5 mr-3" />
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Main content */}
      <div className="pl-64">
        <main className="min-h-screen p-8">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;