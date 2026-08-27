export interface Vendor {
  id: string;
  organizationId: string;
  name: string;
  address: string | null;
  phone: string | null;
  email: string | null;
  pocName: string | null;
  pocEmail: string | null;
  gstin: string | null;
  state: string | null;
  status: 'active' | 'inactive';
  createdAt: string;
}

export interface PurchaseRequest {
  id: string;
  organizationId: string;
  vendorId: string | null;
  vendorName: string;
  requestNumber: string;
  status: 'draft' | 'submitted' | 'approved' | 'rejected' | 'converted';
  requestedByName: string;
  requestedDate: string;
  notes: string;
  createdAt: string;
}

export interface PurchaseOrder {
  id: string;
  organizationId: string;
  purchaseRequestId: string | null;
  purchaseRequestNumber: string;
  vendorId: string;
  vendorName: string;
  poNumber: string;
  status: 'draft' | 'issued' | 'received' | 'closed' | 'cancelled';
  orderDate: string;
  totalAmount: string;
  createdAt: string;
}

export interface GoodsReceipt {
  id: string;
  organizationId: string;
  purchaseOrderId: string;
  poNumber: string;
  vendorId: string;
  vendorName: string;
  grnNumber: string;
  status: 'received' | 'cancelled';
  receiptDate: string;
  createdAt: string;
}

export interface SupplierInvoice {
  id: string;
  organizationId: string;
  vendorId: string;
  vendorName: string;
  purchaseOrderId: string | null;
  poNumber: string;
  goodsReceiptId: string | null;
  grnNumber: string;
  invoiceNumber: string;
  status: 'pending' | 'partially_paid' | 'paid' | 'cancelled';
  invoiceDate: string;
  amount: string;
  gstAmount: string;
  approvalStatus: 'pending' | 'approved' | 'rejected';
  createdAt: string;
}

export interface SupplierPayment {
  id: string;
  organizationId: string;
  supplierInvoiceId: string;
  invoiceNumber: string;
  vendorId: string;
  vendorName: string;
  paymentDate: string;
  amount: string;
  paymentMode: 'Cash' | 'Card' | 'UPI';
  status: 'completed' | 'cancelled';
  createdAt: string;
}

export interface Payable {
  id: string;
  organizationId: string;
  sourceType: 'supplier_invoice';
  sourceId: string;
  invoiceNumber: string;
  vendorId: string;
  vendorName: string;
  amount: string;
  outstanding: string;
  dueDate: string;
  status: 'open' | 'partial' | 'closed';
  createdAt: string;
}

export interface P2pQuery {
  page?: number;
  pageSize?: number;
  search?: string;
  status?: string;
  vendorId?: string;
}

export interface PageResult<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface P2pState {
  vendors: Vendor[];
  purchaseRequests: PurchaseRequest[];
  purchaseOrders: PurchaseOrder[];
  goodsReceipts: GoodsReceipt[];
  supplierInvoices: SupplierInvoice[];
  payments: SupplierPayment[];
  payables: Payable[];
}
