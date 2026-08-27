import {
  GoodsReceipt,
  P2pState,
  Payable,
  PurchaseOrder,
  PurchaseRequest,
  SupplierInvoice,
  SupplierPayment,
  Vendor,
} from '../models/p2p.model';
import { DEMO_ORGANIZATION_ID } from '../../../core/seed/ids';

const ORG = DEMO_ORGANIZATION_ID;

const vendors: Vendor[] = [
  {
    id: 'vnd-001',
    organizationId: ORG,
    name: 'Metro Supplies Ltd',
    address: '12 Industrial Park, Pune',
    phone: '020-44551234',
    email: 'accounts@metrosupplies.example',
    pocName: 'R. Mehta',
    pocEmail: 'r.mehta@metrosupplies.example',
    gstin: '27AABCM1234D1Z5',
    state: 'Maharashtra',
    status: 'active',
    createdAt: '2026-01-12',
  },
  {
    id: 'vnd-002',
    organizationId: ORG,
    name: 'TechParts India',
    address: '88 MIDC, Chakan',
    phone: '02135-667788',
    email: 'billing@techparts.example',
    pocName: 'S. Iyer',
    pocEmail: 's.iyer@techparts.example',
    gstin: '27AADCT5678H1Z2',
    state: 'Maharashtra',
    status: 'active',
    createdAt: '2026-02-03',
  },
  {
    id: 'vnd-003',
    organizationId: ORG,
    name: 'National Logistics',
    address: 'Warehouse 4, Nhava Sheva',
    phone: '022-33445566',
    email: 'ops@natlog.example',
    pocName: 'K. Rao',
    pocEmail: 'k.rao@natlog.example',
    gstin: '27AABCN9012P1Z8',
    state: 'Maharashtra',
    status: 'inactive',
    createdAt: '2025-11-20',
  },
];

const purchaseRequests: PurchaseRequest[] = [
  {
    id: 'pr-001',
    organizationId: ORG,
    vendorId: 'vnd-001',
    vendorName: 'Metro Supplies Ltd',
    requestNumber: 'PR-2026-001',
    status: 'converted',
    requestedByName: 'System Administrator',
    requestedDate: '2026-08-04',
    notes: 'Battery packs for service workshop.',
    createdAt: '2026-08-04',
  },
  {
    id: 'pr-002',
    organizationId: ORG,
    vendorId: 'vnd-002',
    vendorName: 'TechParts India',
    requestNumber: 'PR-2026-002',
    status: 'approved',
    requestedByName: 'System Administrator',
    requestedDate: '2026-08-18',
    notes: 'Controller boards for Model B.',
    createdAt: '2026-08-18',
  },
  {
    id: 'pr-003',
    organizationId: ORG,
    vendorId: null,
    vendorName: '',
    requestNumber: 'PR-2026-003',
    status: 'draft',
    requestedByName: 'System Administrator',
    requestedDate: '2026-08-25',
    notes: 'Packaging materials — vendor to be confirmed.',
    createdAt: '2026-08-25',
  },
];

const purchaseOrders: PurchaseOrder[] = [
  {
    id: 'po-001',
    organizationId: ORG,
    purchaseRequestId: 'pr-001',
    purchaseRequestNumber: 'PR-2026-001',
    vendorId: 'vnd-001',
    vendorName: 'Metro Supplies Ltd',
    poNumber: 'PO-2026-014',
    status: 'received',
    orderDate: '2026-08-06',
    totalAmount: '24500.00',
    createdAt: '2026-08-06',
  },
  {
    id: 'po-002',
    organizationId: ORG,
    purchaseRequestId: null,
    purchaseRequestNumber: '',
    vendorId: 'vnd-002',
    vendorName: 'TechParts India',
    poNumber: 'PO-2026-015',
    status: 'issued',
    orderDate: '2026-08-20',
    totalAmount: '12800.00',
    createdAt: '2026-08-20',
  },
];

const goodsReceipts: GoodsReceipt[] = [
  {
    id: 'grn-001',
    organizationId: ORG,
    purchaseOrderId: 'po-001',
    poNumber: 'PO-2026-014',
    vendorId: 'vnd-001',
    vendorName: 'Metro Supplies Ltd',
    grnNumber: 'GRN-2026-009',
    status: 'received',
    receiptDate: '2026-08-10',
    createdAt: '2026-08-10',
  },
];

const supplierInvoices: SupplierInvoice[] = [
  {
    id: 'si-001',
    organizationId: ORG,
    vendorId: 'vnd-001',
    vendorName: 'Metro Supplies Ltd',
    purchaseOrderId: 'po-001',
    poNumber: 'PO-2026-014',
    goodsReceiptId: 'grn-001',
    grnNumber: 'GRN-2026-009',
    invoiceNumber: 'SI-2026-044',
    status: 'partially_paid',
    invoiceDate: '2026-08-12',
    amount: '24500.00',
    gstAmount: '4410.00',
    approvalStatus: 'approved',
    createdAt: '2026-08-12',
  },
];

const payments: SupplierPayment[] = [
  {
    id: 'pay-001',
    organizationId: ORG,
    supplierInvoiceId: 'si-001',
    invoiceNumber: 'SI-2026-044',
    vendorId: 'vnd-001',
    vendorName: 'Metro Supplies Ltd',
    paymentDate: '2026-08-16',
    amount: '10000.00',
    paymentMode: 'UPI',
    status: 'completed',
    createdAt: '2026-08-16',
  },
];

const payables: Payable[] = [
  {
    id: 'ap-001',
    organizationId: ORG,
    sourceType: 'supplier_invoice',
    sourceId: 'si-001',
    invoiceNumber: 'SI-2026-044',
    vendorId: 'vnd-001',
    vendorName: 'Metro Supplies Ltd',
    amount: '24500.00',
    outstanding: '14500.00',
    dueDate: '2026-09-11',
    status: 'partial',
    createdAt: '2026-08-12',
  },
];

export function createInitialP2pState(): P2pState {
  return {
    vendors: structuredClone(vendors),
    purchaseRequests: structuredClone(purchaseRequests),
    purchaseOrders: structuredClone(purchaseOrders),
    goodsReceipts: structuredClone(goodsReceipts),
    supplierInvoices: structuredClone(supplierInvoices),
    payments: structuredClone(payments),
    payables: structuredClone(payables),
  };
}
