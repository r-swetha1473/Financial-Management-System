import { UserRole } from '../models/auth.model';

export type Permission =
  | 'view'
  | 'create'
  | 'edit'
  | 'delete'
  | 'approve'
  | 'export'
  | 'admin';

const ROLE_PERMISSIONS: Record<UserRole, Permission[]> = {
  ADMIN: ['view', 'create', 'edit', 'delete', 'approve', 'export', 'admin'],
  MANAGER: ['view', 'create', 'edit', 'approve', 'export'],
  FINANCE: ['view', 'create', 'edit', 'approve', 'export'],
  OPERATOR: ['view', 'create', 'edit'],
  VIEWER: ['view'],
};

export function hasPermission(role: UserRole | null | undefined, permission: Permission): boolean {
  if (!role) {
    return false;
  }
  return ROLE_PERMISSIONS[role]?.includes(permission) ?? false;
}

export function canManageRecords(role: UserRole | null | undefined): boolean {
  return hasPermission(role, 'edit') || hasPermission(role, 'delete');
}

export function canMaintainReference(role: UserRole | null | undefined): boolean {
  return role === 'ADMIN' || role === 'MANAGER';
}
