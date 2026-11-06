export interface ApiError {
  detail?: string;
  message?: string;
  status?: number;
}

export class ApiClientError extends Error {
  constructor(
    public readonly status: number,
    message: string
  ) {
    super(message);
    this.name = 'ApiClientError';
  }
}

export async function parseJsonResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    let detail = text;
    try {
      const parsed = JSON.parse(text) as ApiError;
      detail = parsed.detail ?? parsed.message ?? text;
    } catch {
      // keep raw text
    }
    throw new ApiClientError(response.status, detail || `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}
