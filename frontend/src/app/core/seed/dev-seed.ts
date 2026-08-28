import { LoginResponse, UserSession } from '../models/auth.model';
import { DEMO_ADMIN_USER_ID, DEMO_ORGANIZATION_ID } from './ids';
import {
  CashPositionItem,
  DashboardPeriod,
  DashboardSummary,
  DashboardTrendPoint,
  ProductFinancialSummary,
  RecentExpenseRow,
  RecentInvoiceRow,
  RecentReceiptRow,
} from '../models/dashboard.model';

const DEMO_SESSION: UserSession = {
  userId: DEMO_ADMIN_USER_ID,
  email: 'admin@demo-business.com',
  fullName: 'System Administrator',
  role: 'ADMIN',
  organizationId: DEMO_ORGANIZATION_ID,
  organizationName: 'Demo Business Co.',
};

export function DEV_LOGIN(email: string, password: string): LoginResponse | null {
  if (email.trim().toLowerCase() !== DEMO_SESSION.email || password !== 'admin123') {
    return null;
  }

  return {
    accessToken: 'dev-access-token',
    refreshToken: 'dev-refresh-token',
    tokenType: 'bearer',
    session: DEMO_SESSION,
  };
}

export const DASHBOARD_SEED = {
  summary: {
    totalIncome: '2847500.00',
    totalExpenses: '1623400.00',
    cashInHand: '487200.00',
    outstandingReceivables: '356800.00',
    outstandingPayables: '128400.00',
    currency: 'INR',
  } satisfies DashboardSummary,

  trend(period: DashboardPeriod): DashboardTrendPoint[] {
    const labels: Record<DashboardPeriod, string[]> = {
      daily: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
      weekly: ['W1', 'W2', 'W3', 'W4'],
      monthly: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    };
    const income = ['180000.00', '222000.00', '264000.00', '306000.00', '348000.00', '390000.00', '432000.00'];
    const expenses = ['95000.00', '123000.00', '151000.00', '179000.00', '207000.00', '235000.00', '263000.00'];
    return labels[period].map((label, index) => ({
      label,
      income: income[index],
      expenses: expenses[index],
    }));
  },

  expenses: [
    { id: 'EXP-1042', vendor: 'Metro Supplies Ltd', category: 'Procurement', amount: '24500.00', expenseDate: '2026-08-24', status: 'approved' },
    { id: 'EXP-1041', vendor: 'TechParts India', category: 'Maintenance', amount: '12800.00', expenseDate: '2026-08-23', status: 'pending' },
    { id: 'EXP-1040', vendor: 'National Logistics', category: 'Logistics', amount: '18650.00', expenseDate: '2026-08-22', status: 'approved' },
  ] satisfies RecentExpenseRow[],

  invoices: [
    { id: 'INV-892', invoiceNumber: 'SI-2026-0892', customer: 'Acme Retail Pvt Ltd', amount: '78500.00', raisedDate: '2026-08-22', status: 'partially_paid' },
    { id: 'INV-891', invoiceNumber: 'SI-2026-0891', customer: 'Greenfield Motors', amount: '142000.00', raisedDate: '2026-08-21', status: 'pending' },
    { id: 'INV-890', invoiceNumber: 'SI-2026-0890', customer: 'Horizon Fleet', amount: '56000.00', raisedDate: '2026-08-20', status: 'paid' },
  ] satisfies RecentInvoiceRow[],

  receipts: [
    { id: 'RCP-441', invoiceNumber: 'SI-2026-0892', amount: '40000.00', receiptDate: '2026-08-24', paymentMode: 'UPI' },
    { id: 'RCP-440', invoiceNumber: 'SI-2026-0888', amount: '95000.00', receiptDate: '2026-08-23', paymentMode: 'Card' },
    { id: 'RCP-439', invoiceNumber: 'SI-2026-0885', amount: '22000.00', receiptDate: '2026-08-22', paymentMode: 'Cash' },
  ] satisfies RecentReceiptRow[],

  cashPosition: [
    { accountName: 'Main Operating Account', accountType: 'bank', balance: '312400.00' },
    { accountName: 'Petty Cash', accountType: 'cash', balance: '45800.00' },
    { accountName: 'GST Settlement Account', accountType: 'bank', balance: '129000.00' },
  ] satisfies CashPositionItem[],

  products: [
    { productId: 'PRD-001', productName: 'Electric Scooter Model A', totalIncome: '890000.00', totalExpenses: '412000.00', net: '478000.00' },
    { productId: 'PRD-002', productName: 'Electric Scooter Model B', totalIncome: '654000.00', totalExpenses: '398000.00', net: '256000.00' },
    { productId: 'PRD-003', productName: 'Service Plan Annual', totalIncome: '312000.00', totalExpenses: '84000.00', net: '228000.00' },
  ] satisfies ProductFinancialSummary[],
};
