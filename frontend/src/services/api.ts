/**
 * Pipeline One - Axios API client configuration
 */

import axios, { AxiosError, AxiosInstance } from 'axios';

// Custom error class for API errors
export class ApiError extends Error {
  status: number;
  code: string;
  details?: unknown;

  constructor(message: string, status: number, code: string, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

// Create configured Axios instance
const api: AxiosInstance = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout
});

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Network error (no response)
    if (!error.response) {
      console.error('Network Error:', error.message);
      return Promise.reject(new ApiError(
        'Unable to connect to server. Please check your network connection.',
        0,
        'NETWORK_ERROR'
      ));
    }

    const status = error.response.status;
    const data = error.response.data as Record<string, unknown> | undefined;
    const message = data?.detail as string || data?.message as string || error.message;

    // Log the error
    console.error(`API Error [${status}]:`, message);

    // Handle specific error codes
    switch (status) {
      case 401:
        return Promise.reject(new ApiError(
          'Authentication required. Please log in.',
          status,
          'UNAUTHORIZED'
        ));
      case 403:
        return Promise.reject(new ApiError(
          'Access denied. You do not have permission to perform this action.',
          status,
          'FORBIDDEN'
        ));
      case 404:
        return Promise.reject(new ApiError(
          message || 'The requested resource was not found.',
          status,
          'NOT_FOUND'
        ));
      case 422:
        return Promise.reject(new ApiError(
          message || 'Invalid request data.',
          status,
          'VALIDATION_ERROR',
          data
        ));
      case 429:
        return Promise.reject(new ApiError(
          'Too many requests. Please try again later.',
          status,
          'RATE_LIMITED'
        ));
      case 500:
      case 502:
      case 503:
        return Promise.reject(new ApiError(
          'Server error. Please try again later.',
          status,
          'SERVER_ERROR'
        ));
      default:
        return Promise.reject(new ApiError(
          message || 'An unexpected error occurred.',
          status,
          'UNKNOWN_ERROR',
          data
        ));
    }
  }
);

export default api;
