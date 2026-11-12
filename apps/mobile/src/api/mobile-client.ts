/**
 * Cliente HTTP tipado para la App Móvil de VotoSeguro.
 * Consume exactamente los mismos endpoints /api/v1 que la plataforma Web.
 */
import { ENV } from '../config/env';

export class MobileApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.name = 'MobileApiError';
    this.status = status;
    this.data = data;
  }
}

let activeAuthToken: string | null = null;

export function setMobileAuthToken(token: string | null) {
  activeAuthToken = token;
}

export function getMobileAuthToken(): string | null {
  return activeAuthToken;
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});

  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  if (activeAuthToken && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${activeAuthToken}`);
  }

  const url = `${ENV.API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 204) {
    return {} as T;
  }

  let data: any = null;
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    data = await response.json();
  } else {
    data = await response.text();
  }

  if (!response.ok) {
    let errorMessage = 'Ha ocurrido un error inesperado';
    if (data && typeof data === 'object' && data.detail) {
      errorMessage = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
    } else if (typeof data === 'string' && data.length > 0) {
      errorMessage = data;
    }
    throw new MobileApiError(response.status, errorMessage, data);
  }

  return data as T;
}

export const mobileApi = {
  get: <T>(url: string, options?: RequestInit) => request<T>(url, { ...options, method: 'GET' }),
  post: <T>(url: string, body?: any, options?: RequestInit) =>
    request<T>(url, {
      ...options,
      method: 'POST',
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),
  put: <T>(url: string, body?: any, options?: RequestInit) =>
    request<T>(url, {
      ...options,
      method: 'PUT',
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),
  delete: <T>(url: string, options?: RequestInit) =>
    request<T>(url, { ...options, method: 'DELETE' }),
};
