// src/services/api.js
import axios from 'axios';

/**
 * API client for frontend
 *
 * - Attaches Authorization Bearer token automatically from localStorage 'token'
 * - Provides grouped exported objects: authAPI, billsAPI, analyticsAPI, chatAPI, voiceAPI
 * - Uses Vite env to decide base URL (VITE_API_URL). In dev with Vite proxy, API_URL can be empty.
 */

// Base URL configuration (Vite)
const API_URL = import.meta.env.PROD
  ? (import.meta.env.VITE_API_URL || "http://localhost:8000")
  : ""; // when developing with Vite proxy, leave blank

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
  // timeout: 30000, // optional
});

// ------------------------
// Token interceptor
// ------------------------
api.interceptors.request.use((config) => {
  try {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${token}`;
    }
  } catch (e) {
    // ignore
  }
  return config;
}, (error) => Promise.reject(error));

// ------------------------
// Global response error handler
// ------------------------
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // if auth fails globally, clear local storage and redirect to login
    if (error?.response?.status === 401) {
      try {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
      } catch (e) {}
      // if you're in SPA, prefer programmatic navigation; fallback to reload
      window.location.href = '/';
    }
    return Promise.reject(error);
  }
);

// =====================================================
// BILLS API
// =====================================================
export const billsAPI = {
  /**
   * Upload a single file (image/pdf) -> /api/bills/upload
   * formData must include 'file'
   */
  upload: (formData) =>
    api.post('/api/bills/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  /**
   * Bulk upload multiple files -> /api/bills/bulk-upload
   * formData must include 'files' repeated
   */
  bulkUpload: (formData) =>
    api.post('/api/bills/bulk-upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  /**
   * List bills (paginated)
   * params: { limit, offset, merchant, date_from, date_to, sort }
   */
  list: (params = {}) =>
    api.get('/api/bills/list', { params }),

  /**
   * Get one bill (with items)
   * GET /api/bills/{id}
   */
  getDetail: (billId) =>
    api.get(`/api/bills/${billId}`),

  /**
   * Update basic bill fields (merchant, amount, notes)
   * PUT /api/bills/{id}
   */
  update: (billId, data) =>
    api.put(`/api/bills/${billId}`, data),

  /**
   * Delete bill (and cascade items)
   * DELETE /api/bills/{id}
   */
  delete: (billId) =>
    api.delete(`/api/bills/${billId}`),

  /**
   * Search bills/items
   * GET /api/bills/search?q=...
   */
  search: (query) =>
    api.get('/api/bills/search', { params: { q: query } }),

  /**
   * Mark as paid (saves metadata into raw_text)
   * POST /api/bills/{id}/mark-paid
   */
  markAsPaid: (billId, data = {}) =>
    api.post(`/api/bills/${billId}/mark-paid`, data),

  /**
   * Export bills (csv/json)
   * GET /api/bills/export?format=csv
   */
  export: (format = 'csv', params = {}) =>
    api.get('/api/bills/export', {
      params: { format, ...params },
      responseType: format === 'csv' ? 'blob' : 'json',
    }),

  /**
   * Reminders for upcoming payments
   * GET /api/bills/reminders?days_ahead=7
   */
  getReminders: (daysAhead = 7) =>
    api.get('/api/bills/reminders', { params: { days_ahead: daysAhead } }),

  /**
   * Parse-only (returns parsed structure without saving)
   * POST /api/bills/parse-only
   */
  parseOnly: (formData) =>
    api.post('/api/bills/parse-only', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  /**
   * Save edited bill (client-side corrected)
   * POST /api/bills/save-edited
   * payload: { merchant, date, total, items: [...], raw_text }
   */
  saveEdited: (payload) =>
    api.post('/api/bills/save-edited', payload),

  // Item operations (note the correct paths)
  addItem: (billId, item) =>
    api.post(`/api/bills/${billId}/items`, item),

  updateItem: (billId, itemId, item) =>
    api.put(`/api/bills/${billId}/items/${itemId}`, item),

  deleteItem: (billId, itemId) =>
    api.delete(`/api/bills/${billId}/items/${itemId}`),
};

// =====================================================
// AUTH API
// =====================================================
export const authAPI = {
  /**
   * Login - returns token + user info
   * POST /api/auth/login { username, password }
   */
  login: (username, password) =>
    api.post('/api/auth/login', { username, password }),

  /**
   * Register
   * POST /api/auth/register { username, email, password, ... }
   */
  register: (payload) =>
    api.post('/api/auth/register', payload),

  /**
   * Get profile (server requires Authorization header)
   * GET /api/auth/profile
   *
   * Note: this helper also accepts an explicit token (optional).
   */
  getProfile: (token) => {
    if (token) {
      return api.get('/api/auth/profile', { headers: { Authorization: `Bearer ${token}` } });
    }
    return api.get('/api/auth/profile');
  },

  updateProfile: (data) =>
    api.put('/api/auth/profile', data),

  changePassword: (currentPassword, newPassword) =>
    api.put('/api/auth/change-password', { current_password: currentPassword, new_password: newPassword }),

  getStats: () =>
    api.get('/api/auth/get-stats'),

  logout: () =>
    api.post('/api/auth/logout'), // if backend supports logout (optional)
};

// =====================================================
// CHAT API
// =====================================================
export const chatAPI = {
  sendMessage: (message, chat_id = null) => {
    const payload = { message };

    // Only add chat_id if it is a valid integer
    if (typeof chat_id === "number") {
      payload.chat_id = chat_id;
    }

    return api.post('/api/chat/message', payload);
  },

  getCategories: () => api.get('/api/chat/categories'),
  listSessions: () => api.get('/api/chat/list'),
  getSession: (chat_id) => api.get(`/api/chat/${chat_id}`),
  createSession: (title = 'Chat') => api.post('/api/chat', { title }),
  sendFeedback: (chat_id, payload) => api.post(`/api/chat/${chat_id}/feedback`, payload),
  getSummary: (chat_id) => api.get(`/api/chat/${chat_id}/summary`)
};


// =====================================================
// ANALYTICS API
// =====================================================
export const analyticsAPI = {
  getDashboard: () =>
    api.get('/api/analytics/dashboard'),

  getCategoryBreakdown: (days = 30) =>
    api.get('/api/analytics/category-breakdown', { params: { days } }),

  getDailyAnalysis: (days = 30) =>
    api.get('/api/analytics/daily', { params: { days } }),

  getWeeklyAnalysis: (weeks = 4) =>
    api.get('/api/analytics/weekly', { params: { weeks } }),

  getMonthlyAnalysis: (months = 6) =>
    api.get('/api/analytics/monthly', { params: { months } }),

  getCategoryTrends: (category, days = 90) =>
    api.get('/api/analytics/category-trends', { params: { category, days } }),

  getMonthOverMonth: () =>
    api.get('/api/analytics/month-over-month'),

  getSpendingPatterns: () =>
    api.get('/api/analytics/spending-patterns'),

  getInsights: () =>
    api.get('/api/analytics/insights'),

  getShoppingList: (items) =>
    api.get('/api/analytics/shopping', { params: { items } }),
};

// =====================================================
// VOICE API
// =====================================================
export const voiceAPI = {
  /**
   * Transcribe audio blob
   * POST /api/voice/transcribe (form-data: audio)
   */
  transcribe: (audioBlob) => {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.wav');
    return api.post('/api/voice/transcribe', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

// =====================================================
// Export default axios instance (if needed elsewhere)
// =====================================================
export default api;
