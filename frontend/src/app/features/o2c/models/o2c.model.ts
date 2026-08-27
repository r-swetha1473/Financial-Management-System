export interface O2cQuery {
  page?: number;
  pageSize?: number;
  search?: string;
  status?: string;
  customerId?: string;
}

export interface PageResult<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface Customer {
  id: string;
  organizationId: string;
  name: string;
  address: string | null;
  gstin: string | null;
  state: string | null;
  creditLimit: string | null;
  createdAt: string;
  addressProofName?: string;
  addressProofSize?: string;
  addressProofType?: string;
}

export interface OfferingRef {
  id: string;
  name: string;
}

export interface PlanRef {
  id: string;
  name: string;
  amount: string;
}

export interface Quotation {
  id: string;
  organizationId: string;
  customerId: string;
  customerName: string;
  quoteNumber: string;
  status: 'draft' | 'sent' | 'accepted' | 'rejected' | 'converted';
  quoteDate: string;
  validUntil: string | null;
  totalAmount: string;
  createdAt: string;
}

export interface SalesOrder {
  id: string;
  organizationId: string;
  customerId: string;
  customerName: string;
  quotationId: string | null;
  quoteNumber: string;
  orderNumber: string;
  status: 'confirmed' | 'fulfilled' | 'cancelled';
  orderDate: string;
  totalAmount: string;
  createdAt: string;
}

export interface Delivery {
  id: string;
  organizationId: string;
  salesOrderId: string;
  orderNumber: string;
  customerId: string;
  customerName: string;
  deliveryNumber: string;
  status: 'delivered' | 'cancelled';
  deliveryDate: string;
  createdAt: string;
}

export interface SalesInvoice {
  id: string;
  organizationId: string;
  customerId: string;
  customerName: string;
  salesOrderId: string | null;
  orderNumber: string;
  deliveryId: string | null;
  deliveryNumber: string;
  invoiceNumber: string;
  status: 'pending' | 'partially_paid' | 'paid' | 'cancelled';
  approvalStatus: 'pending' | 'approved' | 'rejected';
  invoiceDate: string;
  amount: string;
  gstAmount: string;
  outstanding?: string;
  createdAt: string;
}

export interface Collection {
  id: string;
  organizationId: string;
  salesInvoiceId: string;
  invoiceNumber: string;
  customerId: string;
  customerName: string;
  collectionDate: string;
  amount: string;
  paymentMode: 'Cash' | 'Card' | 'UPI';
  status: 'completed' | 'cancelled';
  createdAt: string;
}

export interface Receivable {
  id: string;
  organizationId: string;
  sourceType: 'sales_invoice';
  sourceId: string;
  invoiceNumber: string;
  customerId: string;
  customerName: string;
  amount: string;
  outstanding: string;
  dueDate: string;
  status: 'open' | 'partial' | 'closed';
  createdAt: string;
}

export interface Booking {
  id: string;
  organizationId: string;
  offeringId: string | null;
  offeringName: string;
  customerId: string | null;
  customerName: string;
  bookingStartDate: string;
  bookingEndDate: string;
  securityPaid: string;
  createdAt: string;
}

export interface LegacyInvoice {
  id: string;
  organizationId: string;
  invoiceNumber: string;
  customerId: string | null;
  customerName: string;
  bookingId: string | null;
  bookingLabel: string;
  planId: string | null;
  planName: string;
  invoiceRaisedDate: string;
  securityAmountDeposited: string;
  invoiceAmount: string;
  isGstInvoice: boolean;
  gstAmount: string;
  status: 'pending' | 'partially_paid' | 'paid';
  createdAt: string;
}

export interface InvoiceReceipt {
  id: string;
  organizationId: string;
  invoiceId: string;
  invoiceNumber: string;
  receiptDate: string;
  receiptAmount: string;
  pendingAmount: string;
  paymentMode: 'Cash' | 'Card' | 'UPI';
  transactionLast4: string;
  enteredBy: string;
  createdAt: string;
}

export interface O2cState {
  customers: Customer[];
  offerings: OfferingRef[];
  plans: PlanRef[];
  quotations: Quotation[];
  salesOrders: SalesOrder[];
  deliveries: Delivery[];
  salesInvoices: SalesInvoice[];
  collections: Collection[];
  receivables: Receivable[];
  bookings: Booking[];
  invoices: LegacyInvoice[];
  receipts: InvoiceReceipt[];
}
