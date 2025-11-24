/**
 * Utility functions for localStorage management with quota error handling
 */

interface StoredOrganization {
  id: string;
  name: string;
  document_count: number;
  prompt: string;
  created_at?: string;
  chat_count?: number;
  last_activity?: string;
}

/**
 * Cleans up localStorage by removing old/unused items
 * Tries to free up space by removing non-essential items
 */
export const cleanupLocalStorage = (): void => {
  try {
    // Remove old items that might be taking up space
    const keysToRemove: string[] = [];
    
    // Check all localStorage keys
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && !key.startsWith('current') && !key.startsWith('auth')) {
        // Remove non-essential keys (keep only currentOrganization, currentUser, and auth-related)
        keysToRemove.push(key);
      }
    }
    
    // Remove the identified keys
    keysToRemove.forEach(key => {
      try {
        localStorage.removeItem(key);
      } catch (e) {
        console.warn(`Failed to remove localStorage key ${key}:`, e);
      }
    });
  } catch (error) {
    console.error('Error during localStorage cleanup:', error);
  }
};

/**
 * Safely sets an item in localStorage with quota error handling
 * @param key - The key to set
 * @param value - The value to set
 * @returns true if successful, false otherwise
 */
export const safeSetItem = (key: string, value: string): boolean => {
  try {
    localStorage.setItem(key, value);
    return true;
  } catch (error: any) {
    if (error.name === 'QuotaExceededError' || error.code === 22) {
      console.warn('localStorage quota exceeded, attempting cleanup...');
      
      // Try to clean up
      cleanupLocalStorage();
      
      // Try again after cleanup
      try {
        localStorage.setItem(key, value);
        return true;
      } catch (retryError) {
        console.error('Failed to set localStorage item after cleanup:', retryError);
        
        // Last resort: try to remove the same key and set again
        try {
          localStorage.removeItem(key);
          localStorage.setItem(key, value);
          return true;
        } catch (finalError) {
          console.error('Failed to set localStorage item after all retries:', finalError);
          return false;
        }
      }
    } else {
      console.error('Error setting localStorage item:', error);
      return false;
    }
  }
};

/**
 * Stores only essential organization fields to minimize storage usage
 */
export const storeOrganization = (organization: any): boolean => {
  const minimalOrg: StoredOrganization = {
    id: organization.id,
    name: organization.name,
    document_count: organization.document_count || 0,
    prompt: organization.prompt || '',
    created_at: organization.created_at,
    chat_count: organization.chat_count,
    last_activity: organization.last_activity,
  };
  
  return safeSetItem('currentOrganization', JSON.stringify(minimalOrg));
};

/**
 * Stores user data (excluding password for security)
 */
export const storeUser = (user: any): boolean => {
  const minimalUser = {
    id: user.id,
    email: user.email,
    organization_id: user.organization_id,
    role: user.role,
    must_change_password: user.must_change_password,
    created_at: user.created_at,
  };
  
  return safeSetItem('currentUser', JSON.stringify(minimalUser));
};

