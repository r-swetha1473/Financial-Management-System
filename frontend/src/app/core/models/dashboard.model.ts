export interface DashboardSummary {
  totalIncome: string;
  totalExpenses: string;
  cashInHand: string;
  outstandingReceivables: string;
  outstandingPayables: string;
  currency: string;
}

export interface DashboardTrendPoint {
  label: string;
  income: string;
  expenses: string;
}

export interface RecentExpenseRow {
  id: string;
  vendor: string;
  category: string;
  amount: string;
  expenseDate: string;
  status: string;
}

export interface RecentInvoiceRow {
  id: string;
  invoiceNumber: string;
  customer: string;
  amount: string;
  raisedDate: string;
  status: string;
}

export interface RecentReceiptRow {
  id: string;
  invoiceNumber: string;
  amount: string;
  receiptDate: string;
  paymentMode: string;
}

export interface CashPositionItem {
  accountName: string;
  accountType: string;
  balance: string;
}

export interface ProductFinancialSummary {
  productId: string;
  productName: string;
  totalIncome: string;
  totalExpenses: string;
  net: string;
}

export type DashboardPeriod = 'daily' | 'weekly' | 'monthly';
