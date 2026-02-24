/**
 * Session management utilities for anonymous user tracking
 */

const SESSION_ID_KEY = 'swaya_session_id';

/**
 * Generate or retrieve existing session ID
 * Session ID persists across page refreshes via localStorage
 * @returns {string} Session ID in format: sess_{timestamp}_{random}
 */
export function getOrCreateSessionId() {
  // Try to get existing session ID from localStorage
  let sessionId = localStorage.getItem(SESSION_ID_KEY);
  
  if (!sessionId) {
    // Generate new session ID
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2, 11); // 9 random chars
    sessionId = `sess_${timestamp}_${random}`;
    
    // Store for future use
    localStorage.setItem(SESSION_ID_KEY, sessionId);
  }
  
  return sessionId;
}

/**
 * Clear session ID (useful for testing or logout)
 */
export function clearSessionId() {
  localStorage.removeItem(SESSION_ID_KEY);
}

/**
 * Get current session ID without creating new one
 * @returns {string|null} Session ID or null if not exists
 */
export function getSessionId() {
  return localStorage.getItem(SESSION_ID_KEY);
}
