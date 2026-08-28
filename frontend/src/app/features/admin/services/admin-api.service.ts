import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';

import { ApiClientService, ApiError } from '../../../core/api/api-client.service';
import {
  AdminQuery,
  AuditLog,
  OrganizationSettings,
  OrgUser,
  PageResult,
  PublicOrgUser,
  ReferenceDatum,
} from '../models/admin.model';

@Injectable({ providedIn: 'root' })
export class AdminApiService {
  private readonly api = inject(ApiClientService);

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
    return this.api.getPaginated<ReferenceDatum>('/reference-data', {
      page: query.page ?? 1,
      page_size: query.pageSize ?? 20,
      search: query.search,
    });
  }

  saveReference(
    payload: Omit<ReferenceDatum, 'id' | 'organizationId' | 'createdAt'> & { id?: string },
  ): Observable<ReferenceDatum> {
    if (payload.id) {
      return throwError(
        () =>
          ({
            code: '501',
            message: 'Updating reference data is not supported by the API yet.',
          }) satisfies ApiError,
      );
    }
    return this.api.post<ReferenceDatum>('/reference-data', {
      dataType: payload.dataType.trim(),
      code: payload.code.trim(),
      label: payload.label.trim(),
      isActive: payload.isActive,
    });
  }

  getOrganization(): Observable<OrganizationSettings> {
    return this.api.get<OrganizationSettings>('/organizations/current');
  }

  saveOrganization(payload: Pick<OrganizationSettings, 'name' | 'slug' | 'isActive'>): Observable<OrganizationSettings> {
    return this.api.put<OrganizationSettings>('/organizations/current', payload);
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
}
