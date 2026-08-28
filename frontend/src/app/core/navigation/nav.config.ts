import { UserRole } from '../models/auth.model';
import { canMaintainReference, hasPermission } from '../rbac/permissions';

export interface NavItem {
  label: string;
  route: string;
  icon: string;
  access?: 'all' | 'admin' | 'reference';
  /** Visible but not clickable — no working backend yet. */
  comingSoon?: boolean;
}

export interface NavSection {
  label: string;
  items: NavItem[];
  module?: 'p2p' | 'o2c' | 'finance' | 'master' | 'reports' | 'admin';
}

export const NAV_SECTIONS: NavSection[] = [
  {
    label: '',
    items: [{ label: 'Dashboard', route: '/dashboard', icon: 'dashboard' }],
  },
  {
    label: 'P2P',
    module: 'p2p',
    items: [
      { label: 'Purchase Requests', route: '/p2p/purchase-requests', icon: 'request' },
      { label: 'Purchase Orders', route: '/p2p/purchase-orders', icon: 'order' },
      { label: 'Receipts', route: '/p2p/receipts', icon: 'receipt' },
      { label: 'Supplier Invoices', route: '/p2p/supplier-invoices', icon: 'invoice' },
      { label: 'Payments', route: '/p2p/payments', icon: 'payment' },
      { label: 'Payables', route: '/p2p/payables', icon: 'payable' },
    ],
  },
  {
    label: 'O2C',
    module: 'o2c',
    items: [
      { label: 'Subscribed Plans', route: '/o2c/quotations', icon: 'quote' },
      { label: 'Sales Orders', route: '/o2c/sales-orders', icon: 'order' },
      { label: 'Deliveries / Services', route: '/o2c/deliveries', icon: 'delivery' },
      { label: 'Sales Invoices', route: '/o2c/sales-invoices', icon: 'invoice' },
      { label: 'Collections', route: '/o2c/collections', icon: 'collection' },
      { label: 'Receivables', route: '/o2c/receivables', icon: 'receivable' },
    ],
  },
  {
    label: 'Finance',
    module: 'finance',
    items: [
      { label: 'Expenses', route: '/finance/expenses', icon: 'expense' },
      { label: 'Income', route: '/finance/income', icon: 'income' },
      { label: 'Transactions', route: '/finance/transactions', icon: 'transaction' },
      { label: 'Accounts', route: '/finance/accounts', icon: 'account' },
      { label: 'GST / Tax', route: '/finance/gst', icon: 'tax' },
      { label: 'Reconciliation', route: '/finance/reconciliation', icon: 'reconcile' },
      { label: 'Bookings', route: '/finance/bookings', icon: 'booking' },
      { label: 'Booking Invoices', route: '/finance/invoices', icon: 'invoice' },
      { label: 'Receipts / Payments', route: '/finance/receipts', icon: 'receipt' },
    ],
  },
  {
    label: 'Master Data',
    module: 'master',
    items: [
      { label: 'Vendors', route: '/master/vendors', icon: 'vendor' },
      { label: 'Customers', route: '/master/customers', icon: 'customer' },
      { label: 'Products', route: '/master/products', icon: 'product' },
      { label: 'Categories', route: '/master/categories', icon: 'category' },
      { label: 'Services', route: '/master/services', icon: 'service' },
    ],
  },
  {
    label: 'Reports',
    module: 'reports',
    items: [{ label: 'All Reports', route: '/reports', icon: 'report' }],
  },
  {
    label: 'Administration',
    module: 'admin',
    items: [
      { label: 'Users & Roles', route: '/admin/users', icon: 'users', access: 'admin' },
      { label: 'Reference Data', route: '/admin/reference-data', icon: 'reference', access: 'reference' },
      { label: 'Audit Logs', route: '/admin/audit-logs', icon: 'audit' },
      { label: 'Documents', route: '/admin/documents', icon: 'document' },
      { label: 'Settings', route: '/admin/settings', icon: 'settings', access: 'admin' },
    ],
  },
];

export const P2P_WORKFLOW_STEPS = [
  'Supplier/Vendor',
  'Purchase Request',
  'Purchase Order',
  'Goods/Service Receipt',
  'Supplier Invoice',
  'Approval',
  'Payment',
  'Payables',
];

export const O2C_WORKFLOW_STEPS = [
  'Customer',
  'Subscribed Plan',
  'Sales Order',
  'Delivery / Service',
  'Sales Invoice',
  'Payment Collection',
  'Receivables',
];

export function canSeeNavItem(role: UserRole | null | undefined, item: NavItem): boolean {
  if (item.access === 'admin') {
    return hasPermission(role, 'admin');
  }
  if (item.access === 'reference') {
    return canMaintainReference(role);
  }
  return true;
}

export function visibleNavSections(role: UserRole | null | undefined): NavSection[] {
  return NAV_SECTIONS.map((section) => ({
    ...section,
    items: section.items.filter((item) => canSeeNavItem(role, item)),
  })).filter((section) => section.items.length > 0);
}
