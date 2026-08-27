export interface FinanceQuery {
  page?: number;
  pageSize?: number;
  search?: string;
  status?: string;
  vendorId?: string;
  categoryId?: string;
  accountId?: string;
  dateFrom?: string;
  dateTo?: string;
}

export interface PageResult<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface Product {
  id: string;
  organizationId: string;
  name: string;
  vinNumber: string;
  model: string;
  batteryType: string;
  bodyColor: string;
  status: 'active' | 'inactive';
  createdAt: string;
}

export interface Category {
  id: string;
  organizationId: string;
  name: string;
  description: string;
  isActive: boolean;
  createdAt: string;
}

export interface Subcategory {
  id: string;
  organizationId: string;
  categoryId: string;
  categoryName: string;
  name: string;
  description: string;
  isActive: boolean;
  createdAt: string;
}

export interface Offering {
  id: string;
  organizationId: string;
  productId: string | null;
  productName: string;
  name: string;
  description: string;
  amount: string;
  isActive: boolean;
  createdAt: string;
}

export interface Expense {
  id: string;
  organizationId: string;
  vendorId: string | null;
  vendorName: string;
  categoryId: string | null;
  categoryName: string;
  subcategoryId: string | null;
  subcategoryName: string;
  productId: string | null;
  productName: string;
  productServiceName: string;
  sku: string;
  quantity: string;
  unitPrice: string;
  cost: string;
  gstPercentage: string;
  gstAmount: string;
  purchaseOrderNumber: string;
  expenseDate: string;
  enteredBy: string;
  status: 'pending' | 'approved' | 'rejected';
  createdAt: string;
}

export interface FinanceAccount {
  id: string;
  organizationId: string;
  name: string;
  accountType: 'bank' | 'cash';
  accountNumber: string;
  balance: string;
  isActive: boolean;
  createdAt: string;
}

export interface FinanceTransaction {
  id: string;
  organizationId: string;
  accountId: string;
  accountName: string;
  transactionType: 'debit' | 'credit';
  amount: string;
  referenceType: string;
  referenceId: string;
  description: string;
  transactionDate: string;
  reconciled: boolean;
  createdAt: string;
}

export interface DocumentMeta {
  id: string;
  organizationId: string;
  entityName: string;
  entityId: string;
  fileName: string;
  mimeType: string;
  fileSize: string;
  storageKey: string;
  uploadedBy: string;
  createdAt: string;
}

export interface AuditEntry {
  id: string;
  organizationId: string;
  action: string;
  entityName: string;
  entityId: string;
  summary: string;
  createdAt: string;
}

export interface IncomeRecord {
  id: string;
  sourceType: 'invoice' | 'receipt' | 'sales_invoice' | 'collection';
  sourceId: string;
  sourceRoute: string;
  customerName: string;
  documentNumber: string;
  amount: string;
  gstAmount: string;
  date: string;
  status: string;
}

export interface FinanceState {
  products: Product[];
  categories: Category[];
  subcategories: Subcategory[];
  offerings: Offering[];
  expenses: Expense[];
  accounts: FinanceAccount[];
  transactions: FinanceTransaction[];
  documents: DocumentMeta[];
  auditEntries: AuditEntry[];
}
