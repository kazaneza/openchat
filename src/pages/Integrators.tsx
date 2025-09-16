import React, { useState } from 'react';
import { MessageSquare, Users, Facebook, Slack, MessageCircle, Instagram, Twitter, Settings, Plus, ExternalLink } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

interface Integrator {
  id: string;
  name: string;
  icon: React.ComponentType<any>;
  description: string;
  status: 'connected' | 'disconnected' | 'pending';
  color: string;
}

const Integrators: React.FC = () => {
  const { currentOrganization } = useAuth();
  const [integrators, setIntegrators] = useState<Integrator[]>([
    {
      id: 'teams',
      name: 'Microsoft Teams',
      icon: Users,
      description: 'Connect your OpenChat bot to Microsoft Teams channels',
      status: 'disconnected',
      color: 'from-blue-600 to-blue-700'
    },
    {
      id: 'facebook',
      name: 'Facebook Messenger',
      icon: Facebook,
      description: 'Enable chat support through Facebook Messenger',
      status: 'connected',
      color: 'from-blue-500 to-blue-600'
    },
    {
      id: 'slack',
      name: 'Slack',
      icon: Slack,
      description: 'Integrate with Slack workspaces and channels',
      status: 'pending',
      color: 'from-purple-500 to-purple-600'
    },
    {
      id: 'whatsapp',
      name: 'WhatsApp Business',
      icon: MessageCircle,
      description: 'Connect to WhatsApp Business API for customer support',
      status: 'disconnected',
      color: 'from-green-500 to-green-600'
    },
    {
      id: 'instagram',
      name: 'Instagram',
      icon: Instagram,
      description: 'Respond to Instagram direct messages automatically',
      status: 'disconnected',
      color: 'from-pink-500 to-purple-500'
    },
    {
      id: 'twitter',
      name: 'Twitter/X',
      icon: Twitter,
      description: 'Handle Twitter mentions and direct messages',
      status: 'disconnected',
      color: 'from-gray-800 to-gray-900'
    }
  ]);

  const handleConnect = (integratorId: string) => {
    setIntegrators(prev => prev.map(integrator => 
      integrator.id === integratorId 
        ? { ...integrator, status: 'pending' as const }
        : integrator
    ));
    
    // Simulate connection process
    setTimeout(() => {
      setIntegrators(prev => prev.map(integrator => 
        integrator.id === integratorId 
          ? { ...integrator, status: 'connected' as const }
          : integrator
      ));
    }, 2000);
  };

  const handleDisconnect = (integratorId: string) => {
    setIntegrators(prev => prev.map(integrator => 
      integrator.id === integratorId 
        ? { ...integrator, status: 'disconnected' as const }
        : integrator
    ));
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected': return 'text-green-600 bg-green-50 dark:bg-green-900/20';
      case 'pending': return 'text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20';
      default: return 'text-gray-600 bg-gray-50 dark:bg-gray-700';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'connected': return 'Connected';
      case 'pending': return 'Connecting...';
      default: return 'Disconnected';
    }
  };

  if (!currentOrganization) {
    return <div>No organization selected</div>;
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Integrators</h1>
        <p className="text-gray-600 dark:text-gray-300">Connect OpenChat to your favorite platforms and channels</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {integrators.filter(i => i.status === 'connected').length}
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-300">Connected</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg flex items-center justify-center">
              <Settings className="w-5 h-5 text-yellow-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {integrators.filter(i => i.status === 'pending').length}
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-300">Pending</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
              <Plus className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{integrators.length}</p>
              <p className="text-sm text-gray-600 dark:text-gray-300">Available</p>
            </div>
          </div>
        </div>
      </div>

      {/* Integrators Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {integrators.map((integrator) => {
          const Icon = integrator.icon;
          return (
            <div
              key={integrator.id}
              className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 dark:border-gray-700 hover:border-slate-300 dark:hover:border-gray-600 transition-all duration-300 hover:shadow-xl hover:shadow-blue-900/10 dark:hover:shadow-blue-400/10"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <div className={`w-12 h-12 bg-gradient-to-r ${integrator.color} rounded-xl flex items-center justify-center`}>
                    <Icon className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                      {integrator.name}
                    </h3>
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(integrator.status)}`}>
                      {getStatusText(integrator.status)}
                    </span>
                  </div>
                </div>
              </div>

              <p className="text-gray-600 dark:text-gray-300 mb-6 text-sm">
                {integrator.description}
              </p>

              <div className="flex space-x-2">
                {integrator.status === 'connected' ? (
                  <>
                    <button
                      onClick={() => handleDisconnect(integrator.id)}
                      className="flex-1 px-4 py-2 border border-red-300 dark:border-red-600 text-red-600 dark:text-red-400 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-all duration-200 text-sm font-medium"
                    >
                      Disconnect
                    </button>
                    <button className="px-4 py-2 bg-slate-100 dark:bg-gray-700 text-slate-700 dark:text-gray-300 rounded-lg hover:bg-slate-200 dark:hover:bg-gray-600 transition-all duration-200 text-sm font-medium flex items-center space-x-1">
                      <Settings className="w-4 h-4" />
                      <span>Configure</span>
                    </button>
                  </>
                ) : integrator.status === 'pending' ? (
                  <button
                    disabled
                    className="flex-1 px-4 py-2 bg-yellow-100 dark:bg-yellow-900/20 text-yellow-600 dark:text-yellow-400 rounded-lg text-sm font-medium flex items-center justify-center space-x-2"
                  >
                    <div className="w-4 h-4 border-2 border-yellow-600 border-t-transparent rounded-full animate-spin" />
                    <span>Connecting...</span>
                  </button>
                ) : (
                  <button
                    onClick={() => handleConnect(integrator.id)}
                    className="flex-1 px-4 py-2 bg-gradient-to-r from-deep-blue to-slate-gray text-white rounded-lg hover:from-blue-800 hover:to-slate-600 transition-all duration-200 text-sm font-medium flex items-center justify-center space-x-1"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Connect</span>
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Help Section */}
      <div className="mt-8 bg-blue-50 dark:bg-blue-900/20 rounded-2xl p-6 border border-blue-200 dark:border-blue-800">
        <div className="flex items-start space-x-3">
          <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
            <ExternalLink className="w-4 h-4 text-blue-600" />
          </div>
          <div>
            <h3 className="font-semibold text-blue-900 dark:text-blue-300 mb-2">Need Help Setting Up Integrations?</h3>
            <p className="text-blue-700 dark:text-blue-400 text-sm mb-3">
              Each platform requires specific configuration steps. Check our documentation for detailed setup guides.
            </p>
            <button className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 text-sm font-medium flex items-center space-x-1">
              <span>View Documentation</span>
              <ExternalLink className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Integrators;