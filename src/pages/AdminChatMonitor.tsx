import React, { useState, useEffect } from 'react';
import { MessageSquare, Users, Clock, TrendingUp, Eye, Search, Filter } from 'lucide-react';

interface ChatSession {
  id: string;
  organization_name: string;
  user_email: string;
  message: string;
  response: string;
  timestamp: string;
  response_time: number;
}

const AdminChatMonitor: React.FC = () => {
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedOrg, setSelectedOrg] = useState('all');
  const [loading, setLoading] = useState(true);

  // Mock data for demonstration
  useEffect(() => {
    // Simulate loading chat sessions
    setTimeout(() => {
      const mockSessions: ChatSession[] = [
        {
          id: '1',
          organization_name: 'TechCorp',
          user_email: 'john@techcorp.com',
          message: 'What is our company policy on remote work?',
          response: 'According to the employee handbook, remote work is allowed up to 3 days per week with manager approval.',
          timestamp: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
          response_time: 1.2
        },
        {
          id: '2',
          organization_name: 'HealthPlus',
          user_email: 'sarah@healthplus.com',
          message: 'How do I submit a medical claim?',
          response: 'To submit a medical claim, please follow these steps: 1. Log into the patient portal, 2. Navigate to Claims section...',
          timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
          response_time: 0.8
        },
        {
          id: '3',
          organization_name: 'TechCorp',
          user_email: 'mike@techcorp.com',
          message: 'What are the vacation policies?',
          response: 'Employees accrue vacation time based on years of service. New employees start with 2 weeks annually.',
          timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
          response_time: 1.5
        }
      ];
      setChatSessions(mockSessions);
      setLoading(false);
    }, 1000);
  }, []);

  const filteredSessions = chatSessions.filter(session => {
    const matchesSearch = session.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         session.user_email.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesOrg = selectedOrg === 'all' || session.organization_name === selectedOrg;
    return matchesSearch && matchesOrg;
  });

  const organizations = [...new Set(chatSessions.map(s => s.organization_name))];
  const avgResponseTime = chatSessions.reduce((acc, s) => acc + s.response_time, 0) / chatSessions.length || 0;
  const totalChats = chatSessions.length;
  const activeUsers = new Set(chatSessions.map(s => s.user_email)).size;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="w-12 h-12 border-4 border-slate-200 dark:border-gray-700 border-t-red-600 dark:border-t-red-400 rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Chat Monitor</h1>
        <p className="text-gray-600 dark:text-gray-300">Monitor chat activity across all organizations</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{totalChats}</p>
              <p className="text-sm text-gray-600 dark:text-gray-300">Total Chats</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
              <Users className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{activeUsers}</p>
              <p className="text-sm text-gray-600 dark:text-gray-300">Active Users</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg flex items-center justify-center">
              <Clock className="w-5 h-5 text-yellow-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{avgResponseTime.toFixed(1)}s</p>
              <p className="text-sm text-gray-600 dark:text-gray-300">Avg Response</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{organizations.length}</p>
              <p className="text-sm text-gray-600 dark:text-gray-300">Organizations</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 dark:border-gray-700 mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input
                type="text"
                placeholder="Search messages or users..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 dark:focus:ring-red-400 focus:border-transparent"
              />
            </div>
          </div>
          <div className="md:w-48">
            <div className="relative">
              <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <select
                value={selectedOrg}
                onChange={(e) => setSelectedOrg(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 dark:focus:ring-red-400 focus:border-transparent appearance-none"
              >
                <option value="all">All Organizations</option>
                {organizations.map(org => (
                  <option key={org} value={org}>{org}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Chat Sessions */}
      <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm rounded-2xl border border-slate-200 dark:border-gray-700 overflow-hidden">
        <div className="p-6 border-b border-slate-200 dark:border-gray-700">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">Recent Chat Sessions</h2>
        </div>
        
        <div className="divide-y divide-slate-200 dark:divide-gray-700">
          {filteredSessions.map((session) => (
            <div key={session.id} className="p-6 hover:bg-slate-50 dark:hover:bg-gray-700/50 transition-colors">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-gradient-to-r from-red-600 to-red-700 rounded-full flex items-center justify-center">
                    <MessageSquare className="w-4 h-4 text-white" />
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900 dark:text-white">{session.organization_name}</p>
                    <p className="text-sm text-gray-600 dark:text-gray-400">{session.user_email}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {new Date(session.timestamp).toLocaleString()}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-500">
                    {session.response_time}s response time
                  </p>
                </div>
              </div>
              
              <div className="space-y-3">
                <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3">
                  <p className="text-sm font-medium text-blue-900 dark:text-blue-300 mb-1">User Message:</p>
                  <p className="text-blue-800 dark:text-blue-200">{session.message}</p>
                </div>
                
                <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3">
                  <p className="text-sm font-medium text-green-900 dark:text-green-300 mb-1">AI Response:</p>
                  <p className="text-green-800 dark:text-green-200">{session.response}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
        
        {filteredSessions.length === 0 && (
          <div className="p-12 text-center">
            <MessageSquare className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">No chat sessions found</h3>
            <p className="text-gray-600 dark:text-gray-300">
              {searchTerm || selectedOrg !== 'all' ? 'Try adjusting your filters' : 'Chat sessions will appear here once users start chatting'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminChatMonitor;