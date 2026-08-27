const STORAGE_KEY = 'bfms_access_token';
const REFRESH_KEY = 'bfms_refresh_token';
const SESSION_KEY = 'bfms_session';

export function getStoredToken(): string | null {
  return localStorage.getItem(STORAGE_KEY);
}

export function getStoredRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function getStoredSession<T>(): T | null {
  const raw = localStorage.getItem(SESSION_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export function storeAuthSession(accessToken: string, refreshToken: string, session: unknown): void {
  localStorage.setItem(STORAGE_KEY, accessToken);
  localStorage.setItem(REFRESH_KEY, refreshToken);
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearAuthSession(): void {
  localStorage.removeItem(STORAGE_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(SESSION_KEY);
}
