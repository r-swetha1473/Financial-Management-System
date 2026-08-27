import { Injectable, inject } from '@angular/core';
import { Observable, of, throwError } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

import { environment } from '../../../../environments/environment';
import { ApiClientService, ApiError } from '../../../core/api/api-client.service';
import { getStoredSession } from '../../../core/auth/auth.storage';
import { UserSession } from '../../../core/models/auth.model';
import { DEMO_ORGANIZATION_ID } from '../../../core/seed/ids';
import {
  AdminQuery,
  AuditLog,
  OrganizationSettings,
  OrgUser,
  PageResult,
  PublicOrgUser,
  ReferenceDatum,
} from '../models/admin.model';
import { AdminStore } from './admin.store';

@Injectable({ providedIn: 'root' })
export class AdminApiService {
  private readonly api = inject(ApiClientService);
  private readonly store = inject(AdminStore);

  listUsers(query: AdminQuery = {}): Observable<PageResult<PublicOrgUser>> {
    return this.api.getPaginated<PublicOrgUser>('/admin/users', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
      search: query.search,
      status: query.status,
      role: query.role,
    });
  }

  saveUser(
    payload: Omit<OrgUser, 'id' | 'organizationId' | 'createdAt'> & { id?: string; password?: string },
  ): Observable<PublicOrgUser> {
    const isNew = !payload.id;
    if (isNew && (!payload.password || payload.password.length < 6)) {
      return throwError(() => ({ code: '400', message: 'Password must be at least 6 characters.' } satisfies ApiError));
    }
    if (!isNew && payload.password && payload.password.length < 6) {
      return throwError(() => ({ code: '400', message: 'Password must be at least 6 characters.' } satisfies ApiError));
    }
    const body = {
      username: payload.username,
      email: payload.email,
      fullName: payload.fullName,
      role: payload.role,
      isActive: payload.isActive,
      password: payload.password || undefined,
    };
    if (isNew) {
      return this.api.post<PublicOrgUser>('/admin/users', body);
    }
    return this.api.put<PublicOrgUser>(`/admin/users/${payload.id}`, body);
  }

  listReference(query: AdminQuery = {}): Observable<PageResult<ReferenceDatum>> {
    return this.list('/reference-data', query, () => this.store.pageReference(query));
  }

  saveReference(
    payload: Omit<ReferenceDatum, 'id' | 'organizationId' | 'createdAt'> & { id?: string },
  ): Observable<ReferenceDatum> {
    const existing = payload.id ? this.store.load().referenceData.find((row) => row.id === payload.id) : undefined;
    const record: ReferenceDatum = {
      ...payload,
      id: payload.id ?? this.store.nextId('ref'),
      organizationId: this.orgId(),
      createdAt: existing?.createdAt ?? today(),
      dataType: payload.dataType.trim(),
      code: payload.code.trim(),
      label: payload.label.trim(),
    };
    return this.write('/reference-data', record, !payload.id, () => this.store.saveReference(record));
  }

  getOrganization(): Observable<OrganizationSettings> {
    return this.one('/organizations/current', () => this.store.load().organization);
  }

  saveOrganization(payload: Pick<OrganizationSettings, 'name' | 'slug' | 'isActive'>): Observable<OrganizationSettings> {
    const current = this.store.load().organization;
    const record: OrganizationSettings = {
      ...current,
      name: payload.name.trim(),
      slug: payload.slug.trim().toLowerCase(),
      isActive: payload.isActive,
    };
    return this.write('/organizations/current', record, false, () => this.store.saveOrganization(record));
  }

  listAuditLogs(query: AdminQuery = {}): Observable<PageResult<AuditLog>> {
    return this.api.getPaginated<AuditLog>('/admin/audit-logs', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
      entity_name: query.entityName,
      action: query.action,
      actor_user_id: query.actorUserId,
      date_from: query.dateFrom,
      date_to: query.dateTo,
    });
  }

  private orgId(): string {
    return getStoredSession<UserSession>()?.organizationId ?? DEMO_ORGANIZATION_ID;
  }

  private list<T>(path: string, query: AdminQuery, fallback: () => PageResult<T>): Observable<PageResult<T>> {
    return this.api
      .get<T[]>(path, {
        page: query.page,
        pageSize: query.pageSize,
        search: query.search,
        status: query.status,
        role: query.role,
        dataType: query.dataType,
        entityName: query.entityName,
        action: query.action,
      })
      .pipe(
        map((data) => ({ items: data, total: data.length, page: query.page ?? 1, pageSize: query.pageSize ?? 10 })),
        catchError((error: ApiError) => (environment.useDevSeed ? of(fallback()) : throwError(() => error))),
      );
  }

  private one<T>(path: string, fallback: () => T): Observable<T> {
    return this.api.get<T>(path).pipe(
      catchError((error: ApiError) => (environment.useDevSeed ? of(fallback()) : throwError(() => error))),
    );
  }

  private write<T extends { id: string }>(path: string, body: T, isNew: boolean, fallback: () => T): Observable<T> {
    const url = isNew || path.endsWith('/current') ? path : `${path}/${body.id}`;
    const request$ = isNew ? this.api.post<T>(path, body) : this.api.put<T>(url, body);
    return request$.pipe(
      catchError((error: ApiError) => {
        if (!environment.useDevSeed) {
          return throwError(() => error);
        }
        try {
          return of(fallback());
        } catch (storeError) {
          return throwError(() => ({
            code: '400',
            message: storeError instanceof Error ? storeError.message : error.message,
          } satisfies ApiError));
        }
      }),
    );
  }
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}
