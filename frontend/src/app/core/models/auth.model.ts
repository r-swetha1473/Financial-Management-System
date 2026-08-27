export type UserRole = 'ADMIN' | 'MANAGER' | 'FINANCE' | 'OPERATOR' | 'VIEWER';

export interface UserSession {
  userId: string;
  email: string;
  fullName: string;
  role: UserRole;
  organizationId: string;
  organizationName: string;
}

export interface LoginResponse {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  session: UserSession;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}
