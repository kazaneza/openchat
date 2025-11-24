/**
 * Utility functions for API configuration
 * Automatically detects the API base URL from the current host
 */

/**
 * Get the API base URL dynamically based on the current host
 * Falls back to localhost:8000 in development if window is not available
 */
export function getApiBaseUrl(): string {
  // Check if we're in a browser environment
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    const port = window.location.port;
    
    // If running on same host (frontend and backend on same origin)
    // Use the current origin but change port to 8000 for API
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      // Development: use port 8000 for API
      return `http://${hostname}:8000/api`;
    } else {
      // Production: assume API is on same origin or use environment variable
      const apiUrl = import.meta.env.VITE_API_URL;
      if (apiUrl) {
        return apiUrl;
      }
      // If no env var, assume API is on same origin
      return `${window.location.protocol}//${hostname}${port ? `:${port}` : ''}/api`;
    }
  }
  
  // Fallback for SSR or non-browser environments
  return import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
}

/**
 * Get the chat endpoint base URL (without /api prefix)
 * Used for external integrations and endpoint display
 */
export function getChatEndpointBaseUrl(): string {
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    const port = window.location.port;
    
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      // Development: use port 8000
      return `http://${hostname}:8000`;
    } else {
      // Production: use current origin or environment variable
      const apiUrl = import.meta.env.VITE_API_URL;
      if (apiUrl) {
        // Remove /api suffix if present
        return apiUrl.replace(/\/api\/?$/, '');
      }
      // If no env var, assume API is on same origin
      return `${window.location.protocol}//${hostname}${port ? `:${port}` : ''}`;
    }
  }
  
  // Fallback
  const apiUrl = import.meta.env.VITE_API_URL;
  if (apiUrl) {
    return apiUrl.replace(/\/api\/?$/, '');
  }
  return 'http://localhost:8000';
}

/**
 * Get the full chat endpoint URL for an organization
 */
export function getChatEndpointUrl(orgId: string): string {
  return `${getChatEndpointBaseUrl()}/chat/${orgId}`;
}

