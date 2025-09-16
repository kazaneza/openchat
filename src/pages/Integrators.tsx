import React, { useState } from 'react';
import { MessageSquare, Users, Facebook, Slack, MessageCircle, Instagram, Twitter, Plus, ExternalLink, Copy, Check } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

interface Integrator {
  id: string;
  name: string;
  icon: React.ComponentType<any>;
  description: string;
  color: string;
  vendor: string;
}

const Integrators: React.FC = () => {
  const { currentOrganization } = useAuth();
  const [showEndpoint, setShowEndpoint] = useState<string | null>(null);
  const [copySuccess, setCopySuccess] = useState(false);
  
  const integrators: Integrator[] = [
    {
      id: 'teams',
      name: 'Microsoft Teams',
      icon: Users,
      description: 'Connect your OpenChat bot to Microsoft Teams channels',
      color: 'from-blue-600 to-blue-700',
      vendor: 'Microsoft'
    },
    {
      id: 'facebook',
      name: 'Facebook Messenger',
      icon: Facebook,
      description: 'Enable chat support through Facebook Messenger',
      color: 'from-blue-500 to-blue-600',
      vendor: 'Meta'
    },
    {
      id: 'slack',
      name: 'Slack',
      icon: Slack,
      description: 'Integrate with Slack workspaces and channels',
      color: 'from-purple-500 to-purple-600',
      vendor: 'Slack Technologies'
    },
    {
      id: 'whatsapp',
      name: 'WhatsApp Business',
      icon: MessageCircle,
      description: 'Connect to WhatsApp Business API for customer support',
      color: 'from-green-500 to-green-600',
      vendor: 'Meta'
    },
    {
      id: 'instagram',
      name: 'Instagram',
      icon: Instagram,
      description: 'Respond to Instagram direct messages automatically',
      color: 'from-pink-500 to-purple-500',
      vendor: 'Meta'
    },
    {
      id: 'twitter',
      name: 'Twitter/X',
      icon: Twitter,
      description: 'Handle Twitter mentions and direct messages',
      color: 'from-gray-800 to-gray-900',
      vendor: 'X Corp'
    }
  ];

  const handleConnect = (integratorId: string) => {
    setShowEndpoint(integratorId);
  };

  const handleCopyEndpoint = async () => {
    if (!currentOrganization) return;
    
    const endpoint = `http://localhost:8000/chat/${currentOrganization.id}`;
    try {
      await navigator.clipboard.writeText(endpoint);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (error) {
      console.error('Failed to copy endpoint:', error);
    }
  };

  const closeEndpointModal = () => {
    setShowEndpoint(null);
    setCopySuccess(false);
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
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">1</p>
              <p className="text-sm text-gray-600 dark:text-gray-300">Chat Endpoint</p>
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
                    <p className="text-xs text-gray-500 dark:text-gray-400">by {integrator.vendor}</p>
                  </div>
                </div>
              </div>

              <p className="text-gray-600 dark:text-gray-300 mb-6 text-sm">
                {integrator.description}
              </p>

              <button
                onClick={() => handleConnect(integrator.id)}
                className="w-full px-4 py-2 bg-gradient-to-r from-deep-blue to-slate-gray text-white rounded-lg hover:from-blue-800 hover:to-slate-600 transition-all duration-200 text-sm font-medium flex items-center justify-center space-x-1"
              >
                <Plus className="w-4 h-4" />
                <span>Connect</span>
              </button>
            </div>
          );
        })}
      </div>

      {/* Connection Modal */}
      {showEndpoint && (
        <div className="fixed inset-0 bg-black/50 dark:bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-8 w-full max-w-2xl">
            {(() => {
              const integrator = integrators.find(i => i.id === showEndpoint);
              const Icon = integrator?.icon || MessageSquare;
              return (
                <>
                  <div className="flex items-center space-x-4 mb-6">
                    <div className={`w-12 h-12 bg-gradient-to-r ${integrator?.color} rounded-xl flex items-center justify-center`}>
                      <Icon className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <h2 className="text-2xl font-bold text-gray-900 dark:text-white">{integrator?.name}</h2>
                      <p className="text-gray-600 dark:text-gray-300">Integration Setup</p>
                    </div>
                  </div>

                  <div className="space-y-6">
                    {/* Chat Endpoint */}
                    <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-xl">
                      <div className="flex items-center justify-between mb-3">
                        <h3 className="font-semibold text-gray-900 dark:text-white">Your Chat Endpoint:</h3>
                        {copySuccess && (
                          <div className="flex items-center text-green-600">
                            <Check className="w-4 h-4 mr-1" />
                            <span className="text-sm">Copied!</span>
                          </div>
                        )}
                      </div>
                      <div className="flex items-center space-x-2">
                        <code className="flex-1 text-sm text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 p-3 rounded-lg border">
                          http://localhost:8000/chat/{currentOrganization?.id}
                        </code>
                        <button
                          onClick={handleCopyEndpoint}
                          className="p-3 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors"
                        >
                          <Copy className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    {/* Instructions */}
                    <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-200 dark:border-blue-800">
                      <h3 className="font-semibold text-blue-900 dark:text-blue-300 mb-3">Integration Instructions:</h3>
                      <div className="space-y-2 text-blue-800 dark:text-blue-400 text-sm">
                        <p>1. Copy the chat endpoint above</p>
                        <p>2. Contact <strong>{integrator?.vendor}</strong> or your platform administrator</p>
                        <p>3. Provide them with the endpoint URL for webhook configuration</p>
                        <p>4. Configure the platform to send POST requests with a "message" parameter</p>
                      </div>
                    </div>

                    {/* Vendor Contact */}
                    <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-xl border border-yellow-200 dark:border-yellow-800">
                      <div className="flex items-start space-x-3">
                        <ExternalLink className="w-5 h-5 text-yellow-600 dark:text-yellow-400 mt-0.5" />
                        <div>
                          <h3 className="font-semibold text-yellow-900 dark:text-yellow-300 mb-2">Need Help?</h3>
                          <p className="text-yellow-800 dark:text-yellow-400 text-sm mb-3">
                            For complete integration setup, please contact {integrator?.vendor} support or your platform administrator. 
                            They will help you configure the webhook and authentication settings.
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-end pt-6">
                    <button
                      onClick={closeEndpointModal}
                      className="px-6 py-3 bg-gradient-to-r from-deep-blue to-slate-gray text-white rounded-xl hover:from-blue-800 hover:to-slate-600 transition-all duration-200 font-medium"
                    >
                      Got it!
                    </button>
                  </div>
                </>
              );
            })()}
          </div>
        </div>
      )}

    </div>
  );
};

export default Integrators;