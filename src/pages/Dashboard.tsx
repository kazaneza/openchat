import React, { useState, useEffect } from 'react';
import { Plus, Check } from 'lucide-react';
import { Organization } from '../types';
import { organizationApi } from '../services/api';
import OrganizationCard from '../components/OrganizationCard';

const Dashboard: React.FC = () => {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showTestModal, setShowTestModal] = useState(false);
  const [selectedOrg, setSelectedOrg] = useState<Organization | null>(null);
  const [testMessage, setTestMessage] = useState('');
  const [testResponse, setTestResponse] = useState('');
  const [testLoading, setTestLoading] = useState(false);
  const [copySuccess, setCopySuccess] = useState(false);
  const [newOrg, setNewOrg] = useState({ name: '', prompt: '' });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadOrganizations();
  }, []);

  const loadOrganizations = async () => {
    try {
      const data = await organizationApi.getAll();
      setOrganizations(data);
    } catch (error) {
      console.error('Failed to load organizations:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateOrganization = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await organizationApi.create(newOrg.name, newOrg.prompt);
      setNewOrg({ name: '', prompt: '' });
      setShowCreateModal(false);
      loadOrganizations();
    } catch (error) {
      console.error('Failed to create organization:', error);
    }
  };

  const handleDeleteOrganization = async (id: string) => {
    if (window.confirm('Are you sure you want to delete this organization?')) {
      try {
        await organizationApi.delete(id);
        loadOrganizations();
      } catch (error) {
        console.error('Failed to delete organization:', error);
      }
    }
  };

  const handleSelectOrganization = (organization: Organization) => {
    // Navigate to chat with this organization
    window.location.href = `/chat?org=${organization.id}`;
  };

  const handleCopyEndpoint = async (orgId: string) => {
    const endpoint = `http://localhost:8000/chat/${orgId}`;
    try {
      await navigator.clipboard.writeText(endpoint);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (error) {
      console.error('Failed to copy endpoint:', error);
    }
  };

  const handleTestEndpoint = (organization: Organization) => {
    setSelectedOrg(organization);
    setShowTestModal(true);
    setTestMessage('');
    setTestResponse('');
  };

  const handleSendTestMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrg || !testMessage.trim()) return;

    setTestLoading(true);
    try {
      const response = await fetch(`http://localhost:8000/chat/${selectedOrg.id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          message: testMessage,
        }),
      });

      const data = await response.json();
      setTestResponse(data.response);
    } catch (error) {
      console.error('Failed to test endpoint:', error);
      setTestResponse('Error: Failed to get response from endpoint');
    } finally {
      setTestLoading(false);
    }
  };
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="w-12 h-12 border-4 border-slate-200 dark:border-gray-700 border-t-deep-blue dark:border-t-blue-400 rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Organizations</h1>
        <p className="text-gray-600 dark:text-gray-300">Manage your AI-powered PDF chat organizations</p>
        {copySuccess && (
          <div className="mt-2 flex items-center text-green-600">
            <Check className="w-4 h-4 mr-1" />
            <span className="text-sm">Endpoint copied to clipboard!</span>
          </div>
        )}
      </div>

      {/* Create Button */}
      <div className="mb-8">
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center px-6 py-3 bg-gradient-to-r from-blue-900 to-slate-700 text-white rounded-xl hover:from-blue-800 hover:to-slate-600 transition-all duration-200 font-medium shadow-lg shadow-blue-900/30"
        >
          <Plus className="w-5 h-5 mr-2" />
          Create Organization
        </button>
      </div>

      {/* Organizations Grid */}
      {organizations.length === 0 ? (
        <div className="text-center py-16">
          <div className="w-24 h-24 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Plus className="w-12 h-12 text-deep-blue dark:text-blue-400" />
          </div>
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">No organizations yet</h3>
          <p className="text-gray-600 dark:text-gray-300 mb-6">Create your first organization to get started</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-6 py-3 bg-gradient-to-r from-blue-900 to-slate-700 text-white rounded-xl hover:from-blue-800 hover:to-slate-600 transition-all duration-200 font-medium"
          >
            Create Organization
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {organizations.map((org) => (
            <OrganizationCard
              key={org.id}
              organization={org}
              onDelete={handleDeleteOrganization}
              onSelect={handleSelectOrganization}
              onCopyEndpoint={handleCopyEndpoint}
              onTestEndpoint={handleTestEndpoint}
            />
          ))}
        </div>
      )}

      {/* Test Endpoint Modal */}
      {showTestModal && selectedOrg && (
        <div className="fixed inset-0 bg-black/50 dark:bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-8 w-full max-w-2xl max-h-[80vh] overflow-y-auto">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Test Endpoint: {selectedOrg.name}</h2>
            
            <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-700 rounded-xl">
              <h3 className="font-semibold text-gray-900 dark:text-white mb-2">Endpoint URL:</h3>
              <code className="text-sm text-gray-600 dark:text-gray-300 break-all">
                POST http://localhost:8000/chat/{selectedOrg.id}
              </code>
            </div>

            <form onSubmit={handleSendTestMessage} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Test Message
                </label>
                <textarea
                  value={testMessage}
                  onChange={(e) => setTestMessage(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-xl focus:outline-none focus:ring-2 focus:ring-deep-blue dark:focus:ring-blue-400 focus:border-transparent h-24 resize-none"
                  placeholder="Enter your test message here..."
                  required
                />
              </div>
              
              <button
                type="submit"
                disabled={testLoading || !testMessage.trim()}
                className="w-full px-4 py-3 bg-gradient-to-r from-blue-900 to-slate-700 text-white rounded-xl hover:from-blue-800 hover:to-slate-600 transition-all duration-200 font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
              >
                {testLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Testing...</span>
                  </>
                ) : (
                  <span>Send Test Message</span>
                )}
              </button>
            </form>

            {testResponse && (
              <div className="mt-6">
                <h3 className="font-semibold text-gray-900 dark:text-white mb-2">Response:</h3>
                <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-xl">
                  <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{testResponse}</p>
                </div>
              </div>
            )}
            
            <div className="flex justify-end pt-6">
              <button
                type="button"
                onClick={() => setShowTestModal(false)}
                className="px-6 py-3 border border-gray-300 dark:border-gray-600 dark:text-gray-300 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors font-medium"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Create Organization Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 dark:bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-8 w-full max-w-md">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Create Organization</h2>
            
            <form onSubmit={handleCreateOrganization} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Organization Name
                </label>
                <input
                  type="text"
                  value={newOrg.name}
                  onChange={(e) => setNewOrg({ ...newOrg, name: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-xl focus:outline-none focus:ring-2 focus:ring-deep-blue dark:focus:ring-blue-400 focus:border-transparent"
                  placeholder="Enter organization name"
                  required
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  System Prompt
                </label>
                <textarea
                  value={newOrg.prompt}
                  onChange={(e) => setNewOrg({ ...newOrg, prompt: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-xl focus:outline-none focus:ring-2 focus:ring-deep-blue dark:focus:ring-blue-400 focus:border-transparent h-32 resize-none"
                  placeholder="Enter the system prompt for this organization's AI assistant (e.g., 'You are a helpful assistant that answers questions about company policies based on the provided documents.')"
                  required
                />
              </div>
              
              <div className="flex space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 dark:text-gray-300 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-3 bg-gradient-to-r from-blue-900 to-slate-700 text-white rounded-xl hover:from-blue-800 hover:to-slate-600 transition-all duration-200 font-medium"
                >
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;