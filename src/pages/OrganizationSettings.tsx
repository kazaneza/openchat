import React, { useState } from 'react';
import { Settings, Copy, Check, Save, Key, MessageSquare } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { organizationApi } from '../services/api';

const OrganizationSettings: React.FC = () => {
  const { currentOrganization } = useAuth();
  const [prompt, setPrompt] = useState(currentOrganization?.prompt || '');
  const [saving, setSaving] = useState(false);
  const [copySuccess, setCopySuccess] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

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

  const handleSavePrompt = async () => {
    if (!currentOrganization) return;
    
    setSaving(true);
    try {
      // In a real implementation, you'd call an API to update the prompt
      // For now, we'll just simulate the save
      await new Promise(resolve => setTimeout(resolve, 1000));
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (error) {
      console.error('Failed to save prompt:', error);
    } finally {
      setSaving(false);
    }
  };

  if (!currentOrganization) {
    return <div>No organization selected</div>;
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Organization Settings</h1>
        <p className="text-gray-600 dark:text-gray-300">Manage your organization's chat configuration</p>
      </div>

      {/* Organization Info */}
      <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 dark:border-gray-700 mb-6">
        <div className="flex items-center space-x-4 mb-4">
          <div className="w-12 h-12 bg-gradient-to-r from-deep-blue to-slate-gray rounded-xl flex items-center justify-center">
            <Settings className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">{currentOrganization.name}</h2>
            <p className="text-gray-600 dark:text-gray-300">{currentOrganization.document_count} documents uploaded</p>
          </div>
        </div>
      </div>

      {/* Chat Endpoint */}
      <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 dark:border-gray-700 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
            <Key className="w-5 h-5 mr-2" />
            Chat Endpoint
          </h3>
          {copySuccess && (
            <div className="flex items-center text-green-600">
              <Check className="w-4 h-4 mr-1" />
              <span className="text-sm">Copied!</span>
            </div>
          )}
        </div>
        
        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 mb-4">
          <div className="flex items-center justify-between">
            <code className="text-sm text-gray-700 dark:text-gray-300 break-all">
              POST http://localhost:8000/chat/{currentOrganization.id}
            </code>
            <button
              onClick={handleCopyEndpoint}
              className="ml-4 p-2 text-gray-500 dark:text-gray-400 hover:text-deep-blue dark:hover:text-blue-400 hover:bg-slate-50 dark:hover:bg-gray-600 rounded-lg transition-all duration-200"
              title="Copy endpoint URL"
            >
              <Copy className="w-4 h-4" />
            </button>
          </div>
        </div>
        
        <div className="text-sm text-gray-600 dark:text-gray-400">
          <p className="mb-2"><strong>Usage:</strong> Send POST requests with form data containing a "message" field.</p>
          <p><strong>Example:</strong> curl -X POST -d "message=Hello" http://localhost:8000/chat/{currentOrganization.id}</p>
        </div>
      </div>

      {/* System Prompt */}
      <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm rounded-2xl p-6 border border-slate-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
            <MessageSquare className="w-5 h-5 mr-2" />
            System Prompt
          </h3>
          {saveSuccess && (
            <div className="flex items-center text-green-600">
              <Check className="w-4 h-4 mr-1" />
              <span className="text-sm">Saved!</span>
            </div>
          )}
        </div>
        
        <p className="text-gray-600 dark:text-gray-300 mb-4">
          Configure how your AI assistant behaves when responding to chat messages.
        </p>
        
        <div className="space-y-4">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-xl focus:outline-none focus:ring-2 focus:ring-deep-blue dark:focus:ring-blue-400 focus:border-transparent h-32 resize-none"
            placeholder="Enter your system prompt here..."
          />
          
          <button
            onClick={handleSavePrompt}
            disabled={saving || prompt === currentOrganization.prompt}
            className="px-6 py-3 bg-gradient-to-r from-deep-blue to-slate-gray text-white rounded-xl hover:from-blue-800 hover:to-slate-600 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 font-medium"
          >
            {saving ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Saving...</span>
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                <span>Save Changes</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default OrganizationSettings;