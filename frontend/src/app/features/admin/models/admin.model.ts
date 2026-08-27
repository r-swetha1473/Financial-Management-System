import { UserRole } from '../../../core/models/auth.model';

export type { AuditLog } from '../../../core/models/audit.model';

export interface OrganizationSettings {
  id: string;
  name: string;
  slug: string;
  isActive: boolean;
  createdAt: string;
}

export interface OrgUser {
  id: string;
  organizationId: string;
  username: string;
  email: string;
  fullName: string;
  role: UserRole;
  isActive: boolean;
  createdAt: string;
  /** Demo-store only. Never displayed. Backend must persist password_hash. */
  password?: string;
}

export type PublicOrgUser = Omit<OrgUser, 'password'>;

export interface ReferenceDatum {
  id: string;
  organizationId: string;
  dataType: string;
  code: string;
  label: string;
  isActive: boolean;
  createdAt: string;
}

export interface AdminState {
  organization: OrganizationSettings;
  users: OrgUser[];
  referenceData: ReferenceDatum[];
}

export interface AdminQuery {
  page?: number;
  pageSize?: number;
  search?: string;
  status?: string;
  role?: string;
  dataType?: string;
  entityName?: string;
  action?: string;
  actorUserId?: string;
  dateFrom?: string;
  dateTo?: string;
}

export interface PageResult<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export const USER_ROLES: UserRole[] = ['ADMIN', 'MANAGER', 'FINANCE', 'OPERATOR', 'VIEWER'];
