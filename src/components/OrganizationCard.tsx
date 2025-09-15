import React from 'react';
import { Organization } from '../types';
import { Building2, FileText, Calendar, Trash2, Copy, ExternalLink } from 'lucide-react';

interface OrganizationCardProps {
  organization: Organization;
  onDelete: (id: string) => void;
  onSelect: (organization: Organization) => void;
  onCopyEndpoint: (id: string) => void;
  onTestEndpoint: (organization: Organization) => void;
}

const OrganizationCard: React.FC<OrganizationCardProps> = ({
  organization,
  onDelete,
  onSelect,
  onCopyEndpoint,
  onTestEndpoint,
}) => {
  return (
    <div className="bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-rose-200 hover:border-rose-300 transition-all duration-300 hover:shadow-xl hover:shadow-rose-500/10 group">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 bg-gradient-to-r from-rose-500 to-pink-500 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform duration-200">
            <Building2 className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 group-hover:text-rose-600 transition-colors">
              {organization.name}
            </h3>
            <div className="flex items-center text-sm text-gray-500 mt-1">
              <Calendar className="w-4 h-4 mr-1" />
              {new Date(organization.created_at).toLocaleDateString()}
            </div>
          </div>
        </div>
        
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete(organization.id);
          }}
          className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all duration-200"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      <p className="text-gray-600 mb-4 line-clamp-2">{organization.prompt}</p>

      {/* Chat Endpoint */}
      <div className="mb-4 p-3 bg-gray-50 rounded-lg">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Chat Endpoint:</span>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onCopyEndpoint(organization.id);
            }}
            className="p-1 text-gray-500 hover:text-rose-600 hover:bg-rose-50 rounded transition-all duration-200"
            title="Copy endpoint URL"
          >
            <Copy className="w-4 h-4" />
          </button>
        </div>
        <code className="text-xs text-gray-600 break-all">
          POST http://localhost:8000/chat/{organization.id}
        </code>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center text-sm text-gray-500">
          <FileText className="w-4 h-4 mr-1" />
          {organization.document_count} documents
        </div>
        
        <div className="flex space-x-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onTestEndpoint(organization);
            }}
            className="px-3 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-all duration-200 text-sm font-medium flex items-center space-x-1"
          >
            <ExternalLink className="w-4 h-4" />
            <span>Test</span>
          </button>
          <button
            onClick={() => onSelect(organization)}
            className="px-4 py-2 bg-gradient-to-r from-rose-500 to-pink-500 text-white rounded-lg hover:from-rose-600 hover:to-pink-600 transition-all duration-200 text-sm font-medium shadow-lg shadow-rose-500/30"
          >
            Open Chat
          </button>
        </div>
      </div>
    </div>
  );
};

export default OrganizationCard;