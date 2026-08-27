import { Injectable, inject } from '@angular/core';

import { LoginResponse, UserSession } from '../../../core/models/auth.model';
import { getStoredSession } from '../../../core/auth/auth.storage';
import { AuditStore } from '../../../core/audit/audit.store';
import {
  AdminQuery,
  AdminState,
  OrganizationSettings,
  OrgUser,
  PageResult,
  PublicOrgUser,
  ReferenceDatum,
} from '../models/admin.model';
import { createInitialAdminState } from '../seed/admin.seed';
import { DEMO_ORGANIZATION_ID } from '../../../core/seed/ids';

const PAGE_SIZE = 10;
const SLUG_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const USERNAME_PATTERN = /^[a-zA-Z0-9._-]+$/;

@Injectable({ providedIn: 'root' })
export class AdminStore {
  private readonly audit = inject(AuditStore);

  load(orgId = this.orgId()): AdminState {
    const raw = localStorage.getItem(this.key(orgId));
    if (!raw) {
      const initial = orgId === DEMO_ORGANIZATION_ID ? createInitialAdminState() : emptyAdminState(orgId);
      this.save(initial, orgId);
      return initial;
    }
    try {
      return JSON.parse(raw) as AdminState;
    } catch {
      const initial = orgId === DEMO_ORGANIZATION_ID ? createInitialAdminState() : emptyAdminState(orgId);
      this.save(initial, orgId);
      return initial;
    }
  }

  save(state: AdminState, orgId = state.organization.id): void {
    localStorage.setItem(this.key(orgId), JSON.stringify(state));
  }

  nextId(prefix: string): string {
    return `${prefix}-${Date.now().toString(36)}`;
  }

  authenticate(email: string, password: string): LoginResponse | null {
    const match = this.findUserByEmail(email);
    if (!match) {
      return null;
    }
    if (!match.organization.isActive) {
      throw new Error('This organization is inactive.');
    }
    if (!match.user.isActive) {
      throw new Error('This user is inactive. Contact an administrator.');
    }
    if (match.user.password !== password) {
      throw new Error('Invalid email or password');
    }
    return toLoginResponse(match.user, match.organization);
  }

  saveUser(record: OrgUser): PublicOrgUser {
    const state = this.load(record.organizationId);
    const existing = state.users.find((row) => row.id === record.id);
    this.assertUniqueUser(state, record);
    this.assertAdminInvariants(state, record, existing);
    if (existing) {
      record.createdAt = existing.createdAt;
      if (!record.password) {
        record.password = existing.password;
      }
    }
    const index = state.users.findIndex((row) => row.id === record.id);
    if (index >= 0) {
      state.users[index] = record;
    } else {
      state.users.unshift(record);
    }
    this.save(state, record.organizationId);
    this.audit.record(
      'user',
      record.id,
      existing ? 'update' : 'create',
      `${existing ? 'Updated' : 'Created'} user ${record.fullName} (${record.role})`,
      record.organizationId,
    );
    return toPublicUser(record);
  }

  saveReference(record: ReferenceDatum): ReferenceDatum {
    const state = this.load(record.organizationId);
    const duplicate = state.referenceData.find(
      (row) => row.dataType === record.dataType && row.code === record.code && row.id !== record.id,
    );
    if (duplicate) {
      throw new Error('A lookup with this type and code already exists.');
    }
    const existing = state.referenceData.some((row) => row.id === record.id);
    const index = state.referenceData.findIndex((row) => row.id === record.id);
    if (index >= 0) {
      state.referenceData[index] = record;
    } else {
      state.referenceData.unshift(record);
    }
    this.save(state, record.organizationId);
    this.audit.record(
      'reference_data',
      record.id,
      existing ? 'update' : 'create',
      `${existing ? 'Updated' : 'Created'} ${record.dataType}:${record.code}`,
      record.organizationId,
    );
    return record;
  }

  saveOrganization(record: OrganizationSettings): OrganizationSettings {
    if (!record.name.trim()) {
      throw new Error('Organization name is required.');
    }
    if (!SLUG_PATTERN.test(record.slug)) {
      throw new Error('Slug must be lowercase letters, numbers, and hyphens.');
    }
    if (this.slugTaken(record.slug, record.id)) {
      throw new Error('This organization slug is already in use.');
    }
    const state = this.load(record.id);
    const previous = state.organization;
    state.organization = { ...record, createdAt: previous.createdAt };
    this.save(state, record.id);
    this.audit.record(
      'organization',
      record.id,
      'update',
      `Updated organization ${record.name} (${record.slug})`,
      record.id,
    );
    return state.organization;
  }

  pageUsers(query: AdminQuery = {}): PageResult<PublicOrgUser> {
    const items = this.load().users.map(toPublicUser);
    return this.page(items, query, (item) => `${item.username} ${item.email} ${item.fullName} ${item.role}`, {
      status: query.status,
      role: query.role,
    });
  }

  pageReference(query: AdminQuery = {}): PageResult<ReferenceDatum> {
    const items = query.dataType
      ? this.load().referenceData.filter((row) => row.dataType === query.dataType)
      : this.load().referenceData;
    return this.page(items, query, (item) => `${item.dataType} ${item.code} ${item.label}`, {
      status: query.status,
    });
  }

  private page<T extends { isActive?: boolean; role?: string }>(
    items: T[],
    query: AdminQuery,
    searchFields: (item: T) => string,
    extra: { status?: string; role?: string } = {},
  ): PageResult<T> {
    const page = query.page ?? 1;
    const pageSize = query.pageSize ?? PAGE_SIZE;
    const search = (query.search ?? '').trim().toLowerCase();
    const filtered = items.filter((item) => {
      const matchesSearch = !search || searchFields(item).toLowerCase().includes(search);
      const matchesStatus =
        !extra.status ||
        (extra.status === 'active' && item.isActive === true) ||
        (extra.status === 'inactive' && item.isActive === false);
      const matchesRole = !extra.role || item.role === extra.role;
      return matchesSearch && matchesStatus && matchesRole;
    });
    const start = (page - 1) * pageSize;
    return { items: filtered.slice(start, start + pageSize), total: filtered.length, page, pageSize };
  }

  private findUserByEmail(email: string): { user: OrgUser; organization: OrganizationSettings } | null {
    const normalized = email.trim().toLowerCase();
    for (const orgId of this.knownOrgIds()) {
      const state = this.load(orgId);
      const user = state.users.find((row) => row.email.toLowerCase() === normalized);
      if (user) {
        return { user, organization: state.organization };
      }
    }
    return null;
  }

  private knownOrgIds(): string[] {
    const ids = new Set<string>([DEMO_ORGANIZATION_ID]);
    for (let index = 0; index < localStorage.length; index += 1) {
      const key = localStorage.key(index);
      const match = key?.match(/^bfms_admin_(.+)$/);
      if (match) {
        ids.add(match[1]);
      }
    }
    return [...ids];
  }

  private slugTaken(slug: string, exceptOrgId: string): boolean {
    return this.knownOrgIds().some((orgId) => {
      const org = this.load(orgId).organization;
      return org.slug === slug && org.id !== exceptOrgId;
    });
  }

  private assertUniqueUser(state: AdminState, record: OrgUser): void {
    if (!USERNAME_PATTERN.test(record.username)) {
      throw new Error('Username may contain letters, numbers, dots, underscores, and hyphens.');
    }
    const email = record.email.trim().toLowerCase();
    if (state.users.some((row) => row.email.toLowerCase() === email && row.id !== record.id)) {
      throw new Error('A user with this email already exists in the organization.');
    }
    if (state.users.some((row) => row.username.toLowerCase() === record.username.toLowerCase() && row.id !== record.id)) {
      throw new Error('A user with this username already exists in the organization.');
    }
  }

  private assertAdminInvariants(state: AdminState, next: OrgUser, previous?: OrgUser): void {
    const session = getStoredSession<UserSession>();
    if (session?.userId === next.id && !next.isActive) {
      throw new Error('You cannot deactivate your own account.');
    }
    const nextUsers = previous
      ? state.users.map((row) => (row.id === next.id ? next : row))
      : [next, ...state.users];
    if (!nextUsers.some((row) => row.role === 'ADMIN' && row.isActive)) {
      throw new Error('The organization must keep at least one active administrator.');
    }
  }

  private orgId(): string {
    return getStoredSession<UserSession>()?.organizationId ?? DEMO_ORGANIZATION_ID;
  }

  private key(orgId: string): string {
    return `bfms_admin_${orgId}`;
  }
}

export function toPublicUser(user: OrgUser): PublicOrgUser {
  const { password: _password, ...rest } = user;
  return rest;
}

function toLoginResponse(user: OrgUser, organization: OrganizationSettings): LoginResponse {
  return {
    accessToken: 'dev-access-token',
    refreshToken: 'dev-refresh-token',
    tokenType: 'bearer',
    session: {
      userId: user.id,
      email: user.email,
      fullName: user.fullName,
      role: user.role,
      organizationId: organization.id,
      organizationName: organization.name,
    },
  };
}

function emptyAdminState(orgId: string): AdminState {
  return {
    organization: {
      id: orgId,
      name: orgId,
      slug: orgId,
      isActive: true,
      createdAt: new Date().toISOString().slice(0, 10),
    },
    users: [],
    referenceData: [],
  };
}
