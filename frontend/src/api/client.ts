import axios from 'axios';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
  timeout: 45000,
  headers: {
    'Content-Type': 'application/json'
  }
});

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.message || error.message || '请求失败';
  }
  if (error instanceof Error) return error.message;
  return '请求失败';
}

export function getErrorCode(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.code || '';
  }
  return '';
}
