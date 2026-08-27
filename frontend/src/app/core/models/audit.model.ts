export interface AuditLog {
  id: string;
  organizationId: string;
  userId: string | null;
  userEmail: string;
  userName: string;
  action: string;
  entityName: string;
  entityId: string | null;
  oldValues: Record<string, unknown> | null;
  newValues: Record<string, unknown> | null;
  /** Seed-store summary only; live API uses oldValues/newValues. */
  details?: string;
  createdAt: string;
}

export interface AuditQuery {
  page?: number;
  pageSize?: number;
  entityName?: string;
  action?: string;
  actorUserId?: string;
  dateFrom?: string;
  dateTo?: string;
}

export interface AuditPage {
  items: AuditLog[];
  total: number;
  page: number;
  pageSize: number;
}
