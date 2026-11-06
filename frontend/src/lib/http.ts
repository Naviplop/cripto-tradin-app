import { API_BASE_URL, REQUEST_TIMEOUT_MS } from './constants';
import { ApiClientError, parseJsonResponse } from './errors';

export interface HttpClient {
  get<T>(path: string): Promise<T>;
  post<T>(path: string, body: unknown): Promise<T>;
  put<T>(path: string, body: unknown): Promise<T>;
  delete<T>(path: string): Promise<T>;
}

export async function fetchWithTimeout<T>(
  path: string,
  options: RequestInit = {},
  timeout = REQUEST_TIMEOUT_MS
): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
    clearTimeout(timeoutId);
    return parseJsonResponse<T>(response);
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof ApiClientError) {
      throw error;
    }
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new Error('Request timed out');
      }
      throw error;
    }
    throw new Error('Unknown network error');
  }
}

export const httpClient: HttpClient = {
  get: <T>(path: string) => fetchWithTimeout<T>(path),
  post: <T>(path: string, body: unknown) =>
    fetchWithTimeout<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    fetchWithTimeout<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  delete: <T>(path: string) =>
    fetchWithTimeout<T>(path, { method: 'DELETE' }),
};
