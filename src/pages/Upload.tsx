import React, { useState, useEffect, useCallback } from 'react';
import { Upload as UploadIcon, FileText, X, Check } from 'lucide-react';
import { organizationApi } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const Upload: React.FC = () => {
  const { currentOrganization } = useAuth();
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadComplete, setUploadComplete] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const droppedFiles = Array.from(e.dataTransfer.files);
    const pdfFiles = droppedFiles.filter(file => file.type === 'application/pdf');
    
    setFiles(prev => [...prev, ...pdfFiles]);
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      const pdfFiles = selectedFiles.filter(file => file.type === 'application/pdf');
      setFiles(prev => [...prev, ...pdfFiles]);
    }
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (!currentOrganization || files.length === 0) return;

    setUploading(true);
    try {
      await organizationApi.uploadDocuments(currentOrganization.id, files);
      setUploadComplete(true);
      setFiles([]);
      setTimeout(() => setUploadComplete(false), 3000);
    } catch (error) {
      console.error('Failed to upload files:', error);
    } finally {
      setUploading(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  if (!currentOrganization) {
    return (
      <div className="max-w-4xl mx-auto text-center py-16">
        <div className="w-24 h-24 bg-slate-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
          <FileText className="w-12 h-12 text-deep-blue dark:text-blue-400" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">No Organization Selected</h2>
        <p className="text-gray-600 dark:text-gray-300">Please log in to upload documents.</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Upload Documents</h1>
        <p className="text-gray-600 dark:text-gray-300">Upload PDF documents to {currentOrganization.name}</p>
      </div>

      {/* File Upload Area */}
      <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm rounded-2xl border border-slate-200 dark:border-gray-700 overflow-hidden">
        <div
          className={`p-8 border-2 border-dashed transition-colors ${
            dragActive
              ? 'border-blue-400 bg-slate-50 dark:bg-gray-700'
              : 'border-gray-300 dark:border-gray-600 hover:border-blue-400 dark:hover:border-blue-400'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <div className="text-center">
            <div className="w-16 h-16 bg-slate-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
              <UploadIcon className="w-8 h-8 text-deep-blue dark:text-blue-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              Drop PDF files here, or click to select
            </h3>
            <p className="text-gray-600 dark:text-gray-300 mb-4">
              Upload multiple PDF documents at once
            </p>
            <input
              type="file"
              multiple
              accept=".pdf"
              onChange={handleFileSelect}
              className="hidden"
              id="file-upload"
            />
            <label
              htmlFor="file-upload"
              className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-blue-900 to-slate-700 text-white rounded-xl hover:from-blue-800 hover:to-slate-600 transition-all duration-200 cursor-pointer font-medium"
            >
              <UploadIcon className="w-5 h-5 mr-2" />
              Select Files
            </label>
          </div>
        </div>

        {/* File List */}
        {files.length > 0 && (
          <div className="border-t border-slate-200 dark:border-gray-700 p-6">
            <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Selected Files ({files.length})
            </h4>
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {files.map((file, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
                >
                  <div className="flex items-center space-x-3">
                    <FileText className="w-5 h-5 text-deep-blue dark:text-blue-400" />
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white">{file.name}</p>
                      <p className="text-sm text-gray-500 dark:text-gray-400">{formatFileSize(file.size)}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => removeFile(index)}
                    className="p-1 text-gray-400 dark:text-gray-500 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Upload Button */}
        {files.length > 0 && (
          <div className="border-t border-slate-200 dark:border-gray-700 p-6">
            <button
              onClick={handleUpload}
              disabled={uploading || uploadComplete}
              className="w-full px-6 py-3 bg-gradient-to-r from-blue-900 to-slate-700 text-white rounded-xl hover:from-blue-800 hover:to-slate-600 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2 font-medium"
            >
              {uploading ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Uploading...</span>
                </>
              ) : uploadComplete ? (
                <>
                  <Check className="w-5 h-5" />
                  <span>Upload Complete!</span>
                </>
              ) : (
                <>
                  <UploadIcon className="w-5 h-5" />
                  <span>Upload Files</span>
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Upload;