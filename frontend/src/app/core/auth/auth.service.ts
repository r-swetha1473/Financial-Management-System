import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, of, throwError } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import { AdminStore } from '../../features/admin/services/admin.store';
import { PublicOrgUser } from '../../features/admin/models/admin.model';
import { ApiClientService, ApiError } from '../api/api-client.service';
import { LoginResponse, UserSession } from '../models/auth.model';
import { DEV_LOGIN } from '../seed/dev-seed';
import { clearAuthSession, getStoredRefreshToken, getStoredSession, getStoredToken, storeAuthSession } from './auth.storage';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly api = inject(ApiClientService);
  private readonly router = inject(Router);
  private readonly admin = inject(AdminStore);

  readonly session = signal<UserSession | null>(getStoredSession<UserSession>());
  readonly isAuthenticated = computed(() => !!this.session() && !!getStoredToken());

  login(email: string, password: string): Observable<LoginResponse> {
    return this.api.post<LoginResponse>('/auth/login', { email, password }).pipe(
      tap((response) => this.persist(response)),
      catchError((error: ApiError) => {
        if (environment.useDevSeed) {
          return this.loginFromSeed(email, password);
        }
        return throwError(() => error);
      }),
    );
  }

  logout(): void {
    clearAuthSession();
    this.session.set(null);
    this.router.navigate(['/login']);
  }

  handleUnauthorized(): void {
    if (this.session()) {
      this.logout();
    }
  }

  updateSession(partial: Partial<UserSession>): void {
    const current = this.session();
    const access = getStoredToken();
    const refresh = getStoredRefreshToken();
    if (!current || !access || !refresh) {
      return;
    }
    const next = { ...current, ...partial };
    storeAuthSession(access, refresh, next);
    this.session.set(next);
  }

  syncCurrentUser(user: Pick<PublicOrgUser, 'id' | 'email' | 'fullName' | 'role'>): void {
    const current = this.session();
    if (!current || current.userId !== user.id) {
      return;
    }
    this.updateSession({ email: user.email, fullName: user.fullName, role: user.role });
  }

  private persist(response: LoginResponse): void {
    storeAuthSession(response.accessToken, response.refreshToken, response.session);
    this.session.set(response.session);
  }

  private loginFromSeed(email: string, password: string): Observable<LoginResponse> {
    try {
      const fromAdmin = this.admin.authenticate(email, password);
      if (fromAdmin) {
        this.persist(fromAdmin);
        return of(fromAdmin);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to sign in.';
      const code = message.includes('inactive') ? '403' : '401';
      return throwError(() => ({ code, message } satisfies ApiError));
    }
    const match = DEV_LOGIN(email, password);
    if (!match) {
      return throwError(() => ({ code: '401', message: 'Invalid email or password' } satisfies ApiError));
    }
    this.persist(match);
    return of(match);
  }
}
