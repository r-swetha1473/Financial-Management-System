import { UserRole } from '../../../core/models/auth.model';
import { AdminState, OrgUser, ReferenceDatum } from '../models/admin.model';

import {
  DEMO_ADMIN_USER_ID,
  DEMO_FINANCE_USER_ID,
  DEMO_MANAGER_USER_ID,
  DEMO_OPERATOR_USER_ID,
  DEMO_ORGANIZATION_ID,
  DEMO_VIEWER_USER_ID,
} from '../../../core/seed/ids';

const ORG = DEMO_ORGANIZATION_ID;

function user(
  id: string,
  username: string,
  email: string,
  fullName: string,
  role: UserRole,
  password: string,
): OrgUser {
  return {
    id,
    organizationId: ORG,
    username,
    email,
    fullName,
    role,
    isActive: true,
    createdAt: '2026-01-15',
    password,
  };
}

function lookup(id: string, dataType: string, code: string, label: string): ReferenceDatum {
  return {
    id,
    organizationId: ORG,
    dataType,
    code,
    label,
    isActive: true,
    createdAt: '2026-01-15',
  };
}

export function createInitialAdminState(): AdminState {
  return {
    organization: {
      id: ORG,
      name: 'Demo Business Co.',
      slug: 'demo-business',
      isActive: true,
      createdAt: '2026-01-15',
    },
    users: [
      user(DEMO_ADMIN_USER_ID, 'admin', 'admin@demo-business.com', 'System Administrator', 'ADMIN', 'admin123'),
      user(DEMO_MANAGER_USER_ID, 'manager', 'manager@demo-business.com', 'Operations Manager', 'MANAGER', 'manager123'),
      user(DEMO_FINANCE_USER_ID, 'finance', 'finance@demo-business.com', 'Finance Lead', 'FINANCE', 'finance123'),
      user(DEMO_OPERATOR_USER_ID, 'operator', 'operator@demo-business.com', 'Records Operator', 'OPERATOR', 'operator123'),
      user(DEMO_VIEWER_USER_ID, 'viewer', 'viewer@demo-business.com', 'Read-only Viewer', 'VIEWER', 'viewer123'),
    ],
    referenceData: [
      lookup('ref-001', 'expense_status', 'pending', 'Pending'),
      lookup('ref-002', 'expense_status', 'approved', 'Approved'),
      lookup('ref-003', 'expense_status', 'rejected', 'Rejected'),
      lookup('ref-004', 'payment_mode', 'Cash', 'Cash'),
      lookup('ref-005', 'payment_mode', 'Card', 'Card'),
      lookup('ref-006', 'payment_mode', 'UPI', 'UPI'),
      lookup('ref-007', 'account_type', 'bank', 'Bank'),
      lookup('ref-008', 'account_type', 'cash', 'Cash'),
    ],
  };
}
