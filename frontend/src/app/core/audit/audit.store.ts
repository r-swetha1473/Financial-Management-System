import { Injectable } from '@angular/core';

import { UserSession } from '../models/auth.model';
import { AuditLog, AuditPage, AuditQuery } from '../models/audit.model';
import { getStoredSession } from '../auth/auth.storage';
import { DEMO_ADMIN_USER_ID, DEMO_ORGANIZATION_ID } from '../seed/ids';

interface FinanceAuditSeed {
  id: string;
  organizationId: string;
  action: string;
  entityName: string;
  entityId: string;
  summary: string;
  createdAt: string;
}

@Injectable({ providedIn: 'root' })
export class AuditStore {
  private key(orgId = this.orgId()): string {
    return `bfms_audit_${orgId}`;
  }

  load(orgId = this.orgId()): AuditLog[] {
    const raw = localStorage.getItem(this.key(orgId));
    if (!raw) {
      const initial = this.seed(orgId);
      this.save(initial, orgId);
      return initial;
    }
    try {
      return JSON.parse(raw) as AuditLog[];
    } catch {
      const initial = this.seed(orgId);
      this.save(initial, orgId);
      return initial;
    }
  }

  save(entries: AuditLog[], orgId = this.orgId()): void {
    localStorage.setItem(this.key(orgId), JSON.stringify(entries));
  }

  record(entityName: string, entityId: string, action: string, details: string, orgId = this.orgId()): AuditLog {
    const session = getStoredSession<UserSession>();
    const entry: AuditLog = {
      id: `aud-${Date.now().toString(36)}`,
      organizationId: orgId,
      userId: session?.userId ?? 'system',
      userEmail: session?.email ?? '',
      userName: session?.fullName ?? 'System',
      action,
      entityName,
      entityId,
      oldValues: null,
      newValues: null,
      details,
      createdAt: new Date().toISOString(),
    };
    const entries = this.load(orgId);
    entries.unshift(entry);
    this.save(entries, orgId);
    return entry;
  }

  page(query: AuditQuery = {}): AuditPage {
    const page = query.page ?? 1;
    const pageSize = query.pageSize ?? 10;
    const filtered = this.load().filter((row) => {
      const matchesEntity = !query.entityName || row.entityName === query.entityName;
      const matchesAction = !query.action || row.action === query.action;
      return matchesEntity && matchesAction;
    });
    const start = (page - 1) * pageSize;
    return { items: filtered.slice(start, start + pageSize), total: filtered.length, page, pageSize };
  }

  private orgId(): string {
    return getStoredSession<UserSession>()?.organizationId ?? DEMO_ORGANIZATION_ID;
  }

  private seed(orgId: string): AuditLog[] {
    const migrated = this.migrateFinance(orgId);
    const seeded: AuditLog[] = [
      {
        id: 'aud-admin-001',
        organizationId: orgId,
        userId: DEMO_ADMIN_USER_ID,
        userEmail: 'admin@demo-business.com',
        userName: 'System Administrator',
        action: 'create',
        entityName: 'user',
        entityId: DEMO_ADMIN_USER_ID,
        oldValues: null,
        newValues: null,
        details: 'Created user System Administrator (ADMIN)',
        createdAt: '2026-01-15T09:00:00.000Z',
      },
    ];
    const seen = new Set(migrated.map((row) => row.id));
    return [...migrated, ...seeded.filter((row) => !seen.has(row.id))];
  }

  private migrateFinance(orgId: string): AuditLog[] {
    const raw = localStorage.getItem(`bfms_finance_${orgId}`);
    if (!raw) {
      return [];
    }
    try {
      const parsed = JSON.parse(raw) as { auditEntries?: FinanceAuditSeed[] };
      return (parsed.auditEntries ?? []).map((row) => ({
        id: row.id,
        organizationId: orgId,
        userId: DEMO_ADMIN_USER_ID,
        userEmail: 'admin@demo-business.com',
        userName: 'System Administrator',
        action: row.action,
        entityName: row.entityName,
        entityId: row.entityId,
        oldValues: null,
        newValues: null,
        details: row.summary,
        createdAt: row.createdAt,
      }));
    } catch {
      return [];
    }
  }
}
